# All Reports — Code Documentation

**Company:** Unreal Estate Habitat Private Limited  
**Stack:** Django (backend) · React + Vite (frontend) · TallyPrime XML API (data source)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Shared Infrastructure](#2-shared-infrastructure)
   - [Base Processor](#21-base-processor--backendmis_enginereportsbasepy)
   - [Data Schemas](#22-data-schemas--backendschemaspy)
   - [Tally API Client](#23-tally-api-client--backendtally_apipy)
   - [Django View](#24-django-view--backendmis_engineviewspy)
3. [Consolidated P&L Report](#3-consolidated-pl-report)
   - [Processor](#31-processor--backendmis_enginereportspnl_bspy)
   - [JSON Structure](#32-json-structure)
4. [Balance Sheet Report](#4-balance-sheet-report)
   - [Processor](#41-processor--backendmis_enginereportspnl_bspy-shared-with-pl)
   - [JSON Structure](#42-json-structure)
5. [Building-Wise Matrix P&L Report](#5-building-wise-matrix-pl-report)
   - [Processor](#51-processor--backendmis_enginereportsmatrixpy)
   - [Expense Source Rules](#52-expense-source-rules)
   - [EBITDA & PBT Formulas](#53-ebitda--pbt-formulas)
   - [General CC Overhead Distribution](#54-general-cc-overhead-distribution)
   - [JSON Structure](#55-json-structure)
6. [Unit-Wise P&L Report](#6-unit-wise-pl-report)
   - [Processor](#61-processor--backendmis_enginereportsunitpy)
   - [Sales Attribution](#62-sales-attribution)
   - [Expense Source Rules](#63-expense-source-rules)
   - [Building General CC Pre-fetch](#64-building-general-cc-pre-fetch)
   - [Company General CC Post-loop](#65-company-general-cc-post-loop)
   - [EBITDA & PBT Formulas](#66-ebitda--pbt-formulas)
   - [JSON Structure](#67-json-structure)
7. [Sign Convention](#7-sign-convention)
8. [Key Schemas — `backend/schemas.py`](#8-key-schemas--backendschemaspy)
9. [Known Issues & Debugging](#9-known-issues--debugging)

---

## 1. Architecture Overview

```
TallyPrime (127.0.0.1:9000)
      │
      │  XML over HTTP
      ▼
backend/tally_api.py              ← TallyAPIClient
      │
      ├──────────────────────────────────────────────┐
      │                                              │
      ▼                                              ▼
mis_engine/reports/pnl_bs.py      mis_engine/reports/matrix.py
StandardReportProcessor           MatrixReportProcessor
 ├─ consolidated_pnl               building-wise P&L columns
 └─ balance_sheet
      │                                              │
      └──────────────────┬───────────────────────────┘
                         │
              mis_engine/reports/unit.py
              UnitReportProcessor
               per-unit P&L columns
                         │
                         ▼
              mis_engine/views.py  ← get_all_reports()
                         │
                         │  JSON (cached 30 min)
                         ▼
              frontend/src/utils/api.js
                         │
                         ▼
              frontend/src/context/ReportContext.jsx
                         │
              ┌──────────┴──────────┬─────────────┐
              ▼                     ▼              ▼
         PnLPage.jsx        MatrixPage.jsx   UnitWisePage.jsx
         BalanceSheetPage.jsx
```

All four reports are fetched in a **single HTTP call** to `GET /api/reports/all/`. The response is cached server-side for 30 minutes; clicking **Generate Report** sends `?bust=true` to invalidate and refresh.

---

## 2. Shared Infrastructure

### 2.1 Base Processor — `backend/mis_engine/reports/base.py`

Every report processor inherits from `BaseReportProcessor`.

```python
class BaseReportProcessor:
    def __init__(self, from_date: str, to_date: str):
        self.from_date = from_date          # "YYYYMMDD"
        self.to_date   = to_date
        self.api       = TallyAPIClient(timeout=120)
        self._raw_data = None               # lazy
        self._mappings = None               # lazy
```

| Property / Method | Description |
|---|---|
| `self.api` | `TallyAPIClient` singleton for this run; caches CC breakup responses internally |
| `self.raw_data` | Lazy-loads Trial Balance via `fetch_trial_balance()` on first access |
| `self.mappings` | Lazy-loads `{tally_ledger_name → LedgerMapping}` from DB on first access |
| `_add_to_report(report, section, group, line_item, amount)` | Upserts into `StandardReport` structure, accumulates subtotals |

---

### 2.2 Data Schemas — `backend/schemas.py`

#### `UNIT_COLUMNS: list[tuple[str, str | None, str]]`

Defines every unit column in the unit-wise report:
```python
("display_name",    "tally_cc_name",       "building_group")
("Koramangala-1",   "Kora-101",            "Koramangala")
("KN 101",          "KN 101",              "Kalyan Nagar")
("KN Pent House",   "Kn PentHouse",        "Kalyan Nagar")   # excluded from salary ÷
("E-City",          "E-CITY General",      "E-City")         # unit CC = General CC
("General Office",  None,                  "General")        # aggregates all General CCs
```

#### `COST_CENTER_GROUPS: dict[str, list[str]]`

Maps each matrix column label to its constituent Tally cost centers:
```python
"Koramangala": ["Kora -1", "Kora-101", "Kora-102", "Kora-103", "Kora-104", "Koramangala 1 General"]
"Kalyan Nagar": ["KN 101", ..., "KN 303", "KN General", "Kn PentHouse"]
"General":      ["General", "MK General"]
```

#### `BUILDING_GENERAL_CC_MAPPING: dict[str, str | None]`

Maps building group name to its General CC in Tally:
```python
"Koramangala": "Koramangala 1 General"
"Kalyan Nagar": "KN General"
"EEE":          "EEE General"
"JPN 202":      None    # single unit; no General CC
```

#### `UNIT_GENERAL_CCS: list[str]`

All building-level General CCs aggregated in the "General Office" unit column.  
**Does NOT include** `"General"` (the company-level overhead CC) — that is handled separately in the post-loop block.

---

### 2.3 Tally API Client — `backend/tally_api.py`

All report processors share one `TallyAPIClient(timeout=120)` instance per request.

#### Host

Default host is `127.0.0.1` (not `localhost`). On this Windows machine `localhost` resolves to `::1` (IPv6) which hits a different process; Tally listens on IPv4 `0.0.0.0:9000` only.

#### Key methods used by reports

| Method | Used by | Description |
|---|---|---|
| `fetch_trial_balance(from, to)` | All (via `raw_data`) | Returns all non-zero ledger closing balances for the period |
| `fetch_pnl_report(from, to)` | P&L (primary) | Tally's own Profit & Loss report — pre-classified, no DB needed |
| `fetch_balance_sheet(to)` | Balance Sheet | Group-level balance sheet (not exploded) |
| `fetch_cost_center_breakup(from, to, cc_name)` | Matrix, Unit | Cost Centre Breakup for one CC; results cached by CC name |
| `fetch_ledger_vouchers(name, from, to)` | Unit (GST/Host) | Voucher list for one ledger |

#### `fetch_cost_center_breakup()` return type

```python
list[LedgerBalance]   # where LedgerBalance = {"ledger_name": str, "amount": float, "dr_cr": "Dr"|"Cr"}
```

`amount` is always **absolute** (positive); `dr_cr` encodes the sign. Sign correction is done at call site:
```python
signed = -ledger["amount"] if ledger["dr_cr"] == "Dr" else ledger["amount"]
# Dr expenses → negative; Cr income → positive
```

Results are cached per CC name within one `TallyAPIClient` instance, so calling `fetch_cost_center_breakup("KN General", ...)` a second time returns the in-memory cache instantly.

---

### 2.4 Django View — `backend/mis_engine/views.py`

#### `GET /api/reports/all/`

| Param | Format | Default | Purpose |
|-------|--------|---------|---------|
| `from` | `YYYYMMDD` | `20250401` | Period start |
| `to` | `YYYYMMDD` | `20260131` | Period end |
| `bust` | `true`/`false` | `false` | Invalidate cache before fetching |

**Execution order (sequential):**
1. `StandardReportProcessor` → P&L + Balance Sheet
2. `MatrixReportProcessor` → Building-wise matrix
3. `UnitReportProcessor` → Per-unit P&L

Because all three use the same `TallyAPIClient` instance **per processor** (not shared), CC breakup results are not shared between processors. However, since Django's development server is multi-threaded, the three processors still run in the same OS thread sequentially.

**Cache key:** `mis_all_{from}_{to}` — 30-minute Django `locmem` cache.

---

## 3. Consolidated P&L Report

### 3.1 Processor — `backend/mis_engine/reports/pnl_bs.py`

**Class:** `StandardReportProcessor(BaseReportProcessor)`

#### Two-path P&L assembly

```
fetch_pnl_report()
    ├── Success → loop Tally's own sections → _add_to_report()
    │            (Tally pre-classifies; no DB mapping needed)
    └── Failure / empty
           → fetch_trial_balance() + LedgerMapping DB lookup
             → loop ledgers → map section/group/line_item → _add_to_report()
```

#### Section mapping (primary path)

| Tally section | `report_section` | `report_group` |
|---|---|---|
| `Sales Accounts` | `Income` | `Sales Accounts` |
| `Direct Incomes` | `Income` | `Direct Incomes` |
| `Direct Expenses` | `Direct Expenses` | `Direct Expenses` |
| `Indirect Incomes` | `Income` | `Indirect Incomes` |
| `Indirect Expenses` | `Expenses` | `Indirect Expenses` |
| `Cost of Sales :` | *(skipped — parent header)* | — |

#### Summary calculations

```python
total_income      = sum of Income group subtotals           (positive)
direct_expenses   = sum of Direct Expenses group subtotals  (negative)
indirect_expenses = sum of Expenses group subtotals         (negative)
gross_profit      = total_income + direct_expenses          (income − |direct_exp|)
net_profit        = gross_profit + indirect_expenses
```

---

### 3.2 JSON Structure

```json
{
  "report_type": "pnl",
  "period": "20260101 to 20260131",
  "company": "Unreal Estate Habitat Private Limited",
  "sections": {
    "Income": {
      "Sales Accounts": {
        "group_name": "Sales Accounts",
        "subtotal": 7541428.37,
        "items": {
          "Koramangala": { "name": "Koramangala", "amount": 826564.68, "breakdown": [] }
        }
      },
      "Direct Incomes":   { "group_name": "...", "subtotal": 0.0, "items": {} },
      "Indirect Incomes": { "group_name": "...", "subtotal": 23706.06, "items": {} }
    },
    "Direct Expenses": {
      "Direct Expenses": {
        "group_name": "Direct Expenses",
        "subtotal": -4461552.92,
        "items": {
          "Electricity": { "name": "Electricity", "amount": -246269.66, "breakdown": [] },
          "Rent":        { "name": "Rent",        "amount": -3408570.00, "breakdown": [] }
        }
      }
    },
    "Expenses": {
      "Indirect Expenses": {
        "group_name": "Indirect Expenses",
        "subtotal": -1264298.39,
        "items": {
          "Salary A/c":        { "name": "Salary A/c",        "amount": -721077.60, "breakdown": [] },
          "Professional Fees": { "name": "Professional Fees", "amount": -80500.00,  "breakdown": [] }
        }
      }
    }
  },
  "summary": {
    "total_income":       7565154.43,
    "direct_expenses":   -4461552.92,
    "indirect_expenses": -1264298.39,
    "total_expenses":    -5725851.31,
    "gross_profit":       3103601.51,
    "net_profit":         1839303.12
  }
}
```

---

## 4. Balance Sheet Report

### 4.1 Processor — `backend/mis_engine/reports/pnl_bs.py` (shared with P&L)

Balance Sheet is assembled inside the same `StandardReportProcessor.process()` call that produces the P&L. It uses **group-level** Tally data (not exploded to individual ledgers).

#### Data source

`api.fetch_balance_sheet(to_date)` — requests the `Balance Sheet` report without `EXPLODEFLAG`, returning one row per top-level group.

#### Group-to-section mapping (hardcoded)

| Tally group | `section` | `group` |
|---|---|---|
| `Capital Account` | `Equity & Liabilities` | `Capital Account` |
| `Loans (Liability)` | `Equity & Liabilities` | `Loans (Liability)` |
| `Current Liabilities` | `Equity & Liabilities` | `Current Liabilities` |
| `Suspense A/c` | `Equity & Liabilities` | `Suspense` |
| `Profit & Loss A/c` | `Equity & Liabilities` | `Profit & Loss A/c` |
| `Fixed Assets` | `Assets` | `Fixed Assets` |
| `Current Assets` | `Assets` | `Current Assets` |
| `Loans & Advances (Asset)` | `Assets` | `Current Assets` |
| `Investments` | `Assets` | `Investments` |
| *(unrecognised, Cr)* | `Equity & Liabilities` | `Other Liabilities` |
| *(unrecognised, Dr)* | `Assets` | `Other Assets` |

---

### 4.2 JSON Structure

Same `StandardReport` shape as P&L, with `"report_type": "balance_sheet"`. Groups appear as line items (not individual ledgers):

```json
{
  "report_type": "balance_sheet",
  "period": "20260101 to 20260131",
  "company": "Unreal Estate Habitat Private Limited",
  "sections": {
    "Equity & Liabilities": {
      "Capital Account": {
        "group_name": "Capital Account",
        "subtotal": 100000.00,
        "items": {
          "Capital Account": { "name": "Capital Account", "amount": 100000.00, "breakdown": [] }
        }
      },
      "Current Liabilities": { ... }
    },
    "Assets": {
      "Fixed Assets": {
        "group_name": "Fixed Assets",
        "subtotal": -76307900.04,
        "items": {
          "Fixed Assets": { "name": "Fixed Assets", "amount": -76307900.04, "breakdown": [] }
        }
      },
      "Current Assets": { ... }
    }
  },
  "summary": {}
}
```

---

## 5. Building-Wise Matrix P&L Report

### 5.1 Processor — `backend/mis_engine/reports/matrix.py`

**Class:** `MatrixReportProcessor(BaseReportProcessor)`

Produces a single table where **rows** are P&L line items and **columns** are buildings + a Total column.

#### Column definitions (from `COST_CENTERS`)

```
JPN 202 | Koramangala | EEE | E-City | Kalyan Nagar | Mysore | Coles Park |
Mahaveer Celese | Hebbal | CMR | Prestige | Manyata | Hennur | Mysore Frenza |
Kora-2 | JPN-Hotel | Brigade | Lang Ford | Viman Nagar | LRP | General | Total
```

#### Row definitions (ordered)

| Row | Notes |
|---|---|
| `Gross Sales` | From Trial Balance (Excluded/sales ledgers via `LedgerMapping.cost_center`) |
| `Net Sales` | Same as Gross Sales (GST/host fee breakdown not done at building level) |
| `Other Income` | Indirect income CCs summed per building |
| `Direct Expenses` | All Direct Expense CCs summed per building (absolute value) |
| `Gross Profit` | `Net Sales + Other Income − Direct Expenses` |
| `Indirect Expenses` | All Indirect Expense CCs + allocated General CC overhead |
| `EBIDTA` | `Gross Profit − Indirect Expenses` (Interest excluded) |
| `EBIDTA %` | `EBITDA / Net Sales × 100` |
| `Interest` | Separated from Indirect Expenses; stays in `General` column only |
| `PBT` | `EBITDA − Interest` |
| `Occupancy %` | Not yet populated (placeholder, all zeros) |

---

### 5.2 Expense Source Rules

#### Sales (Pass 1 — unit-level sales ledgers)

Trial Balance ledgers where `LedgerMapping.report_section == "Excluded"` and `"sales"` in the ledger name. The `cost_center` field on the mapping determines which building column they credit.

#### Sales (Pass 2 — building-level sales ledgers)

Trial Balance ledgers where `report_group == "Sales Accounts"` and `report_section == "Income"`. Only applied to building columns that had no unit-level sales in Pass 1.

#### Expenses (CC Breakup loop)

For each building column, all Tally cost centers listed in `COST_CENTER_GROUPS[col_name]` are fetched via `fetch_cost_center_breakup()`. Each ledger result is routed:

| Condition | Destination |
|---|---|
| `report_group == "Sales Accounts"` | Skipped |
| `report_group == "Indirect Incomes"` | `Other Income` |
| `report_section == "Direct Expenses"` or `report_group == "Direct Expenses"` | `Direct Expenses` |
| `"Indirect" in report_group` and `"interest"` in `line_item.lower()` | `Interest` |
| `"Indirect" in report_group` (all other) | `Indirect Expenses` |

---

### 5.3 EBITDA & PBT Formulas

```python
gp     = ns + oi - de           # Gross Profit = Net Sales + Other Income - Direct Expenses
ebitda = gp - ie                # EBITDA = GP - Indirect Expenses (Interest excluded)
pbt    = ebitda - interest      # PBT = EBITDA - Interest

# All values are absolute (positive) in matrix_rows except derived rows.
# de and ie are accumulated as absolute values from fetch_cost_center_breakup().
```

---

### 5.4 General CC Overhead Distribution

The `"General"` Tally CC contains company-level overhead (Office Admin, Conveyance, Professional Fees, GRM Salary, Interest Paid, Bank Charges, Rates & Taxes). It is already included in `COST_CENTER_GROUPS["General"]` so it appears in the **General column** in full.

Additionally, three overhead categories are **distributed pro-rata** to every building column:

```
Overhead distributed = Office Admin + Conveyance + (Professional Fees + Salary A/c)
```

Distribution logic:
```python
eligible_per_bldg[bldg] = count of units in UNIT_COLUMNS for that building,
                           excluding: cc is None, bldg=="General", "penthouse" in cc.lower()

share_for_building = (eligible_per_bldg[bldg] / total_eligible) × overhead_total
matrix_rows["Indirect Expenses"][bldg] += share_for_building
```

The **General column** retains the full overhead amounts from the CC loop; building columns receive their proportional share on top. This means Indirect Expenses in the Total row includes the General column overhead + the sum of building shares (intentional — General column is an overhead pool, not a production unit).

**Interest Paid is NOT distributed** — it stays in the General column only.

---

### 5.5 JSON Structure

```json
[
  {
    "period": "20260101 to 20260131",
    "rows": [
      {
        "row_name": "Gross Sales",
        "cost_centers": {
          "Koramangala": 1250000.0,
          "Kalyan Nagar": 980000.0,
          "General": 0.0,
          "Total": 8400000.0
        },
        "total": 8400000.0
      },
      { "row_name": "Net Sales",        "cost_centers": { ... }, "total": 8400000.0 },
      { "row_name": "Other Income",     "cost_centers": { ... }, "total": 12000.0   },
      { "row_name": "Direct Expenses",  "cost_centers": { ... }, "total": 4200000.0 },
      { "row_name": "Gross Profit",     "cost_centers": { ... }, "total": 4212000.0 },
      { "row_name": "Indirect Expenses","cost_centers": { ... }, "total": 1400000.0 },
      { "row_name": "EBIDTA",           "cost_centers": { ... }, "total": 2812000.0 },
      { "row_name": "EBIDTA %",         "cost_centers": { ... }, "total": 33.47     },
      { "row_name": "Interest",         "cost_centers": { "General": 190710.0, ... }, "total": 190710.0 },
      { "row_name": "PBT",              "cost_centers": { ... }, "total": 2621290.0 },
      { "row_name": "Occupancy %",      "cost_centers": { ... }, "total": 0.0       }
    ]
  }
]
```

---

## 6. Unit-Wise P&L Report

### 6.1 Processor — `backend/mis_engine/reports/unit.py`

**Class:** `UnitReportProcessor(BaseReportProcessor)`

Produces a per-unit P&L where each column is one property unit (e.g., "KN 101", "EEE 401"). Columns are defined by `UNIT_COLUMNS` in `schemas.py` (~100 entries). The last column is always `"General Office"` which aggregates all building-level General CCs.

---

### 6.2 Sales Attribution

#### Gross Sales

Trial Balance ledgers with `report_section == "Excluded"` and `"sales"` in the name are matched to a unit column via `_match_sales_ledger_to_unit()`:

1. **Kora-2 regex** — matches `"kora 2 NNN"` → `"Koramangala-New NNN"`
2. **Koramangala small regex** — matches `"koromangala N sales"` → `"Koramangala-N"`
3. **CC name substring** — normalises both ledger name and CC name (strip whitespace/hyphens/underscores, lowercase); matches longest CC name first to avoid false-positive shorter matches

#### GST

DB ledgers containing `"output"` + `"gst"` (SGST excluded). For each voucher:
- Scans all voucher line-item names for a sales ledger
- Maps that sales ledger to a unit via `_match_sales_ledger_to_unit()`
- CGST multiplied by 2.0 (to reconstruct full GST = CGST + SGST); IGST multiplied by 1.0

#### Host Fees

DB ledgers containing `"host fee"`. Same voucher scan as GST.

#### Final Gross Sales

```python
d["gross_sales"] = gross_sales + gst + host_fees
```

---

### 6.3 Expense Source Rules

Expenses are fetched from Tally Cost Centre Breakup reports, not Trial Balance. Each unit column has exactly one source (except General Office which aggregates many):

| Unit type | Source |
|---|---|
| Normal unit (`cc` is not None) | `fetch_cost_center_breakup(cc)` for that unit's own CC |
| `"General Office"` (`cc` is None) | All CCs in `UNIT_GENERAL_CCS` (all building General CCs, excluding the company `"General"` CC) |

#### Routing per ledger

```
report_group == "Sales Accounts"          → skip
report_group == "Indirect Incomes"        → indirect_income (float, not dict)
report_section or group == "Direct Expenses":
    line_item == "Salary"                 → SKIP (salary comes from building General CC)
    anything else                         → direct_exp[line_item]
"Indirect" in report_group OR
    (section == "Expenses" and "Direct" not in group):
    "interest" in line_item.lower()       → d["interest"]  (excluded from EBITDA)
    anything else                         → indirect_exp[normalised_key]
```

#### Key normalisation

Line item names from `LedgerMapping` may vary in spacing. A `_INDIRECT_KEY_MAP` normalises them at insert time:

| DB line_item | Canonical key |
|---|---|
| `"Conveyance / Travelling Expenses"` | `"Conveyance/ Travelling Expenses"` |
| `"Conveyance/Travelling Expenses"` | `"Conveyance/ Travelling Expenses"` |
| `"Rates and Taxes"` | `"Rates and taxes"` |

---

### 6.4 Building General CC Pre-fetch

Before the main per-unit CC loop, four direct expenses are fetched from each building's **General CC** and distributed equally to that building's eligible units.

**Eligible units** for a building = units in `UNIT_COLUMNS` where:
- `cc is not None`
- `bldg != "General"`
- `"penthouse" not in cc.lower()`

| Expense | Source | Distribution rule |
|---|---|---|
| **Salary** | Building General CC | Equally divided, excluding penthouse |
| **Consumables** | Building General CC ÷ units + per-unit CC directly | Sum of general share + unit's own CC amount |
| **Electricity** | Building General CC ÷ units + per-unit CC | Sum |
| **Maintenance** | Building General CC ÷ units + per-unit CC | Sum |

**Why salary only from General CC:** Staff salary is booked to the building General CC (e.g., `"KN General"`), not to individual unit CCs. Per-unit CC salary is skipped via the `line == "Salary": pass` guard.

**Example (Jan 2026):**

| Building | General CC | Total Salary | Eligible Units | Per-unit |
|---|---|---|---|---|
| Kalyan Nagar | KN General | −48,000 | 9 (excl. Kn PentHouse) | −5,333 |
| EEE | EEE General | −30,400 | 8 | −3,800 |

---

### 6.5 Company General CC Post-loop

After the per-unit CC loop, the **company-level** `"General"` Tally CC is fetched once. This CC holds company-wide overhead (Office Admin, Conveyance, Professional Fees, GRM Salary, Interest Paid, Bank Charges, Rates & Taxes).

#### Full amounts → General Office column

Every ledger from the `"General"` CC is routed into the `"General Office"` unit column with special handling:

| Ledger / condition | General Office destination |
|---|---|
| Direct Expenses, `line_item != "Salary"` | `direct_exp[line_item]` |
| `line_item == "Salary"` (GRM salary) | `indirect_exp["Professional Fees/GRM Salary"]` |
| `"interest"` in `line_item.lower()` | `d["interest"]` (excluded from EBITDA) |
| `"professional"` in ledger name/line_item | `indirect_exp["Professional Fees/GRM Salary"]` |
| Other Indirect Expenses | `indirect_exp[normalised_key]` |

#### Distributed shares → units with rent

Three overhead amounts are divided equally across **units that have a non-zero Rent** in their `direct_exp`:

| Overhead | Added to each unit-with-rent |
|---|---|
| Office Admin | `indirect_exp["Office Admin"]` |
| Conveyance / Travelling Expenses | `indirect_exp["Conveyance/ Travelling Expenses"]` |
| Professional Fees + Salary A/c combined | `indirect_exp["Professional Fees/GRM Salary"]` |

**Why rent-based filter:** Units with no rent are vacant or pre-operational. Allocating overhead only to occupied units gives a meaningful per-unit cost.

**Interest Paid is NOT distributed** to individual units — it stays in General Office only.

---

### 6.6 EBITDA & PBT Formulas

```python
net_sales         = gross_sales − gst − host_fees
net_revenue       = net_sales + indirect_income
total_direct_exp  = sum(direct_exp.values())          # negative (expenses)
gross_profit      = net_sales + total_direct_exp      # = net_sales − |direct_exp|
total_indirect_exp = sum(indirect_exp.values())       # negative; excludes interest
ebitda            = gross_profit + total_indirect_exp # = GP − |indirect_exp|
pbt               = ebitda + interest                 # interest is negative → reduces PBT
```

**Row display order:**

Direct expenses: `Rent → Salary → Consumables → Electricity → Water Bill → Maintenance → Repairs → House Hold Items → Pillow Covers/Bed Sheets/Clothing → Brokerage`

Indirect expenses: `Office Admin → Conveyance/ Travelling Expenses → Professional Fees/GRM Salary → Office Rent → Rates and taxes → In Eligible GST Input → CXO Salary`

Any expense with a line_item not in those lists is appended alphabetically.

---

### 6.7 JSON Structure

```json
{
  "period": "20260101 to 20260131",
  "columns": [
    ["JPN 202",         "JPN 202"],
    ["Koramangala-1",   "Koramangala"],
    ["KN 101",          "Kalyan Nagar"],
    ["General Office",  "General"]
  ],
  "direct_rows":   ["Rent", "Salary", "Consumables", "Electricity", "Maintenance"],
  "indirect_rows": ["Office Admin", "Conveyance/ Travelling Expenses", "Professional Fees/GRM Salary"],
  "data": {
    "KN 101": {
      "building":          "Kalyan Nagar",
      "cc":                "KN 101",
      "gross_sales":       180000.0,
      "gst":               16200.0,
      "host_fees":         1800.0,
      "indirect_income":   0.0,
      "direct_exp": {
        "Rent":         -31500.0,
        "Salary":       -5333.0,
        "Consumables":  -3713.0,
        "Electricity":  -2127.0,
        "Maintenance":  -300.0
      },
      "indirect_exp": {
        "Office Admin":                      -2086.0,
        "Conveyance/ Travelling Expenses":   -549.0,
        "Professional Fees/GRM Salary":      -6988.0
      },
      "interest":          0.0,
      "net_sales":         162000.0,
      "net_revenue":       162000.0,
      "total_direct_exp":  -42973.0,
      "gross_profit":      119027.0,
      "total_indirect_exp":-9623.0,
      "ebitda":            109404.0,
      "depreciation":      0.0,
      "pbt":               109404.0
    },
    "General Office": {
      "building": "General",
      "cc": null,
      "gross_sales": 0.0,
      "direct_exp": {
        "Consumables": -187334.0,
        "Maintenance": -7200.0
      },
      "indirect_exp": {
        "Conveyance/ Travelling Expenses":   -71551.0,
        "Bank Charges":                      -599.0,
        "Office Admin":                      -208617.0,
        "Professional Fees/GRM Salary":      -698763.0,
        "Rates and taxes":                   -2000.0
      },
      "interest":   -190710.0,
      "ebitda":     -1521187.0,
      "pbt":        -1711897.0
    }
  }
}
```

---

## 7. Sign Convention

Consistent throughout the entire pipeline:

| Type | Sign | Examples |
|------|------|---------|
| Income / Credit | Positive `+` | Sales, Indirect Income |
| Expense / Debit | Negative `−` | Rent, Salary, Office Admin |
| EBITDA (profit) | Positive `+` if profitable | |
| EBITDA (loss) | Negative `−` | General Office column |
| Interest | Negative `−` | Financing cost |

`fetch_cost_center_breakup()` returns absolute amounts — sign correction is applied at each call site via `lamount = -ledger["amount"] if ledger["dr_cr"] == "Dr" else ledger["amount"]`.

The frontend always displays with `Math.abs()` and a `₹` prefix.

---

## 8. Key Schemas — `backend/schemas.py`

### `LedgerMapping` (Django Model)

| Field | Type | Description |
|---|---|---|
| `tally_ledger_name` | `CharField(unique)` | Exact Tally ledger name |
| `report_section` | `CharField` | `"Income"`, `"Direct Expenses"`, `"Expenses"`, `"Excluded"` |
| `report_group` | `CharField` | `"Sales Accounts"`, `"Direct Expenses"`, `"Indirect Expenses"`, `"Indirect Incomes"` |
| `line_item` | `CharField` | Display name: `"Rent"`, `"Salary"`, `"Electricity"`, … |
| `cost_center` | `CharField(nullable)` | Building column for matrix report (e.g., `"Koramangala"`, `"Hebbal"`) |

### Key routing rules derived from `LedgerMapping`

| `report_section` | `report_group` | Used in |
|---|---|---|
| `Direct Expenses` | `Direct Expenses` | Unit `direct_exp`, Matrix `Direct Expenses` |
| `Expenses` | `Indirect Expenses` | Unit `indirect_exp`, Matrix `Indirect Expenses` |
| `Income` | `Indirect Incomes` | Unit `indirect_income`, Matrix `Other Income` |
| `Excluded` | *(any)* | Sales ledgers — gross sales only, not expenses |

---

## 9. Known Issues & Debugging

### Tally not responding
- **Symptom:** HTTP 500; `ConnectionError` in backend log
- **Fix:** Open TallyPrime, load "Unreal Estate Habitat Private Limited", enable HTTP XML Server on port 9000
- **Note:** Always use `127.0.0.1:9000`, not `localhost:9000`. On this machine `localhost` resolves to `::1` (IPv6) which hits a different process.

### Wrong salary amounts in unit report
- **Symptom:** All units show 0 salary, or salary differs from expected per-unit split
- **Cause A:** `"Salary A/c"` not mapped with `report_section="Direct Expenses"` in `LedgerMapping`
- **Cause B:** Building General CC (e.g., `"KN General"`) has no `"Salary A/c"` transactions for the period
- **Debug:** Check `BUILDING_GENERAL_CC_MAPPING` in `schemas.py`; verify the General CC has salary in Tally for the period

### Office Admin / Conveyance / Professional Fees showing 0 in units
- **Cause:** The `"General"` Tally CC has no transactions for the period, or no units have non-zero Rent (the eligibility filter)
- **Debug:** Check `_units_with_rent` count in `unit.py` post-loop block; verify `"General"` CC has data in Tally

### Duplicate indirect expense rows in unit report
- **Symptom:** Two rows for Conveyance — `"Conveyance / Travelling Expenses"` and `"Conveyance/ Travelling Expenses"`
- **Cause:** `LedgerMapping.line_item` has inconsistent spacing for a ledger; not covered by `_INDIRECT_KEY_MAP`
- **Fix:** Add the variant to `_INDIRECT_KEY_MAP` in `unit.py`, or update the DB line_item via Django admin

### EBITDA looks too high (includes interest)
- **Cause:** Interest Paid ledger not being detected by `"interest" in line.lower()` — check `LedgerMapping.line_item` for the interest ledger
- **Fix:** Ensure the interest ledger's `line_item` contains the word "interest" (case-insensitive)

### Matrix Total column double-counts overhead
- **By design:** The `"General"` column contains the full company overhead pool; each building column also receives its pro-rata share. The Total = sum(building allocations) + General pool. This is the management accounting model: buildings show fully-loaded costs, General shows the overhead pool for reference.

### Cache serving stale data
- **Fix:** Click **Generate Report** (sends `bust=true`) or call the API with `?bust=true` directly
- **Note:** Cache is in-process (`locmem`); restarting the Django dev server also clears it
