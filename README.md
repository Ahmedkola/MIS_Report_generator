# MIS Report Generator

MIS Report Generator is a Django + React dashboard that connects to a local
TallyPrime company, extracts accounting data through Tally's XML HTTP API, and
renders management information system reports for Unreal Estate Habitat Private
Limited.

The app produces:

- Consolidated Profit & Loss
- Balance Sheet
- Building-wise Matrix P&L
- Unit-wise P&L
- Cash Flow Statement
- Deposits and Loans report
- Offline ZIP export containing a self-contained interactive HTML dashboard

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Django 5.1, SQLite, Python |
| Frontend | React 18, Vite, Tailwind CSS, Recharts |
| Data source | TallyPrime XML API over HTTP |
| Export | Vite single-file build injected with report JSON and zipped by Django |

## Repository Layout

```text
.
├── backend/
│   ├── config/                    # Django project settings and URL routing
│   ├── mis_engine/
│   │   ├── management/commands/   # Tally sync and mapping maintenance commands
│   │   ├── migrations/            # DB schema and seed data
│   │   ├── reports/               # Report processors
│   │   ├── export.py              # Offline report ZIP generation
│   │   ├── models.py              # Ledger, building, and cost-center config
│   │   ├── urls.py                # API routes
│   │   └── views.py               # JSON API views
│   ├── schemas.py                 # TypedDict report schema definitions
│   ├── tally_api.py               # TallyPrime XML API client
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── components/            # Report UI components
│   │   ├── context/               # Report data provider
│   │   ├── pages/                 # Route-level report pages
│   │   └── utils/                 # API and formatting helpers
│   ├── package.json
│   └── vite.config.js
├── docs/
│   ├── all_reports.md             # Detailed report pipeline documentation
│   └── pnl_report.md              # P&L-specific implementation notes
└── README.md
```

## How It Works

```text
TallyPrime on 127.0.0.1:9000
        |
        | XML over HTTP
        v
backend/tally_api.py
        |
        v
backend/mis_engine/reports/
        |
        | report JSON
        v
backend/mis_engine/views.py
        |
        | /api/reports/*
        v
frontend/src/context/ReportContext.jsx
        |
        v
React dashboard pages
```

The main dashboard calls `GET /api/reports/all/` once for the selected date
range. The backend builds every core report and caches the combined payload for
30 minutes using Django's in-memory cache. Clicking Generate sends `bust=true`
to force a fresh Tally pull.

## Prerequisites

### System

- Python 3.11+ recommended
- Node.js 18+ recommended
- npm
- TallyPrime running on the same machine or reachable over the network

### TallyPrime

The backend expects Tally's XML HTTP server to be enabled.

1. Open TallyPrime.
2. Load the company:
   `Unreal Estate Habitat Private Limited`
3. Enable the HTTP server on port `9000`.
4. Confirm Tally is reachable at `127.0.0.1:9000`.

The code intentionally uses `127.0.0.1` instead of `localhost`, because some
Windows environments resolve `localhost` to IPv6 while Tally listens on IPv4.

## Backend Setup

From the repository root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install django requests
python manage.py migrate
python manage.py runserver 8001
```

There is currently no `requirements.txt` in this repository. The backend imports
at least `django` and `requests`; add any local environment-specific packages if
your setup requires them.

The Django API will be available at:

```text
http://localhost:8001/api/
```

## Frontend Setup

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on:

```text
http://localhost:5174
```

Vite proxies `/api` requests to the Django backend at `http://localhost:8001`.

## Typical Development Workflow

1. Start TallyPrime and load the correct company.
2. Start Django:

   ```bash
   cd backend
   source .venv/bin/activate
   python manage.py runserver 8001
   ```

3. Start Vite:

   ```bash
   cd frontend
   npm run dev
   ```

4. Open `http://localhost:5174`.
5. Select the month range.
6. Click Generate to refresh the server cache and pull fresh Tally data.

If the frontend cannot reach the backend, `frontend/src/utils/api.js` falls back
to mock data for the main dashboard API. Cash flow still expects the live API.

## API Reference

All date parameters use Tally's `YYYYMMDD` format.

### `GET /api/reports/all/`

Returns the combined report payload used by the dashboard.

Query parameters:

