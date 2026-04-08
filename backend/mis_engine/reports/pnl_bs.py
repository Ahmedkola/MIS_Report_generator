from typing import Dict
from schemas import StandardReport
from .base import BaseReportProcessor

class StandardReportProcessor(BaseReportProcessor):

    # Maps Tally's P&L section names to our StandardReport (report_section, report_group) tuples.
    # "Cost of Sales :" is a parent header that wraps "Direct Expenses" — skip it.
    _PNL_SECTION_MAP = {
        "Sales Accounts":   ("Income",          "Sales Accounts"),
        "Direct Incomes":   ("Income",          "Direct Incomes"),
        "Direct Expenses":  ("Direct Expenses", "Direct Expenses"),
        "Indirect Incomes": ("Income",          "Indirect Incomes"),
        "Indirect Expenses":("Expenses",        "Indirect Expenses"),
    }

    def process(self) -> Dict[str, StandardReport]:
        pnl_report: StandardReport = {
            "report_type": "pnl",
            "period": f"{self.from_date} to {self.to_date}",
            "company": self.api.COMPANY_ID,
            "sections": {},
            "summary": {}
        }

        bs_report: StandardReport = {
            "report_type": "balance_sheet",
            "period": f"{self.from_date} to {self.to_date}",
            "company": self.api.COMPANY_ID,
            "sections": {},
            "summary": {}
        }

        # ── P&L: try Tally's P&L report first; fall back to Trial Balance ────
        # Tally's P&L report pre-classifies every ledger, so no DB mapping is needed.
        # If the P&L report fetch fails (wrong report name, Tally version, etc.)
        # we fall back to the original Trial Balance + LedgerMapping approach.
        pnl_sections = {}
        try:
            pnl_sections = self.api.fetch_pnl_report(self.from_date, self.to_date)
        except Exception as exc:
            import logging
            logging.getLogger("pnl_bs").warning("fetch_pnl_report failed (%s), falling back to Trial Balance.", exc)

        if pnl_sections:
            # ── Primary path: use Tally's own P&L classification ──────────────
            for tally_section, section_data in pnl_sections.items():
                mapping = self._PNL_SECTION_MAP.get(tally_section)
                if not mapping:
                    continue  # skip "Cost of Sales :" and unrecognised headers
                report_section, report_group = mapping
                for item in section_data["items"]:
                    self._add_to_report(pnl_report, report_section, report_group, item["name"], item["amount"])
        else:
            # ── Fallback: Trial Balance + LedgerMapping ────────────────────────
            raw_ledgers = self.raw_data
            if not raw_ledgers:
                raise ValueError("Tally returned 0 ledgers. Check connection or dates.")
            for ledger in raw_ledgers:
                ledger_name = ledger["ledger_name"]
                amount      = ledger["amount"]
                db_mapping  = self.mappings.get(ledger_name)
                if not db_mapping:
                    unmapped_section = "Income" if amount >= 0 else "Expenses"
                    self._add_to_report(pnl_report, "Unmapped", unmapped_section, ledger_name, amount)
                    continue
                report_section = db_mapping.report_section
                report_group   = db_mapping.report_group
                line_item      = db_mapping.line_item
                if report_section.lower() == "excluded":
                    continue
                if report_section.lower() in ["income", "expenses", "direct expenses", "indirect expenses"]:
                    self._add_to_report(pnl_report, report_section, report_group, line_item, amount)

        self._calculate_summaries(pnl_report, bs_report)

        bs_report["sections"] = {}
        bs_group_section = {
            "Capital Account":       ("Equity & Liabilities", "Capital Account"),
            "Loans (Liability)":     ("Equity & Liabilities", "Loans (Liability)"),
            "Current Liabilities":   ("Equity & Liabilities", "Current Liabilities"),
            "Suspense A/c":          ("Equity & Liabilities", "Suspense"),
            "Profit & Loss A/c":     ("Equity & Liabilities", "Profit & Loss A/c"),
            "Fixed Assets":          ("Assets",               "Fixed Assets"),
            "Current Assets":        ("Assets",               "Current Assets"),
            "Loans & Advances (Asset)": ("Assets",            "Current Assets"),
            "Investments":           ("Assets",               "Investments"),
            "Misc. Expenses (Asset)": ("Assets",              "Misc. Expenses"),
        }
        bs_raw = self.api.fetch_balance_sheet(self.to_date)
        for item in bs_raw:
            group_name = item["ledger_name"]
            amount = item["amount"]
            if group_name in bs_group_section:
                section, group = bs_group_section[group_name]
                self._add_to_report(bs_report, section, group, group_name, amount)
            elif amount > 0:
                self._add_to_report(bs_report, "Equity & Liabilities", "Other Liabilities", group_name, amount)
            else:
                self._add_to_report(bs_report, "Assets", "Other Assets", group_name, amount)

        return {
            "pnl": pnl_report,
            "balance_sheet": bs_report
        }

    def _calculate_summaries(self, pnl: StandardReport, bs: StandardReport):
        total_income = sum(g["subtotal"] for g in pnl["sections"].get("Income", {}).values())
        direct_expenses   = sum(g["subtotal"] for g in pnl["sections"].get("Direct Expenses", {}).values())
        indirect_expenses = sum(g["subtotal"] for g in pnl["sections"].get("Expenses", {}).values())
        total_expenses    = direct_expenses + indirect_expenses

        gross_profit = total_income + direct_expenses
        net_profit   = gross_profit + indirect_expenses
        
        pnl["summary"] = {
            "total_income":    total_income,
            "direct_expenses": direct_expenses,
            "indirect_expenses": indirect_expenses,
            "total_expenses":  total_expenses,
            "gross_profit":    gross_profit,
            "net_profit":      net_profit,
        }
