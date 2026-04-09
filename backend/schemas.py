"""
schemas.py – MIS Data Pipeline: Target JSON Schema Definitions
Company: Unreal Estate Habitat Pvt. Ltd. (ID: 110011)

Architecture: DYNAMIC GROUPING
  The pipeline does not hardcode ledger names. Instead, Django's LedgerMapping
  model drives which Tally ledger goes into which group and line item.
  Adding a new property, ledger, or expense category = zero code changes here.

Sign convention (mirrors Tally):
  Positive → Credit / Income / Asset
  Negative → Debit  / Expense / Outflow

Levels:
  Level 1 — Section   ("Income", "Expenses", "Assets")  → hardcoded, accounting never changes
  Level 2 — Group     ("Direct Expenses", "Fixed Assets") → dynamic, driven by LedgerMapping
  Level 3 — Line Item ("Rent", "New Custom Expense")      → dynamic, driven by LedgerMapping
"""

from __future__ import annotations
from typing import TypedDict, Optional


# ---------------------------------------------------------------------------
# Core Building Blocks
# ---------------------------------------------------------------------------

class LineItem(TypedDict):
    """
    One dynamic line item = the aggregated total of all Tally ledgers that
    the accountant has mapped to this name via LedgerMapping.

    breakdown is optional — only populated when the caller requests drill-down
    (e.g. "Security Deposits" → list of individual property deposit ledgers).
    """
    name: str                               # e.g. "Rent", "Consumables"
    amount: float                           # Signed float, INR implied
    breakdown: Optional[list[dict[str, float]]]  # [{"ledger_name": amount}, ...]


class ReportGroup(TypedDict):
    """
    A dynamic collection of LineItems under a named accounting group.
    Items dict uses line item name as key for O(1) lookup.
    """
    group_name: str                         # e.g. "Direct Expenses"
    items: dict[str, LineItem]              # line_item_name → LineItem
    subtotal: float                         # sum of all item amounts


# ---------------------------------------------------------------------------
# 1. Standard Report  (Consolidated P&L  AND  Balance Sheet share this shape)
#    Source sheets: "Consolidated P&l",  "BS-January 26"
#
#    sections layout:
#      P&L   → { "Income": { "Sales Accounts": <ReportGroup>, ... },
#                "Expenses": { "Direct Expenses": <ReportGroup>, ... } }
#      B/S   → { "Equity & Liabilities": { "Capital Account": ..., ... },
#                "Assets":               { "Fixed Assets": ...,    ... } }
# ---------------------------------------------------------------------------

class StandardReport(TypedDict):
    """
    Scalable, DB-driven structure for both the P&L and the Balance Sheet.

    Example JSON output (P&L):
    {
      "report_type": "pnl",
      "period": "1-Apr-25 to 31-Jan-26",
      "company": "Unreal Estate Habitat Private Limited",
      "sections": {
        "Income": {
          "Sales Accounts": {
            "group_name": "Sales Accounts",
            "items": {
              "Koramangala": {"name": "Koramangala", "amount": 8265642.68, "breakdown": null},
              "Hebbal":      {"name": "Hebbal",      "amount": 7448000.00, "breakdown": null}
            },
            "subtotal": 75421489.02
          },
          "Indirect Incomes": { ... }
        },
        "Expenses": {
          "Direct Expenses": {
            "group_name": "Direct Expenses",
            "items": {
              "Consumables":   {"name": "Consumables",   "amount": 3662303.69, "breakdown": null},
              "Pillow/Cover":  {"name": "Pillow/Cover",  "amount": 839365.18,  "breakdown": null},
              "Marketing":     {"name": "Marketing",     "amount": 5000.00,    "breakdown": null}
            },
            "subtotal": 44615529.20
          },
          "Indirect Expenses": { ... }
        }
      },
      "summary": {
        "gross_profit": 30805959.82,
        "net_profit":   18400035.95,
        "total_income": 31043019.88,
        "total_expenses": 31043019.88
      }
    }
    """
    report_type: str                            # "pnl" | "balance_sheet"
    period: str                                 # Human-readable period label
    company: str
    sections: dict[str, dict[str, ReportGroup]] # section → group_name → ReportGroup
    summary: dict[str, float]                   # key totals (gross_profit, net_profit, etc.)


