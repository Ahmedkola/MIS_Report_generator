"""
CashFlowProcessor — Indirect Method via Tally Cash Flow Breakup
================================================================
Uses Tally's built-in "Cash Flow Breakup" report (CCBkUp) which directly
gives per-group cash inflow / outflow for the period.

Sign convention in CFB:
  negative value → cash inflow  (money received)
  positive value → cash outflow (money paid)

After parsing, each group has:
  inflow  = total cash received   (always ≥ 0)
  outflow = total cash paid       (always ≥ 0)
  net     = inflow − outflow      (positive = net receipt)

Groups appear TWICE in the XML (once per direction block); parser accumulates both.
"""
from datetime import datetime, timedelta

# Ledger name keywords for Cash & Bank accounts (used for opening balance lookup)
CASH_KEYWORDS = ("cash", "bank", "sbi", "hdfc", "icici", "axis", "kotak", "yes bank",
                 "current account", "saving", "petty cash")


def _opening_date(from_date: str) -> str:
    """Return the day before from_date as YYYYMMDD."""
    d = datetime.strptime(from_date, "%Y%m%d") - timedelta(days=1)
    return d.strftime("%Y%m%d")


def _extract_cash_balance(bs_raw: dict) -> float:
    """
    Sum Cash & Bank ledger balances from the Current Assets section of a BS snapshot.
    Used only for opening-balance lookup (CFB gives changes, not opening balance).
    """
    ca = bs_raw.get("Current Assets", {})
    items = ca.get("items", []) if isinstance(ca, dict) else []
    if isinstance(items, dict):
        items = list(items.values())
    total = 0.0
    for item in items:
        name = item.get("ledger_name", "")
        if any(kw in name.lower() for kw in CASH_KEYWORDS):
            total += item.get("amount", 0.0)
    return abs(total)


def _fmt_label(from_date: str, to_date: str) -> str:
    """e.g. '20250401' / '20251231' → 'April 2025 to Dec 2025'"""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    full   = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    fm = int(from_date[4:6]) - 1
    fy = from_date[:4]
    tm = int(to_date[4:6]) - 1
    ty = to_date[:4]
    return f"{full[fm]} {fy} to {months[tm]} {ty}"


def _net(cfb: dict, *group_names: str) -> float:
    """Sum net cash flow across one or more group names (tries each in order, sums all found)."""
    total = 0.0
    for name in group_names:
        total += cfb.get(name, {}).get("net", 0.0)
    return total


def _compute_period(api, from_date: str, to_date: str) -> dict:
    # ── Fetch data ──────────────────────────────────────────────────────────
    cfb          = api.fetch_cash_flow_breakup(from_date, to_date)
    opening_bs   = api.fetch_balance_sheet(_opening_date(from_date))

    # ── Operating: P&L cash flows ───────────────────────────────────────────
    # net > 0 for income groups (more received than paid),
    # net < 0 for expense groups (more paid than received)
    sales_net        = _net(cfb, "Sales Accounts", "Sales Account")
    dir_inc_net      = _net(cfb, "Direct Incomes",   "Direct Income")
    indir_inc_net    = _net(cfb, "Indirect Incomes", "Indirect Income")
    dir_exp_net      = _net(cfb, "Direct Expenses",  "Direct Expense")   # negative
    indir_exp_net    = _net(cfb, "Indirect Expenses","Indirect Expense") # negative

    net_profit = (sales_net + dir_inc_net + indir_inc_net
                  + dir_exp_net + indir_exp_net)   # expenses already negative

    # ── Working Capital ─────────────────────────────────────────────────────
    # Current Assets net: positive = assets reduced = cash released (good)
    #                     negative = assets grew   = cash tied up   (bad)
    wc_current_assets      = _net(cfb, "Current Assets")
    # Current Liabilities net: positive = liabilities grew = cash saved (good)
    #                          negative = liabilities fell = cash paid  (bad)
    wc_current_liabilities = _net(cfb, "Current Liabilities", "Current Liability")

    operating = net_profit + wc_current_assets + wc_current_liabilities

    # ── Investing ───────────────────────────────────────────────────────────
    # Fixed Assets net: negative = more assets purchased = cash paid out
    invest_fixed_assets = _net(cfb, "Fixed Assets", "Fixed Asset")
    # Loans & Advances (Asset) net: negative = more loans given = cash paid
    invest_loans_asset  = _net(cfb, "Loans & Advances (Asset)",
                                    "Loans and Advances (Asset)",
                                    "Loan & Advances (Asset)")

    investing = invest_fixed_assets + invest_loans_asset

    # ── Financing ───────────────────────────────────────────────────────────
    # Loans (Liability) net: positive = new borrowing = cash received
    fin_loans   = _net(cfb, "Loans (Liability)", "Loan (Liability)",
                            "Loans and Advances (Liability)")
    # Capital Account net: positive = new capital = cash received
    fin_capital = _net(cfb, "Capital Account")

    financing = fin_loans + fin_capital

    # ── Summary ─────────────────────────────────────────────────────────────
    net_change   = operating + investing + financing
    opening_cash = _extract_cash_balance(opening_bs)
    closing_cash = opening_cash + net_change

    return {
        "label":                   _fmt_label(from_date, to_date),
        # Operating
        "net_profit":              net_profit,
        "wc_current_assets":       wc_current_assets,
        "wc_current_liabilities":  wc_current_liabilities,
        "operating":               operating,
        # Investing
        "invest_fixed_assets":     invest_fixed_assets,
        "invest_loans_asset":      invest_loans_asset,
        "investing":               investing,
        # Financing
        "fin_loans":               fin_loans,
        "fin_capital":             fin_capital,
        "financing":               financing,
        # Summary
        "net_change":              net_change,
        "opening_cash":            opening_cash,
        "closing_cash":            closing_cash,
    }


class CashFlowProcessor:
    def __init__(self, p1_from: str, p1_to: str, p2_from: str, p2_to: str):
        self.periods = [(p1_from, p1_to), (p2_from, p2_to)]
        from tally_api import TallyAPIClient
        self.api = TallyAPIClient(timeout=120)

    def process(self) -> dict:
        periods = [_compute_period(self.api, f, t) for f, t in self.periods]
        return {
            "company": self.api.COMPANY_ID,
            "periods": periods,
        }