| Param | Default | Description |
| --- | --- | --- |
| `from` | `20250401` | Report period start |
| `to` | `20260131` | Report period end |
| `bust` | `false` | When `true`, deletes the cached payload before regenerating |

Example:

```text
/api/reports/all/?from=20250401&to=20260131&bust=true
```

Response shape:

```json
{
  "status": "success",
  "data": {
    "company_id": "Unreal Estate Habitat Private Limited",
    "company_name": "Unreal Estate Habitat Private Limited",
    "period_start": "20250401",
    "period_end": "20260131",
    "consolidated_pnl": {},
    "balance_sheet": {},
    "matrix_pnl": [],
    "unit_wise": {},
    "deposits_loans": {}
  }
}
```

### Individual Report Endpoints

| Endpoint | Description |
| --- | --- |
| `GET /api/reports/pnl/` | Consolidated P&L only |
| `GET /api/reports/balance-sheet/` | Balance Sheet only |
| `GET /api/reports/matrix/` | Building-wise Matrix P&L only |
| `GET /api/reports/unit-wise/` | Unit-wise P&L only |
| `GET /api/reports/cashflow/` | Cash Flow Statement |
| `GET /api/reports/download/` | Offline interactive report ZIP |
| `GET /api/reports/debug-tb/` | Debug trial-balance ledger search |

### Cash Flow

```text
/api/reports/cashflow/?p1_from=20250401&p1_to=20260131&p2_from=20250401&p2_to=20251231
```

Required parameters:

| Param | Description |
| --- | --- |
| `p1_from` | First comparison period start |
| `p1_to` | First comparison period end |
| `p2_from` | Second comparison period start |
| `p2_to` | Second comparison period end |

### Offline Download

```text
/api/reports/download/?from=20250401&to=20260131
```

This endpoint requires a frontend production build at `frontend/dist`.

```bash
cd frontend
npm run build
cd ../backend
python manage.py runserver 8001
```

Then request the download endpoint. The ZIP contains an `index.html` that can be
opened without a live backend because report data is injected into
`window.REPORT_DATA`.

## Report Processors

| Processor | File | Responsibility |
| --- | --- | --- |
| `StandardReportProcessor` | `backend/mis_engine/reports/pnl_bs.py` | Builds consolidated P&L and Balance Sheet |
| `MatrixReportProcessor` | `backend/mis_engine/reports/matrix.py` | Builds building-wise P&L matrix |
| `UnitReportProcessor` | `backend/mis_engine/reports/unit.py` | Builds per-unit report using DB cost-center config |
| `CashFlowProcessor` | `backend/mis_engine/reports/cashflow.py` | Builds cash-flow comparisons |
| `DepositsLoansProcessor` | `backend/mis_engine/reports/deposits_loans.py` | Builds deposits and loans view |

All processors inherit shared Tally and mapping helpers from
`backend/mis_engine/reports/base.py`.

## Data Model

The reporting logic is driven by database configuration, not only hardcoded
ledger names.

### `LedgerMapping`

Maps an exact Tally ledger name into an MIS report location.

Important fields:

- `tally_ledger_name`: exact ledger name from Tally
- `report_section`: top-level report section, such as `Income`, `Expenses`,
  `Direct Expenses`, `Assets`, or `Equity & Liabilities`
- `report_group`: group inside the report section
- `line_item`: final display line item
- `cost_center`: optional matrix/building column association

### `Building`

Defines a physical property group used by matrix and unit-wise reporting.

Important fields:

- `display_name`
- `general_cc`
- `rent_ledger`
- `column_order`
- `is_active`

### `CostCenter`

Defines individual units or virtual columns inside a building.

Important fields:

- `building`
- `display_name`
- `tally_cc`
- `column_order`
- `is_excluded_from_split`
- `rent_weight`
- `is_active`

## Management Commands

Run these from `backend/` with the virtual environment activated.

### Sync Ledgers From Tally

```bash
python manage.py sync_tally
```

Fetches active ledgers from Tally, creates missing `LedgerMapping` rows, then
runs auto-mapping for new unmapped ledgers.

Skip auto-mapping:

```bash
python manage.py sync_tally --no-automap
```

### Auto-map Ledgers

```bash
python manage.py auto_map
```

