"""
mis_engine/export.py
--------------------
Generates a fully self-contained offline interactive HTML report ZIP.

Flow:
  1. Run all four report processors (same as get_all_reports view)
  2. Serialize the data snapshot as JSON
  3. Inject it into the pre-built Vite dist/index.html via placeholder replacement
  4. Zip the entire dist folder (with the patched HTML) in-memory
  5. Return a BytesIO ready to stream as a Django HttpResponse

The React app checks for window.REPORT_DATA at startup.
If it exists → offline mode (no API calls).
If it doesn't → live API mode (normal dashboard behaviour).
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Absolute path to the Vite dist folder (relative to this file's location)
# Layout: backend/mis_engine/export.py → ../../frontend/dist
DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

# The exact placeholder string that must appear in dist/index.html.
# The build step (npm run build) preserves HTML comments verbatim.
DATA_PLACEHOLDER = "<!-- __MIS_REPORT_DATA__ -->"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_snapshot(from_date: str, to_date: str) -> dict:
    """
    Runs all processors and returns a single JSON-serialisable dict that
    mirrors the 'data' payload returned by the get_all_reports API endpoint.

    Args:
        from_date: "YYYYMMDD" e.g. "20250401"
        to_date:   "YYYYMMDD" e.g. "20260131"
    """
    from mis_engine.reports.pnl_bs import StandardReportProcessor
    from mis_engine.reports.matrix import aggregate_from_unit
    from mis_engine.reports.unit import UnitReportProcessor
    from mis_engine.reports.deposits_loans import DepositsLoansProcessor

    logger.info("Building report snapshot: %s → %s", from_date, to_date)

    std    = StandardReportProcessor(from_date, to_date)
    std_r  = std.process()

    unit   = UnitReportProcessor(from_date, to_date)
    unit_r = unit.process()

    mat_r  = aggregate_from_unit(unit_r)

    dl     = DepositsLoansProcessor(from_date, to_date)
    dl._raw_data = unit._raw_data   # reuse already-fetched trial balance
    dl_r   = dl.process()

    snapshot = {
        "company_id":       std.api.COMPANY_ID,
        "company_name":     std.api.COMPANY_ID,
        "period_start":     from_date,
        "period_end":       to_date,
        "consolidated_pnl": std_r["pnl"],
        "balance_sheet":    std_r["balance_sheet"],
        "matrix_pnl":       mat_r,
        "unit_wise":        unit_r,
        "deposits_loans":   dl_r,
    }

    logger.info(
        "Snapshot built — PnL sections: %s, Matrix periods: %d, Unit count: %d",
        list(std_r["pnl"].get("sections", {}).keys()),
        len(mat_r) if isinstance(mat_r, list) else 1,
        len(unit_r) if isinstance(unit_r, list) else 0,
    )
    return snapshot


def generate_report_zip(from_date: str, to_date: str) -> io.BytesIO:
    """
    Builds the data snapshot, injects it into the Vite dist HTML, and
    returns an in-memory ZIP (BytesIO) ready to stream to the client.

    With vite-plugin-singlefile, ALL JS and CSS are inlined directly inside
    dist/index.html — so the ZIP only needs to contain this one file.
    This avoids the Chrome file:// CORS restriction on type="module" scripts.

    Raises:
        FileNotFoundError: if the Vite dist folder or index.html is missing.
        RuntimeError:      if the DATA_PLACEHOLDER is not found in index.html.
    """
    if not DIST_DIR.exists():
        raise FileNotFoundError(
            f"Frontend dist folder not found at: {DIST_DIR}\n"
            "Run 'npm run build' inside the frontend directory first."
        )

    index_path = DIST_DIR / "index.html"
    if not index_path.exists():
        raise FileNotFoundError(f"dist/index.html not found at: {index_path}")

    # ── 1. Build JSON snapshot ──────────────────────────────────────────────
    snapshot  = build_snapshot(from_date, to_date)
    json_str  = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))

    # Escape </script> sequences inside JSON to prevent premature tag closure
    json_str = json_str.replace("</", "<\\/")

    injection = f'<script>window.REPORT_DATA={json_str};</script>'

    # ── 2. Patch index.html ─────────────────────────────────────────────────
    html_content = index_path.read_text(encoding="utf-8")
    if DATA_PLACEHOLDER not in html_content:
        raise RuntimeError(
            f"Placeholder '{DATA_PLACEHOLDER}' was not found in dist/index.html.\n"
            "Make sure the placeholder exists in frontend/index.html before running "
            "'npm run build'."
        )
    patched_html = html_content.replace(DATA_PLACEHOLDER, injection)

    # ── 3. Build in-memory ZIP ──────────────────────────────────────────────
    # With vite-plugin-singlefile, everything (JS, CSS, fonts) is inlined
    # into index.html — so the ZIP only needs this one file.
    # Any remaining files in dist/ (e.g. font files not inlined) are included
    # for completeness, but the app works from index.html alone.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # Patched index.html with all app code + data inlined
        zf.writestr("index.html", patched_html.encode("utf-8"))

        # Include any remaining dist assets (fonts as woff2 if not inlined)
        for file_path in DIST_DIR.rglob("*"):
            if file_path.is_file() and file_path.name != "index.html":
                arcname = file_path.relative_to(DIST_DIR).as_posix()
                zf.write(str(file_path), arcname)

    logger.info(
        "ZIP generated in-memory for %s → %s (%d bytes)",
        from_date, to_date, buf.tell(),
    )

    buf.seek(0)
    return buf

