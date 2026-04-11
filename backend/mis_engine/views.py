from django.http import JsonResponse
from django.core.cache import cache
from mis_engine.reports.pnl_bs import StandardReportProcessor
from mis_engine.reports.matrix import MatrixReportProcessor
from mis_engine.reports.unit import UnitReportProcessor

def _get_dates(request):
    from_date = request.GET.get('from', '20250401')
    to_date   = request.GET.get('to',   '20260131')
    if len(from_date) != 8 or not from_date.isdigit():
        raise ValueError("Invalid 'from' date. Expected YYYYMMDD.")
    if len(to_date) != 8 or not to_date.isdigit():
        raise ValueError("Invalid 'to' date. Expected YYYYMMDD.")
    return from_date, to_date

def _handle_error(e):
    import traceback
    return JsonResponse({
        "status": "error",
        "message": str(e),
        "traceback": traceback.format_exc()
    }, status=500)

def _build_payload(processor, data_key, data):
    return {
        "status": "success",
        "data": {
            "company_id": processor.api.COMPANY_ID,
            "company_name": processor.api.COMPANY_ID,
            "period_start": processor.from_date,
            "period_end": processor.to_date,
            data_key: data,
        }
    }

# ── Unified endpoint ──────────────────────────────────────────────────────────
# Returns all four reports in a single response.
# Cached by (from_date, to_date) for 30 minutes.
# Pass ?bust=true to force regeneration (used when the user clicks "Generate").

def get_all_reports(request):
    try:
        from_date, to_date = _get_dates(request)
        bust = request.GET.get('bust', 'false').lower() == 'true'

        cache_key = f"mis_all_{from_date}_{to_date}"

        if bust:
            cache.delete(cache_key)

        cached = cache.get(cache_key)
        if cached is not None:
            return JsonResponse(cached)

        # Run all processors — each shares the same Tally connection session
        std  = StandardReportProcessor(from_date, to_date)
        std_reports = std.process()

        unit = UnitReportProcessor(from_date, to_date)
        unit_report = unit.process()

        from mis_engine.reports.matrix import aggregate_from_unit
        mat_reports = aggregate_from_unit(unit_report)

        payload = {
            "status": "success",
            "data": {
                "company_id":   std.api.COMPANY_ID,
                "company_name": std.api.COMPANY_ID,
                "period_start": from_date,
                "period_end":   to_date,
                "consolidated_pnl": std_reports["pnl"],
                "balance_sheet":    std_reports["balance_sheet"],
                "matrix_pnl":       mat_reports,
                "unit_wise":        unit_report,
            }
        }

        cache.set(cache_key, payload)
        return JsonResponse(payload)

    except Exception as e:
        return _handle_error(e)

# ── Individual endpoints (kept for backwards compatibility / direct testing) ──

def get_pnl(request):
    try:
        from_date, to_date = _get_dates(request)
        processor = StandardReportProcessor(from_date, to_date)
        reports = processor.process()
        return JsonResponse(_build_payload(processor, "consolidated_pnl", reports["pnl"]))
    except Exception as e:
        return _handle_error(e)

def get_balance_sheet(request):
    try:
        from_date, to_date = _get_dates(request)
        processor = StandardReportProcessor(from_date, to_date)
        reports = processor.process()
        return JsonResponse(_build_payload(processor, "balance_sheet", reports["balance_sheet"]))
    except Exception as e:
        return _handle_error(e)

def get_matrix(request):
    try:
        from_date, to_date = _get_dates(request)
        processor = MatrixReportProcessor(from_date, to_date)
        reports = processor.process()
        return JsonResponse(_build_payload(processor, "matrix_pnl", reports))
    except Exception as e:
        return _handle_error(e)

def get_unit_wise(request):
    try:
        from_date, to_date = _get_dates(request)
        processor = UnitReportProcessor(from_date, to_date)
        report = processor.process()
        return JsonResponse(_build_payload(processor, "unit_wise", report))
    except Exception as e:
        return _handle_error(e)

def get_cash_flow(request):
    try:
        p1_from = request.GET.get("p1_from", "")
        p1_to   = request.GET.get("p1_to",   "")
        p2_from = request.GET.get("p2_from", "")
        p2_to   = request.GET.get("p2_to",   "")
        for v in (p1_from, p1_to, p2_from, p2_to):
            if len(v) != 8 or not v.isdigit():
                raise ValueError(f"Invalid date '{v}'. Expected YYYYMMDD.")
        from mis_engine.reports.cashflow import CashFlowProcessor
        data = CashFlowProcessor(p1_from, p1_to, p2_from, p2_to).process()
        return JsonResponse({"status": "success", "data": data})
    except Exception as e:
        return _handle_error(e)


def download_report(request):
    """
    GET /api/reports/download/?from=20250401&to=20260131

    Generates a fully self-contained offline interactive report ZIP and
    streams it to the browser as a file download. The ZIP contains the
    pre-built React dashboard with full report data injected inline —
    the client only needs to extract the ZIP and open index.html.
    """
    try:
        from_date, to_date = _get_dates(request)
        from mis_engine.export import generate_report_zip
        from django.http import HttpResponse

        zip_buf  = generate_report_zip(from_date, to_date)
        filename = f"MIS_Report_{from_date}_to_{to_date}.zip"

        response = HttpResponse(
            zip_buf.read(),
            content_type="application/zip",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except FileNotFoundError as e:
        return JsonResponse(
            {"status": "error", "message": str(e)},
            status=503,
        )
    except Exception as e:
        return _handle_error(e)