# ---------------------------------------------------------------------------
# 2. Matrix Report  (Building-Wise / Cost-Center Pivot)
#    Source sheet: "Building Wise Data"
#
#    Each MatrixRow = one metric (Gross Sales, Direct Expenses, EBIDTA …)
#    pivoted across all cost-center columns from COST_CENTERS below.
# ---------------------------------------------------------------------------

class MatrixRow(TypedDict):
    """
    One metric row in the building-wise matrix.
    cost_centers keys are the Excel column labels from COST_CENTERS.
    A new property = new key in cost_centers automatically; no schema change.

    Example:
    {
      "row_name": "Net Sales",
      "cost_centers": {
        "Koramangala": 320635.80,
        "EEE":         621888.64,
        "New Branch":  50000.00      ← appears automatically if mapped in DB
      },
      "total": 9425442.65
    }
    """
    row_name: str                   # e.g. "Gross Sales", "EBIDTA"
    cost_centers: dict[str, float]  # column_label → amount
    total: float                    # row sum (= "Total" column in Excel)


class MatrixReport(TypedDict):
    """
    Building-wise P&L matrix for one reporting month.
    The pipeline builds a list[MatrixReport], one per month.

    Fixed row order (matches Excel "Building Wise Data" sheet):
      1. Gross Sales
      2. Net Sales
      3. Other Income
      4. Direct Expenses
      5. Gross Profit
      6. Indirect Expenses
      7. EBIDTA
      8. EBIDTA %
      9. Occupancy %

    Example:
    {
      "period": "2026-01",
      "rows": [
        {"row_name": "Gross Sales",  "cost_centers": { ... }, "total": 10274280.64},
        {"row_name": "Net Sales",    "cost_centers": { ... }, "total": 9425442.65},
        ...
      ]
    }
    """
    period: str             # ISO year-month "YYYY-MM"
    rows: list[MatrixRow]


# ---------------------------------------------------------------------------
# 3. Cash Flow Statement (CFS)
#    Source sheet: "CFS"
#    Three YTD/monthly comparison columns.
# ---------------------------------------------------------------------------

class CFSSection(TypedDict):
    """One section of the CFS (Operating / Investing / Financing)."""
    section_name: str
    line_items: dict[str, float]    # label → signed amount
    subtotal: float


class CFSPeriodBlock(TypedDict):
    """All CFS data for one reporting column (one time window)."""
    label: str                      # e.g. "April 2025 to January 2026"
    operating: CFSSection
    investing: CFSSection
    financing: CFSSection
    opening_cash: float
    closing_cash: float
    net_change: float               # closing_cash − opening_cash


class CashFlowStatement(TypedDict):
    """
    Full statement of cash flows with three comparison columns.

    Example:
    {
      "company": "Unreal Estate Habitat Private Limited",
      "period_ytd":   { "label": "April 2025 to January 2026", "operating": {...}, ... },
      "period_month": { "label": "January 2026", ... },
      "prior_ytd":    { "label": "April 2025 to December 2025", ... }
    }
    """
    company: str
    period_ytd: CFSPeriodBlock
    period_month: CFSPeriodBlock
    prior_ytd: CFSPeriodBlock


# ---------------------------------------------------------------------------
# 4. Top-level MIS Payload Envelope
# ---------------------------------------------------------------------------

class MISPayload(TypedDict):
    """
    Root envelope returned by the pipeline for a given reporting run.
    Serialized to JSON and persisted / sent to the frontend.
    """
    company_id: str                             # "110011"
    company_name: str
    generated_at: str                           # ISO 8601 datetime
    period_start: str                           # "2025-04-01"
    period_end: str                             # "2026-01-31"
    consolidated_pnl: StandardReport            # report_type = "pnl"
    balance_sheet: StandardReport               # report_type = "balance_sheet"
    matrix_pnl: list[MatrixReport]             # one entry per month
    cash_flow_statement: CashFlowStatement


# ---------------------------------------------------------------------------
# Cost Center Configuration  (static config, not a schema)
# ---------------------------------------------------------------------------
# These two constants are used by the PIPELINE LAYER, not by TypedDicts.
# They describe how raw Tally cost centers roll up into matrix columns.

