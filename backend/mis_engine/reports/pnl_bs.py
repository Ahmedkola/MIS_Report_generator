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

        # ── P&L: use Tally's own Group Summary classification ────────────────
        # fetch_pnl_report now calls Group Summary per P&L group (EXPLODEFLAG=Yes)
        # — same proven strategy as fetch_balance_sheet_group. This gives us
        # Tally's own classification directly, no manual DB mapping needed.
        pnl_sections = {}
        try:
            pnl_sections = self.api.fetch_pnl_report(self.from_date, self.to_date)
        except Exception as exc:
            import logging
            logging.getLogger("pnl_bs").error("fetch_pnl_report failed: %s", exc)

        if not pnl_sections:
            raise ValueError("Tally returned empty P&L. Check connection or dates.")

        for tally_section, section_data in pnl_sections.items():
            mapping = self._PNL_SECTION_MAP.get(tally_section)
            if not mapping:
                continue  # skip any unrecognised section
            report_section, report_group = mapping
            for item in section_data["items"]:
                self._add_to_report(pnl_report, report_section, report_group, item["name"], item["amount"])

        self._calculate_summaries(pnl_report, bs_report)

        bs_report["sections"] = {}
        bs_group_section = {
            "Capital Account":          ("Equity & Liabilities", "Capital Account"),
            "Loans (Liability)":        ("Equity & Liabilities", "Loans (Liability)"),
            "Current Liabilities":      ("Equity & Liabilities", "Current Liabilities"),
            "Suspense A/c":             ("Equity & Liabilities", "Suspense"),
            "Profit & Loss A/c":        ("Equity & Liabilities", "Profit & Loss A/c"),
            "Fixed Assets":             ("Assets",               "Fixed Assets"),
            "Current Assets":           ("Assets",               "Current Assets"),
            "Loans & Advances (Asset)": ("Assets",               "Current Assets"),
            "Investments":              ("Assets",               "Investments"),
            "Misc. Expenses (Asset)":   ("Assets",               "Misc. Expenses"),
        }
        # fetch_balance_sheet now returns {group_name: {"total": float, "items": [LedgerBalance]}}
        bs_raw = self.api.fetch_balance_sheet(self.to_date)
        for group_name, group_data in bs_raw.items():
            total  = group_data["total"]
            items  = group_data["items"]   # list[LedgerBalance]

            if group_name in bs_group_section:
                section, group = bs_group_section[group_name]
            elif total > 0:
                section, group = "Equity & Liabilities", "Other Liabilities"
            else:
                section, group = "Assets", "Other Assets"

            # Create the group with the overall total
            self._add_to_report(bs_report, section, group, group_name, total)

            # Populate individual ledger items (replace the self-entry added by _add_to_report)
            if items:
                rg = bs_report["sections"][section][group]
                rg["items"] = {}   # clear the group-name self-entry
                for item in items:
                    rg["items"][item["ledger_name"]] = {
                        "name":      item["ledger_name"],
                        "amount":    item["amount"],
                        "breakdown": None,
                    }

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
