# P&L Report — Code Documentation

**Company:** Unreal Estate Habitat Private Limited  
**Stack:** Django (backend) · React + Vite (frontend) · TallyPrime XML API (data source)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Flow](#2-data-flow)
3. [Backend](#3-backend)
   - [Tally API Client](#31-tally-api-client--backendtally_apipy)
   - [Data Schemas](#32-data-schemas--backendschemaspy)
   - [Report Processor](#33-report-processor--backendmis_enginereportspnl_bspy)
   - [Base Processor](#34-base-processor--backendmis_enginereportsbasepy)
   - [Django View](#35-django-view--backendmis_engineviewspy)
4. [Frontend](#4-frontend)
   - [API Utility](#41-api-utility--frontendsrcutilsapijs)
   - [Report Context](#42-report-context--frontendsrccontextreportcontextjsx)
   - [P&L Page](#43-pl-page--frontendsrcpagespnlpagejsx)
   - [P&L Report Component](#44-pl-report-component--frontendsrccomponentspnlreportjsx)
5. [JSON Data Structure](#5-json-data-structure)
6. [Sign Convention](#6-sign-convention)
7. [Fetching Strategy](#7-fetching-strategy)
8. [Known Issues & Debugging](#8-known-issues--debugging)

---

## 1. Architecture Overview

```
TallyPrime (port 9000)
      │
      │  XML over HTTP
      ▼
backend/tally_api.py          ← TallyAPIClient
      │
      │  list[LedgerBalance] or dict of P&L sections
      ▼
backend/mis_engine/reports/
  pnl_bs.py                   ← StandardReportProcessor
      │
      │  StandardReport (dict)
      ▼
backend/mis_engine/views.py   ← get_all_reports()
      │
      │  JSON response (cached 30 min)
      ▼
frontend/src/utils/api.js     ← fetchAllData()
      │
      ▼
frontend/src/context/ReportContext.jsx   ← ReportDataProvider
      │
      ▼
frontend/src/pages/PnLPage.jsx
      │
      ▼
frontend/src/components/PnLReport.jsx   ← T-account display
```

---

## 2. Data Flow

### Step-by-step

| # | Where | What happens |
|---|-------|--------------|
| 1 | Browser | User selects date range (e.g. Apr 2025 – Jan 2026) and clicks **Generate Report** |
| 2 | `api.js` | Converts `YYYY-MM` to `YYYYMMDD` (`20250401` / `20260131`) and calls `GET /api/reports/all/?from=20250401&to=20260131&bust=true` |
| 3 | `views.py` | Checks 30-min cache; cache miss → runs `StandardReportProcessor` |
| 4 | `pnl_bs.py` | **Primary:** calls `api.fetch_pnl_report()` to get Tally's pre-classified P&L XML. **Fallback:** if that fails, calls `api.fetch_trial_balance()` + DB mapping |
| 5 | `tally_api.py` | POSTs XML request to TallyPrime on `127.0.0.1:9000`, decodes UTF-16 response, parses into sections |
| 6 | `pnl_bs.py` | Maps Tally section names → `StandardReport` structure; calculates summaries |
| 7 | `views.py` | Returns JSON envelope; caches it for 30 min |
| 8 | `ReportContext.jsx` | Stores response in React state |
| 9 | `PnLReport.jsx` | Renders T-account layout (Trading Account + P&L Account) |

---

## 3. Backend

### 3.1 Tally API Client — `backend/tally_api.py`

**Class:** `TallyAPIClient`  
**Purpose:** Communicates with TallyPrime's XML HTTP server.

#### Key methods

---

##### `fetch_pnl_report(from_date, to_date) → dict`

Primary method for P&L data. Requests Tally's own "Profit & Loss" report.

**Request payload (sent to Tally):**
```xml
<ENVELOPE>
  <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
  <BODY><EXPORTDATA><REQUESTDESC>
    <REPORTNAME>Profit &amp; Loss</REPORTNAME>
    <STATICVARIABLES>
      <SVCURRENTCOMPANY>Unreal Estate Habitat Private Limited</SVCURRENTCOMPANY>
      <SVFROMDATE>20250401</SVFROMDATE>
      <SVTODATE>20260131</SVTODATE>
      <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      <EXPLODEFLAG>Yes</EXPLODEFLAG>
      <EXPLODEALLLEVELS>Yes</EXPLODEALLLEVELS>
    </STATICVARIABLES>
  </REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>
```

**Returns:**
```python
{
  "Sales Accounts":    {"total": 75414283.37, "items": [{"name": "Koramangala", "amount": 8265642.68}, ...]},
  "Direct Incomes":    {"total": 7205.65,     "items": [{"name": "Amazon Pay",  "amount": 7205.65}]},
  "Direct Expenses":   {"total":-44615529.20, "items": [{"name": "Electricity", "amount":-2462696.62}, ...]},
  "Indirect Incomes":  {"total": 237060.06,   "items": [...]},
  "Indirect Expenses": {"total":-12642983.93, "items": [...]},
}
```

**Encoding note:** Tally responds in UTF-16 LE. The method detects the BOM (`\xff\xfe` or `\xfe\xff`) and decodes with `bytes.decode("utf-16")`. Without this, each ASCII character appears with a space between it (e.g. `< E N V E L O P E >`).

**Debug files created:**
- `pnl_dump.bin` — raw bytes from Tally
- `pnl_dump.xml` — decoded XML text

---

##### `_parse_pnl_xml(raw_xml) → dict`

Parses the P&L report XML. The XML has a flat sibling structure under `<ENVELOPE>`:

```
Tag sequence              → Meaning
──────────────────────────────────────────────────────
DSPACCNAME                → Section or sub-section name
PLAMT / BSMAINAMT filled  → Top-level section total
PLAMT / PLSUBAMT filled   → Sub-section total (Direct Expenses under Cost of Sales)
BSNAME                    → Pending individual line item name
BSAMT / BSSUBAMT          → Line item amount
```

Parse state machine:
1. `DSPACCNAME` → set `current_section`; initialise `sections[current_section]` if new
2. `PLAMT` → read `BSMAINAMT` or `PLSUBAMT`; store as section total
3. `BSNAME` → set `pending_item`
4. `BSAMT` → read `BSSUBAMT`; if non-zero append `{name, amount}` to `sections[current_section]["items"]`

---

##### `fetch_trial_balance(from_date, to_date) → list[LedgerBalance]`

Fallback data source. Returns all non-zero ledger closing balances for the period.

Uses a two-strategy approach:
1. **Strategy 1 — Trial Balance Report API:** requests the "Trial Balance" report with `EXPLODEFLAG=Yes`. Parses `DSPACCNAME` / `DSPACCINFO` / `DSPCLDRAMTA` / `DSPCLCRAMTA` sibling pairs.
2. **Strategy 2 — Raw Collection API:** if Strategy 1 returns empty, queries Tally's `LEDGER` collection with `CLOSINGBALANCE`.

**Returns:**
```python
[
  {"ledger_name": "Koramangala", "amount": 8265642.68, "dr_cr": "Cr"},
  {"ledger_name": "Electricity", "amount": -2462696.62, "dr_cr": "Dr"},
  ...
]
```

---

##### `fetch_balance_sheet(to_date) → list[LedgerBalance]`

Fetches the Balance Sheet at **group level** (not exploded). Returns one entry per top-level group (Fixed Assets, Current Assets, Capital Account, etc.).

---

##### `_parse_tally_amount(raw) → (float, str)`

Handles all Tally amount string formats:

| Input | Output |
|-------|--------|
| `"34085700.00 Dr"` | `(-34085700.0, "Dr")` |
| `"250.50 Cr"` | `(250.5, "Cr")` |
| `"-34085700.00"` | `(-34085700.0, "Dr")` |
| `""` / `None` | `(0.0, "Cr")` |

---

##### `_sanitize_xml(raw) → str`

Strips characters invalid in XML 1.0 and malformed numeric entity references that Tally sometimes emits. Removes the BOM if present.

---

##### `_post(xml_payload) → str | None`
##### `_post_raw(xml_payload) → bytes | None`

`_post` returns `r.text` (auto-decoded by requests).  
`_post_raw` returns `r.content` (raw bytes) — used by `fetch_pnl_report` to handle UTF-16 manually.

Both raise `ConnectionError` if Tally is unreachable, `TimeoutError` if no response within `timeout` seconds (default 120s).

---

### 3.2 Data Schemas — `backend/schemas.py`

#### `LedgerBalance` (TypedDict)
```python
{
  "ledger_name": str,   # exact Tally ledger name
  "amount":      float, # signed; negative = Debit
  "dr_cr":       str,   # "Dr" | "Cr"
}
```

#### `LineItem` (TypedDict)
```python
{
  "name":      str,           # e.g. "Rent", "Consumables"
  "amount":    float,         # signed INR
  "breakdown": list | None,   # optional drill-down
}
```

#### `ReportGroup` (TypedDict)
```python
{
  "group_name": str,                  # e.g. "Direct Expenses"
  "items":      dict[str, LineItem],  # line_item_name → LineItem
  "subtotal":   float,                # sum of all item amounts
}
```

#### `StandardReport` (TypedDict) — the P&L JSON shape
```python
{
  "report_type": "pnl",
  "period":      "20250401 to 20260131",
  "company":     "Unreal Estate Habitat Private Limited",
  "sections": {
    "Income": {
      "Sales Accounts": ReportGroup,   # items = individual property ledgers
      "Direct Incomes": ReportGroup,
      "Indirect Incomes": ReportGroup,
    },
    "Direct Expenses": {
      "Direct Expenses": ReportGroup,  # Rent, Electricity, Consumables, etc.
    },
    "Expenses": {
      "Indirect Expenses": ReportGroup, # Salary, Professional Fees, etc.
    }
  },
  "summary": {
    "total_income":      float,
    "direct_expenses":   float,  # negative
    "indirect_expenses": float,  # negative
    "total_expenses":    float,  # negative
    "gross_profit":      float,
    "net_profit":        float,
  }
}
```

---

### 3.3 Report Processor — `backend/mis_engine/reports/pnl_bs.py`

**Class:** `StandardReportProcessor(BaseReportProcessor)`

#### Section mapping

Tally's own section names are mapped to the `StandardReport` structure:

| Tally section name | `report_section` | `report_group` |
|---|---|---|
| `Sales Accounts` | `Income` | `Sales Accounts` |
| `Direct Incomes` | `Income` | `Direct Incomes` |
| `Direct Expenses` | `Direct Expenses` | `Direct Expenses` |
| `Indirect Incomes` | `Income` | `Indirect Incomes` |
| `Indirect Expenses` | `Expenses` | `Indirect Expenses` |
| `Cost of Sales :` | *(skipped — parent header)* | — |

#### `process() → {"pnl": StandardReport, "balance_sheet": StandardReport}`

**P&L assembly (two-path logic):**

```
fetch_pnl_report()
   ├── Success (dict non-empty)
   │     → loop sections → _add_to_report() into pnl_report
   │       (Tally's own classification — most accurate)
   └── Failure / empty
         → fetch_trial_balance() + LedgerMapping DB lookup
           → loop ledgers → map section/group/line_item → _add_to_report()
           (fallback — depends on DB mappings being complete)
```

**Balance Sheet assembly:**

Calls `api.fetch_balance_sheet()` (group-level, not exploded) and maps group names to `(section, group)` pairs via a hardcoded dict:

```python
{
  "Capital Account":          ("Equity & Liabilities", "Capital Account"),
  "Loans (Liability)":        ("Equity & Liabilities", "Loans (Liability)"),
  "Current Liabilities":      ("Equity & Liabilities", "Current Liabilities"),
  "Fixed Assets":             ("Assets", "Fixed Assets"),
  "Current Assets":           ("Assets", "Current Assets"),
  "Loans & Advances (Asset)": ("Assets", "Current Assets"),
  # etc.
}
```

#### `_calculate_summaries(pnl, bs)`

```python
total_income      = sum of sections["Income"].values()        (subtotals)
direct_expenses   = sum of sections["Direct Expenses"].values()
indirect_expenses = sum of sections["Expenses"].values()
gross_profit      = total_income + direct_expenses            (direct_expenses is negative)
net_profit        = gross_profit + indirect_expenses
```

---

### 3.4 Base Processor — `backend/mis_engine/reports/base.py`

**Class:** `BaseReportProcessor`

| Property / Method | Description |
|---|---|
| `self.api` | `TallyAPIClient(timeout=120)` instance |
| `self.raw_data` | Lazy-loaded Trial Balance (`fetch_trial_balance()`) |
| `self.mappings` | Lazy-loaded `{ledger_name: LedgerMapping}` dict from DB |
| `_add_to_report(report, section, group, line_item, amount)` | Upserts amount into `report["sections"][section][group]["items"][line_item]` and accumulates `subtotal` |

---

### 3.5 Django View — `backend/mis_engine/views.py`

#### `GET /api/reports/all/`

**Parameters:**

| Param | Format | Example | Default |
|-------|--------|---------|---------|
| `from` | `YYYYMMDD` | `20250401` | `20250401` |
| `to` | `YYYYMMDD` | `20260131` | `20260131` |
| `bust` | `true`/`false` | `true` | `false` |

**Behaviour:**
1. Validates date format (8 digits)
2. Checks Django cache (`mis_all_{from}_{to}`) — returns cached JSON if hit
3. `bust=true` deletes the cache entry first
4. Runs `StandardReportProcessor`, `MatrixReportProcessor`, `UnitReportProcessor` sequentially
5. Returns combined JSON; caches for 30 minutes

**Response shape:**
```json
{
  "status": "success",
  "data": {
    "company_id": "Unreal Estate Habitat Private Limited",
    "period_start": "20250401",
    "period_end": "20260131",
    "consolidated_pnl": { ... },
    "balance_sheet": { ... },
    "matrix_pnl": [ ... ],
    "unit_wise": { ... }
  }
}
```

**Error response (HTTP 500):**
```json
{
  "status": "error",
  "message": "...",
  "traceback": "..."
}
```

---

## 4. Frontend

### 4.1 API Utility — `frontend/src/utils/api.js`

#### Date conversion helpers

| Function | Input | Output | Example |
|---|---|---|---|
| `toTallyFrom(ym)` | `"2025-04"` | `"20250401"` | Always appends `01` |
| `toTallyTo(ym)` | `"2026-01"` | `"20260131"` | Computes last day of month |

#### `fetchAllData(fromYM, toYM, bust, signal)`

- Calls `GET /api/reports/all/?from=YYYYMMDD&to=YYYYMMDD[&bust=true]`
- On network failure (Tally/backend unreachable) → falls back to `getMockData()`
- Returns `{ data: {...}, source: "live" | "mock" }`

---

### 4.2 Report Context — `frontend/src/context/ReportContext.jsx`

**Provider:** `<ReportDataProvider>`  
**Hook:** `useReport()`

Exposes:

| Value | Type | Description |
|-------|------|-------------|
| `data` | `object \| null` | Full API response (`data` field) |
| `loading` | `boolean` | True while fetch in progress |
| `error` | `string \| null` | Error message if fetch failed |
| `source` | `"live" \| "mock" \| null` | Origin of current data |
| `generate(fromYM, toYM, bust)` | `function` | Triggers a new fetch; cancels any in-flight request |

Cancellation: uses `AbortController`; starting a new `generate()` call aborts the previous one.

---

### 4.3 P&L Page — `frontend/src/pages/PnLPage.jsx`

Simple composition layer:

```jsx
const { data, loading, error } = useReport()
const pnl = data.consolidated_pnl

return (
  <section>
    <SummaryCards pnl={pnl} />
    <SectionTitle title="Consolidated Profit & Loss" sub={pnl.period} />
    <PnLReport report={pnl} />
  </section>
)
```

---

### 4.4 P&L Report Component — `frontend/src/components/PnLReport.jsx`

Renders the standard double-entry **T-account** layout.

#### Layout structure

```
┌─────────────────────────────────────────────────────────┐
│  Company Name · Profit & Loss Account · Period           │
├──────────────────────────┬──────────────────────────────┤
│  TRADING ACCOUNT                                         │
├──────────────────────────┬──────────────────────────────┤
│  Dr — Direct Expenses    │  Cr — Sales Accounts         │
│    Electricity           │    Koramangala                │
│    Rent                  │    Hebbal                     │
│    ...                   │    ...                        │
│  Gross Profit c/o  ►     │    Direct Incomes             │
├──────────────────────────┼──────────────────────────────┤
│  Total                   │  Total                        │
├──────────────────────────┬──────────────────────────────┤
│  PROFIT & LOSS ACCOUNT                                   │
├──────────────────────────┬──────────────────────────────┤
│  Dr — Indirect Expenses  │  Cr — Gross Profit b/f        │
│    Salary                │       ◄ carried forward       │
│    Professional Fees     │  Indirect Incomes             │
│    ...                   │    Discount/Gift Cards        │
│  Nett Loss / Profit ►    │    Int. on FD                 │
├──────────────────────────┼──────────────────────────────┤
│  Total                   │  Total                        │
├──────────────────────────┴──────────────────────────────┤
│  GROSS PROFIT  |  NET PROFIT/LOSS  |  TOTAL REVENUE      │
└─────────────────────────────────────────────────────────┘
```

#### Data partitioning

```js
// Income groups split into Sales vs Indirect
const INDIRECT_INCOME_GROUPS = new Set(['Indirect Incomes', 'Indirect Income'])
const salesGroups          = Income groups NOT in INDIRECT_INCOME_GROUPS
const indirectIncomeGroups = Income groups IN  INDIRECT_INCOME_GROUPS

// Expense sections from backend keys
const directExpGroups   = sections['Direct Expenses']
const indirectExpGroups = sections['Expenses']
```

#### Calculations (frontend-computed)

```js
totalSales      = sum(|salesGroup.subtotal|)
totalDirectExp  = sum(|directExpGroup.subtotal|)
grossProfit     = totalSales - totalDirectExp

totalIndirectInc = sum(|indirectIncGroup.subtotal|)
totalIndirectExp = sum(|indirectExpGroup.subtotal|)
netProfit        = grossProfit + totalIndirectInc - totalIndirectExp
```

The backend-computed `summary.net_profit` is used for the summary footer if available (more accurate), falling back to the frontend calculation.

---

## 5. JSON Data Structure

Full example of `consolidated_pnl` as returned by the API:

```json
{
  "report_type": "pnl",
  "period": "20250401 to 20260131",
  "company": "Unreal Estate Habitat Private Limited",
  "sections": {
    "Income": {
      "Sales Accounts": {
        "group_name": "Sales Accounts",
        "subtotal": 75414283.37,
        "items": {
          "Koramangala": { "name": "Koramangala",  "amount": 8265642.68, "breakdown": [] },
          "Hebbal":      { "name": "Hebbal",       "amount": 8148800.00, "breakdown": [] }
        }
      },
      "Direct Incomes": {
        "group_name": "Direct Incomes",
        "subtotal": 7205.65,
        "items": {
          "Amazon Pay": { "name": "Amazon Pay", "amount": 7205.65, "breakdown": [] }
        }
      },
      "Indirect Incomes": {
        "group_name": "Indirect Incomes",
        "subtotal": 237060.06,
        "items": {
          "Int. on FD":   { "name": "Int. on FD",   "amount": 27738.00, "breakdown": [] },
          "Other Income": { "name": "Other Income", "amount": 198325.14, "breakdown": [] }
        }
      }
    },
    "Direct Expenses": {
      "Direct Expenses": {
        "group_name": "Direct Expenses",
        "subtotal": -44615529.20,
        "items": {
          "Electricity":  { "name": "Electricity",  "amount": -2462696.62, "breakdown": [] },
          "RENT":         { "name": "RENT",         "amount": -34085700.00, "breakdown": [] },
          "Consumables":  { "name": "Consumables",  "amount": -3662303.69, "breakdown": [] }
        }
      }
    },
    "Expenses": {
      "Indirect Expenses": {
        "group_name": "Indirect Expenses",
        "subtotal": -12642983.93,
        "items": {
          "Salary A/c":         { "name": "Salary A/c",        "amount": -7210776.00, "breakdown": [] },
          "Ineligible GST":     { "name": "Ineligible GST",    "amount": -2003060.00, "breakdown": [] },
          "Professional Fees":  { "name": "Professional Fees", "amount": -805000.00,  "breakdown": [] }
        }
      }
    }
  },
  "summary": {
    "total_income":      75651549.02,
    "direct_expenses":  -44615529.20,
    "indirect_expenses":-12642983.93,
    "total_expenses":   -57258513.13,
    "gross_profit":      31036019.82,
    "net_profit":        18393035.89
  }
}
```

---

## 6. Sign Convention

Mirrors TallyPrime throughout the entire pipeline:

| Type | Sign | Examples |
|------|------|---------|
| Income / Credit | Positive `+` | Sales ₹75,414,283 |
| Expense / Debit | Negative `−` | Rent `−34,085,700` |
| Asset (Dr balance) | Negative `−` | Fixed Assets |
| Liability (Cr balance) | Positive `+` | Capital Account |

The frontend always displays amounts with `Math.abs()` and formats them with `₹` prefix (via `formatCurrency`).

---

## 7. Fetching Strategy

The system has two strategies for P&L data, tried in order:

### Primary — Direct P&L Report (new)
- Sends `REPORTNAME=Profit & Loss` to Tally
- Tally returns pre-classified sections (it already knows which ledger is an expense vs income)
- No database involvement for classification
- Most accurate; immune to missing `LedgerMapping` entries

### Fallback — Trial Balance + `LedgerMapping` DB
- Sends `REPORTNAME=Trial Balance` to Tally — returns all ledgers without section info
- Looks up each ledger name in the `LedgerMapping` Django model to determine:
  - `report_section` — e.g. `"Income"`, `"Expenses"`, `"Direct Expenses"`
  - `report_group` — e.g. `"Sales Accounts"`, `"Indirect Expenses"`
  - `line_item` — display name
- Ledgers with no mapping go to `"Unmapped"` section (not rendered in frontend)
- Was the original approach; "partially correct" when mappings were incomplete

---

## 8. Known Issues & Debugging

### Tally not running
- **Symptom:** HTTP 500, backend log shows `ConnectionError`
- **Fix:** Open TallyPrime, load company "Unreal Estate Habitat Private Limited", enable HTTP XML Server on port 9000

### P&L fetch returns empty
- **Symptom:** Backend log: `fetch_pnl_report failed (...), falling back to Trial Balance`
- **Debug:** Check `pnl_dump.bin` / `pnl_dump.xml` in the backend working directory
- **Common cause:** Tally report name mismatch or UTF-16 decode issue

### Amounts appear in wrong section
- **Cause:** Using fallback path with incomplete `LedgerMapping` DB entries
- **Fix:** Add missing rows to `LedgerMapping` via Django admin

### Date format error
- **Symptom:** HTTP 500, `"Invalid 'from' date. Expected YYYYMMDD"`
- **Cause:** Frontend sending raw `YYYY-MM` instead of converting — check `api.js` `toTallyFrom()`/`toTallyTo()` functions

### Cache serving stale data
- **Fix:** Click **Generate Report** (sends `bust=true`) or call `/api/reports/all/?from=...&to=...&bust=true` directly