# COST_CENTERS: Ordered list of Excel column labels for the matrix report.
# "Total" is always last and is computed — it is never a real Tally cost center.
COST_CENTERS: list[str] = [
    "JPN 202",
    "Koramangala",
    "EEE",
    "E-City",
    "Kalyan Nagar",
    "Mysore",
    "Coles Park",
    "Mahaveer Celese",
    "Hebbal",
    "CMR",
    "Prestige",
    "Manyata",
    "Hennur",
    "Mysore Frenza",
    "Kora-2",
    "JPN-Hotel",
    "Brigade",
    "Lang Ford",
    "Viman Nagar",
    "LRP",
    "General",
    "Total",
]

# COST_CENTER_GROUPS: Maps each Excel column label → exact Tally cost center
# names (from Master.txt). The pipeline sums all unit-level amounts per group.
COST_CENTER_GROUPS: dict[str, list[str]] = {
    "JPN 202": ["JPN 202"],
    "Koramangala": [
        "Kora -1", "Kora-101", "Kora-102", "Kora-103", "Kora-104",
        "Koramangala 1 General",
    ],
    "EEE": [
        "EEE 101", "EEE 102", "EEE 201", "EEE 202",
        "EEE 301", "EEE 302", "EEE 401", "EEE 402",
        "EEE General",
    ],
    "E-City": [
        "E CITY 101", "E CITY 102", "E CITY 103",
        "E CITY 201", "E CITY 202", "E CITY 203",
        "E CITY 301", "E CITY 302", "E CITY 303",
        "E CITY 401", "E CITY 402", "E CITY 403",
        "E CITY 501", "E CITY 502",
        "E-CITY General",
    ],
    "Kalyan Nagar": [
        "KN 101", "KN 102", "KN 103",
        "KN 201", "KN 202", "KN 203",
        "KN 301", "KN 302", "KN 303",
        "KN General", "Kn PentHouse",
    ],
    "Mysore": [
        "Mysore  101", "Mysore  102", "Mysore  103",
        "Mysore  201", "Mysore  202", "Mysore  203",
        "Mysore  301", "Mysore General",
    ],
    "Coles Park": [
        "CP 301", "CP 302", "CP 303", "CP 304", "CP 402", "Cp General",
    ],
    "Mahaveer Celese": [
        "MC 601", "MC 905", "MC 1004", "MC 1104", "MC General",
    ],
    "Hebbal": [
        "HB 101", "HB 102", "HB 201", "HB 202",
        "HB 301", "HB 302", "HB 401", "HB 402",
        "HB 501", "HB 502", "HB General",
    ],
    "CMR": [
        "CMR 201", "CMR 202", "CMR 203", "CMR 204", "CMR 205", "CMR 206",
        "CMR 301", "CMR 302", "CMR 303", "CMR 304", "CMR 305", "CMR 306",
        "CMR 401", "CMR 402", "CMR 403", "CMR 404", "CMR 405", "CMR 406",
        "CMR General",
    ],
    "Prestige": [
        "Prestige Waterford 11013", "Prestige Waterford 12194",
    ],
    "Manyata": [
        "MN 101", "MN102", "MN 201", "MN202",
        "MN301", "MN302", "MN401", "MN402",
        "MN501", "MN General",
    ],
    "Hennur": [
        "HN 101", "HN 201", "HN 301", "HN 401", "HN 501",
        "HN-General", "Hennur General",
    ],
    "Mysore Frenza": [
        "MF 101", "MF 102", "MF 201", "MF 202",
        "MF 301", "MF 302", "MF 401", "Mf General",
    ],
    "Kora-2": [
        "Kora-001",
        "Kora 2 101", "Kora 2 102", "Kora 2 103", "Kora 2 104",  # floor 1 unit CCs if set up
        "Kora-201", "Kora-202", "Kora-203", "Kora-204",
        "Kora-301", "Kora-302", "Kora-303",
        "Kora 402", "Kora 404", "Kora 503", "Kora 504",
        "Kora Building 2 General",
    ],
    "JPN-Hotel": ["JPN Hotel"],
    "Brigade": ["ED 701"],
    "Lang Ford": [
        "LF 1 F", "LF 2 F", "LF 3 F",
        "LF General", "Lang Ford General",
    ],
    "Viman Nagar": [
        "VN 301", "VN 302", "VN 303", "VN 304", "VN 305",
        "VN 401", "VN 402", "VN 403", "VN 404",
        "VN 501", "VN 502", "VN General",
    ],
    "LRP": ["LRP General"],
    "General": ["General", "MK General"],
    # "Total" → computed by pipeline, no Tally cost centers
}