Applies two phases:

- Known-correct explicit mappings for this company
- Keyword-based fallback mappings for ledgers that remain unmapped

Useful variants:

```bash
python manage.py auto_map --phase1
python manage.py auto_map --force
```

### Apply Known-correct Mappings

```bash
python manage.py apply_correct_mappings
```

Repairs or reapplies explicit company-specific mappings.

Preview without writing:

```bash
python manage.py apply_correct_mappings --dry-run
```

## Tally Data Extraction

`backend/tally_api.py` owns the XML integration with TallyPrime.

Key methods:

| Method | Purpose |
| --- | --- |
| `ping()` | Checks whether Tally is reachable |
| `fetch_trial_balance(from, to)` | Fetches ledger balances for a period |
| `fetch_pnl_report(from, to)` | Fetches Tally's Profit & Loss report |
| `fetch_balance_sheet(to)` | Fetches group-level Balance Sheet data |
| `fetch_cost_center_breakup(from, to, cc)` | Fetches cost-center ledger breakup |
| `fetch_ledger_vouchers(name, from, to)` | Fetches vouchers for GST and host-fee attribution |

Sign convention:

- Credit / income values are positive.
- Debit / expense values are negative in the normalized report payload.
- Some cost-center APIs return absolute values plus `dr_cr`; processors convert
  those back to signed amounts.

## Frontend Routes

| Route | Page |
| --- | --- |
| `/pnl` | Consolidated P&L |
| `/balance-sheet` | Balance Sheet |
| `/matrix` | Building-wise Matrix P&L |
| `/unit-wise` | Unit-wise report |
| `/cash-flow` | Cash Flow Statement |
| `/deposits-loans` | Deposits and Loans |

The default `/` route redirects to `/pnl`.

## Configuration Notes

- Backend port expected by Vite proxy: `8001`
- Frontend dev port: `5174`
- Tally XML server default: `127.0.0.1:9000`
- Default report date range in backend views: `20250401` to `20260131`
- Default month range in frontend UI: `2025-04` to `2026-01`
- Django cache backend: local in-memory cache with 30-minute timeout
- Database: SQLite at `backend/db.sqlite3`

## Testing and Validation

Backend:

```bash
cd backend
python manage.py test
```

Frontend build:

```bash
cd frontend
npm run build
```

API smoke test:

```bash
curl "http://localhost:8001/api/reports/all/?from=20250401&to=20260131"
```

Tally connection check through Django:

```bash
cd backend
python manage.py sync_tally --no-automap
```

## Troubleshooting

### `Could not connect to Tally XML server`

- Confirm TallyPrime is open.
- Confirm the correct company is loaded.
- Confirm the HTTP server is enabled on port `9000`.
- Confirm no firewall or port conflict is blocking `127.0.0.1:9000`.

### API returns `Tally returned empty P&L`

- Check the date range.
- Confirm the active Tally company has data for that period.
- Try the debug endpoint:

  ```text
  /api/reports/debug-tb/?q=rent&from=20250401&to=20260131
  ```

### Frontend shows mock data

The frontend falls back to mock data when the live `/api/reports/all/` request
cannot reach Django. Start the backend on port `8001` and regenerate.

### Offline ZIP endpoint returns `frontend dist folder not found`

Build the frontend before using `/api/reports/download/`:

```bash
cd frontend
npm run build
```

### Report values look double-counted

Check `LedgerMapping` rows for parent Tally group ledgers. Parent aggregates and
child ledgers that would double-count should use:

```text
report_section = Excluded
report_group   = Excluded
```

Run:

```bash
cd backend
python manage.py apply_correct_mappings --dry-run
```

## Additional Documentation

- `docs/all_reports.md` contains detailed implementation notes for all report
  processors and report-specific formulas.
- `docs/pnl_report.md` documents the P&L pipeline in depth.

## Known Gaps

- No backend `requirements.txt` is currently committed.
- Django settings are development-oriented: `DEBUG=True`, SQLite, and a checked-in
  development secret key. Production deployment should move secrets and
  environment-specific settings out of source control.
- `frontend/package.json` references `postbuild.py`, but this repository does
  not currently include that file. If `npm run build` fails after Vite finishes,
  either add the missing script or update the build command.