# ---------------------------------------------------------------------------
# 5. Unit-Wise P&L Configuration
# ---------------------------------------------------------------------------
# Each entry: (display_name, tally_cc, building_group)
# display_name  — column header shown in the UI (matches Excel column labels)
# tally_cc      — exact Tally cost center name for CC breakup API call
#                 None = "General Office" virtual column (see UNIT_GENERAL_CCS)
# building_group — used to render building-level header rows in the frontend

UNIT_COLUMNS: list[tuple[str, str | None, str]] = [
    # ── JPN 202 ────────────────────────────────────────────────────────────
    ("JPN 202",              "JPN 202",                  "JPN 202"),

    # ── Koramangala (small building — 3 units, CCs: Kora-101/102/103) ──────
    # Sales ledgers: "Kormangala 1 Sales A/c", "Koramangala - 2 Sales A/c", etc.
    ("Koramangala-1",        "Kora-101",                 "Koramangala"),
    ("Koramangala-2",        "Kora-102",                 "Koramangala"),
    ("Koramangala-3",        "Kora-103",                 "Koramangala"),

    # ── East End Enclave (EEE) ─────────────────────────────────────────────
    ("EEE 101",              "EEE 101",                  "EEE"),
    ("EEE 102",              "EEE 102",                  "EEE"),
    ("EEE 202",              "EEE 202",                  "EEE"),
    ("EEE 301",              "EEE 301",                  "EEE"),
    ("EEE 302",              "EEE 302",                  "EEE"),
    ("EEE 401",              "EEE 401",                  "EEE"),
    ("EEE 402",              "EEE 402",                  "EEE"),
    ("EEE 201",              "EEE 201",                  "EEE"),

    # ── E-City (single building-level column) ──────────────────────────────
    ("E-City",               "E-CITY General",           "E-City"),

    # ── Kalyan Nagar ───────────────────────────────────────────────────────
    ("KN 101",               "KN 101",                   "Kalyan Nagar"),
    ("KN 102",               "KN 102",                   "Kalyan Nagar"),
    ("KN 103",               "KN 103",                   "Kalyan Nagar"),
    ("KN 201",               "KN 201",                   "Kalyan Nagar"),
    ("KN 202",               "KN 202",                   "Kalyan Nagar"),
    ("KN 203",               "KN 203",                   "Kalyan Nagar"),
    ("KN 301",               "KN 301",                   "Kalyan Nagar"),
    ("KN 302",               "KN 302",                   "Kalyan Nagar"),
    ("KN 303",               "KN 303",                   "Kalyan Nagar"),
    ("KN Pent House",        "Kn PentHouse",             "Kalyan Nagar"),

    # ── Mysore ─────────────────────────────────────────────────────────────
    ("Mysore 101",           "Mysore  101",              "Mysore"),
    ("Mysore 102",           "Mysore  102",              "Mysore"),
    ("Mysore 103",           "Mysore  103",              "Mysore"),
    ("Mysore 201",           "Mysore  201",              "Mysore"),
    ("Mysore 202",           "Mysore  202",              "Mysore"),
    ("Mysore 203",           "Mysore  203",              "Mysore"),
    ("Mysore 301",           "Mysore  301",              "Mysore"),

    # ── Coles Park ─────────────────────────────────────────────────────────
    ("CP 301",               "CP 301",                   "Coles Park"),
    ("CP 302",               "CP 302",                   "Coles Park"),
    ("CP 303",               "CP 303",                   "Coles Park"),
    ("CP 304",               "CP 304",                   "Coles Park"),
    ("CP 402",               "CP 402",                   "Coles Park"),

    # ── Mahaveer Celese (order matches Excel: 1004, 1104, 601, 905) ─────────
    ("MC 1004",              "MC 1004",                  "Mahaveer Celese"),
    ("MC 1104",              "MC 1104",                  "Mahaveer Celese"),
    ("MC 601",               "MC 601",                   "Mahaveer Celese"),
    ("MC 905",               "MC 905",                   "Mahaveer Celese"),

    # ── Hebbal ─────────────────────────────────────────────────────────────
    ("HB 101",               "HB 101",                   "Hebbal"),
    ("HB 102",               "HB 102",                   "Hebbal"),
    ("HB 201",               "HB 201",                   "Hebbal"),
    ("HB 202",               "HB 202",                   "Hebbal"),
    ("HB 301",               "HB 301",                   "Hebbal"),
    ("HB 302",               "HB 302",                   "Hebbal"),
    ("HB 401",               "HB 401",                   "Hebbal"),
    ("HB 402",               "HB 402",                   "Hebbal"),
    ("HB 501",               "HB 501",                   "Hebbal"),
    ("HB 502",               "HB 502",                   "Hebbal"),

    # ── CMR ────────────────────────────────────────────────────────────────
    ("CMR 201",              "CMR 201",                  "CMR"),
    ("CMR 202",              "CMR 202",                  "CMR"),
    ("CMR 203",              "CMR 203",                  "CMR"),
    ("CMR 204",              "CMR 204",                  "CMR"),
    ("CMR 205",              "CMR 205",                  "CMR"),
    ("CMR 206",              "CMR 206",                  "CMR"),
    ("CMR 301",              "CMR 301",                  "CMR"),
    ("CMR 302",              "CMR 302",                  "CMR"),
    ("CMR 303",              "CMR 303",                  "CMR"),
    ("CMR 304",              "CMR 304",                  "CMR"),
    ("CMR 305",              "CMR 305",                  "CMR"),
    ("CMR 306",              "CMR 306",                  "CMR"),
    ("CMR 401",              "CMR 401",                  "CMR"),
    ("CMR 402",              "CMR 402",                  "CMR"),
    ("CMR 403",              "CMR 403",                  "CMR"),
    ("CMR 404",              "CMR 404",                  "CMR"),
    ("CMR 405",              "CMR 405",                  "CMR"),
    ("CMR 406",              "CMR 406",                  "CMR"),

    # ── Prestige ───────────────────────────────────────────────────────────
    ("Prestige 11013",       "Prestige Waterford 11013", "Prestige"),
    ("Prestige 12194",       "Prestige Waterford 12194", "Prestige"),

    # ── Manyata (order matches Excel) ──────────────────────────────────────
    ("MN 101",               "MN 101",                   "Manyata"),
    ("MN 201",               "MN 201",                   "Manyata"),
    ("MN 202",               "MN202",                    "Manyata"),
    ("MN 301",               "MN301",                    "Manyata"),
    ("MN 302",               "MN302",                    "Manyata"),
    ("MN 401",               "MN401",                    "Manyata"),
    ("MN 402",               "MN402",                    "Manyata"),
    ("MN 501",               "MN501",                    "Manyata"),
    ("MN 102",               "MN102",                    "Manyata"),

    # ── Hennur ─────────────────────────────────────────────────────────────
    ("HN 101",               "HN 101",                   "Hennur"),
    ("HN 201",               "HN 201",                   "Hennur"),
    ("HN 301",               "HN 301",                   "Hennur"),
    ("HN 401",               "HN 401",                   "Hennur"),
    ("HN 501",               "HN 501",                   "Hennur"),

    # ── Mysore Frenza ──────────────────────────────────────────────────────
    ("MF 101",               "MF 101",                   "Mysore Frenza"),
    ("MF 102",               "MF 102",                   "Mysore Frenza"),
    ("MF 201",               "MF 201",                   "Mysore Frenza"),
    ("MF 202",               "MF 202",                   "Mysore Frenza"),
    ("MF 301",               "MF 301",                   "Mysore Frenza"),
    ("MF 302",               "MF 302",                   "Mysore Frenza"),
    ("MF 401",               "MF 401",                   "Mysore Frenza"),

    # ── Kora-2 (big Koramangala building) ─────────────────────────────────
    # Display names: "Koramangala-New NNN" (matches Excel exactly).
    # Sales ledgers: "Kora 2 NNN Sales A/c" — matched by display name in services.py.
    # CCs 001/201-204/301-303/402/404/503/504 confirmed in Tally COST_CENTER_GROUPS.
    # CCs for floor 1 (101-104) likely don't exist as separate CCs in Tally;
    # expenses for those units are captured under "Kora Building 2 General".
    ("Koramangala-New 001",  "Kora-001",                 "Kora-2"),
    ("Koramangala-New 101",  "Kora 2 101",               "Kora-2"),
    ("Koramangala-New 102",  "Kora 2 102",               "Kora-2"),
    ("Koramangala-New 103",  "Kora 2 103",               "Kora-2"),
    ("Koramangala-New 104",  "Kora 2 104",               "Kora-2"),
    ("Koramangala-New 201",  "Kora-201",                 "Kora-2"),
    ("Koramangala-New 202",  "Kora-202",                 "Kora-2"),
    ("Koramangala-New 203",  "Kora-203",                 "Kora-2"),
    ("Koramangala-New 204",  "Kora-204",                 "Kora-2"),
    ("Koramangala-New 301",  "Kora-301",                 "Kora-2"),
    ("Koramangala-New 302",  "Kora-302",                 "Kora-2"),
    ("Koramangala-New 303",  "Kora-303",                 "Kora-2"),
    ("Koramangala-New 402",  "Kora 402",                 "Kora-2"),
    ("Koramangala-New 404",  "Kora 404",                 "Kora-2"),
    ("Koramangala-New 503",  "Kora 503",                 "Kora-2"),
    ("Koramangala-New 504",  "Kora 504",                 "Kora-2"),

    # ── JPN Hotel ──────────────────────────────────────────────────────────
    ("JPN-Hotel",            "JPN Hotel",                "JPN-Hotel"),

    # ── Brigade ────────────────────────────────────────────────────────────
    ("ED 701",               "ED 701",                   "Brigade"),

    # ── Lang Ford ──────────────────────────────────────────────────────────
    ("LF 1",                 "LF 1 F",                   "Lang Ford"),
    ("LF 2",                 "LF 2 F",                   "Lang Ford"),
    ("LF 3",                 "LF 3 F",                   "Lang Ford"),

    # ── Viman Nagar ────────────────────────────────────────────────────────
    ("VN 301",               "VN 301",                   "Viman Nagar"),
    ("VN 302",               "VN 302",                   "Viman Nagar"),
    ("VN 303",               "VN 303",                   "Viman Nagar"),
    ("VN 304",               "VN 304",                   "Viman Nagar"),
    ("VN 305",               "VN 305",                   "Viman Nagar"),
    ("VN 401",               "VN 401",                   "Viman Nagar"),
    ("VN 402",               "VN 402",                   "Viman Nagar"),
    ("VN 403",               "VN 403",                   "Viman Nagar"),
    ("VN 404",               "VN 404",                   "Viman Nagar"),
    ("VN 501",               "VN 501",                   "Viman Nagar"),
    ("VN 502",               "VN 502",                   "Viman Nagar"),

    # ── LRP ────────────────────────────────────────────────────────────────
    ("LRP",                  "LRP General",              "LRP"),

    # ── General Office (aggregates all building-overhead General CCs) ───────
    ("General Office",       None,                       "General"),
]

# General / overhead CCs aggregated into the "General Office" unit column
UNIT_GENERAL_CCS: list[str] = [
    "Koramangala 1 General", "EEE General", "E-CITY General",
    "KN General", "Kn PentHouse", "Mysore General", "Cp General",
    "MC General", "HB General", "CMR General", "MN General",
    "HN-General", "Hennur General", "Mf General", "Kora Building 2 General",
    "LF General", "Lang Ford General", "VN General", "MK General",
    # "General" CC removed — it is company-level overhead, handled separately in post-loop block
]

# ---------------------------------------------------------------------------
# 6. Building -> General Cost Center Mapping
# ---------------------------------------------------------------------------
# Maps a building group name (Matches building_group from UNIT_COLUMNS)
# to its respective General Cost Center in Tally.
# 'None' means the building is a single unit and has no general CC.

BUILDING_GENERAL_CC_MAPPING: dict[str, str | None] = {
    "JPN 202": None,
    "Koramangala": "Koramangala 1 General",
    "EEE": "EEE General",
    "E-City": "E-CITY General",
    "Kalyan Nagar": "KN General",
    "Mysore": "Mysore General",
    "Coles Park": "Cp General",
    "Mahaveer Celese": "MC General",
    "Hebbal": "HB General",
    "CMR": "CMR General",
    "Prestige": None,
    "Manyata": "MN General",
    "Hennur": "Hennur General",
    "Mysore Frenza": "Mf General",
    "Kora-2": "Kora Building 2 General",
    "JPN-Hotel": None,
    "Brigade": None,
    "Lang Ford": "LF General",
    "Viman Nagar": "VN General",
    "LRP": "LRP General"
}

