import re
from typing import Dict
from mis_engine.models import LedgerMapping

# schemas.py and tally_api.py are in the project root
try:
    from schemas import (StandardReport, ReportGroup, LineItem, MatrixReport, MatrixRow,
                         COST_CENTERS, COST_CENTER_GROUPS, UNIT_COLUMNS, UNIT_GENERAL_CCS)
    from tally_api import TallyAPIClient, LedgerBalance
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from schemas import (StandardReport, ReportGroup, LineItem, MatrixReport, MatrixRow,
                         COST_CENTERS, COST_CENTER_GROUPS, UNIT_COLUMNS, UNIT_GENERAL_CCS)
    from tally_api import TallyAPIClient, LedgerBalance


class MISProcessor:
    """
    Consumes raw XML data streams from Tally API and processes them
    into the JSON schemas dictated by `schemas.py` using DB mappings.
    """
    
    def __init__(self, from_date: str = "20250401", to_date: str = "20260131"):
        self.from_date = from_date
        self.to_date = to_date
        self.api = TallyAPIClient()
    
    def process_standard_reports(self) -> Dict[str, StandardReport]:
        self.raw_data = self.api.fetch_trial_balance(self.from_date, self.to_date)
        raw_ledgers = self.raw_data
        if not raw_ledgers:
            raise ValueError("Tally returned 0 ledgers. Check connection or dates.")
            
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
        
        # Load all mappings into memory for ultra-fast O(1) assembly loop
        mappings = {m.tally_ledger_name: m for m in LedgerMapping.objects.all()}
        
        for ledger in raw_ledgers:
            ledger_name = ledger["ledger_name"]
            amount = ledger["amount"]
            
            mapping = mappings.get(ledger_name)
            
            # If a ledger exists in Tally but not in our DB, catch it in "Unmapped"
            if not mapping:
                # We categorize Unmapped based on its natural sign just for safety
                unmapped_section = "Income" if amount >= 0 else "Expenses"
                self._add_to_report(pnl_report, "Unmapped", unmapped_section, ledger_name, amount)
                continue
                
            report_section = mapping.report_section  
            report_group = mapping.report_group      
            line_item = mapping.line_item            
            
            # Skip Tally group-level aggregates that would double-count child ledgers
            if report_section.lower() == "excluded":
                continue

            # Route to P&L vs Balance Sheet appropriately
            if report_section.lower() in ["income", "expenses", "direct expenses", "indirect expenses"]:
                self._add_to_report(pnl_report, report_section, report_group, line_item, amount)
            else:
                self._add_to_report(bs_report, report_section, report_group, line_item, amount)

        self._calculate_summaries(pnl_report, bs_report)

        # ── Balance Sheet: fetch at GROUP level directly from Tally BS report ──
        # The trial balance returns ALL hierarchy levels (groups + children) so
        # we'd double-count if we build BS from it.  Tally's Balance Sheet report
        # without EXPLODEFLAG returns one row per top-level group — matching the
        # values Tally itself displays (Fixed Assets=1,67,95,524 etc.).
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
            # Unknown groups: heuristic — positive = liability, negative = asset
            elif amount > 0:
                self._add_to_report(bs_report, "Equity & Liabilities", "Other Liabilities", group_name, amount)
            else:
                self._add_to_report(bs_report, "Assets", "Other Assets", group_name, amount)

        return {
            "pnl": pnl_report,
            "balance_sheet": bs_report
        }

    def _add_to_report(self, report: StandardReport, section: str, group: str, line_item: str, amount: float):
        """Assembles dynamically categorized ledgers into the Python dictionary"""
        if section not in report["sections"]:
            report["sections"][section] = {}
            
        sec = report["sections"][section]
        if group not in sec:
            sec[group] = {
                "group_name": group,
                "items": {},
                "subtotal": 0.0
            }
            
        grp = sec[group]
        if line_item not in grp["items"]:
            grp["items"][line_item] = {
                "name": line_item,
                "amount": 0.0,
                "breakdown": []
            }
            
        grp["items"][line_item]["amount"] += amount
        grp["subtotal"] += amount

    def _calculate_summaries(self, pnl: StandardReport, bs: StandardReport):
        """The core Math Engine for deriving final figures."""
        total_income = sum(g["subtotal"] for g in pnl["sections"].get("Income", {}).values())

        # Expenses live in TWO top-level sections:
        #   "Direct Expenses"  — trading/operating costs (RENT, Electricity, etc.)
        #   "Expenses"         — indirect/overhead costs (Salary, Professional Fees, etc.)
        direct_expenses   = sum(g["subtotal"] for g in pnl["sections"].get("Direct Expenses", {}).values())
        indirect_expenses = sum(g["subtotal"] for g in pnl["sections"].get("Expenses", {}).values())
        total_expenses    = direct_expenses + indirect_expenses

        # In our system: Income = +ve (Cr), Expenses = -ve (Dr)
        # Net Profit = Total Income (positive) + Total Expenses (negative)
        gross_profit = total_income + direct_expenses     # before indirect costs
        net_profit   = gross_profit + indirect_expenses
        
        pnl["summary"] = {
            "total_income":    total_income,
            "direct_expenses": direct_expenses,
            "indirect_expenses": indirect_expenses,
            "total_expenses":  total_expenses,
            "gross_profit":    gross_profit,
            "net_profit":      net_profit,
        }

    def process_matrix_report(self) -> list[MatrixReport]:
        """
        Phase 5 API: Fetches the building-wise P&L.
        Combines explicitly mapped Revenue ledgers from Trial Balance with 
        dynamic Expense ledgers from Tally's native Cost Centre Breakups.
        """
        # 1. Initialize empty Matrix structures mapping 1:1 with Excel columns
        matrix_rows = {
            "Gross Sales": { c: 0.0 for c in COST_CENTERS },
            "Net Sales": { c: 0.0 for c in COST_CENTERS },
            "Other Income": { c: 0.0 for c in COST_CENTERS },
            "Direct Expenses": { c: 0.0 for c in COST_CENTERS },
            "Gross Profit": { c: 0.0 for c in COST_CENTERS },
            "Indirect Expenses": { c: 0.0 for c in COST_CENTERS },
            "EBIDTA": { c: 0.0 for c in COST_CENTERS },
            "EBIDTA %": { c: 0.0 for c in COST_CENTERS },
            "Occupancy %": { c: 0.0 for c in COST_CENTERS }
        }
        
        mappings = {m.tally_ledger_name: m for m in LedgerMapping.objects.all()}
        
        # 1.5 Inject Gross Sales from unit-level sales ledgers
        #
        # The accountant created individual unit Sales A/c ledgers (e.g. 'Kora 2 303 Sales A/c',
        # 'EEE 201 Sales A/C', etc.) tagged to cost_center columns.  These are marked Excluded
        # in the P&L (to avoid double-counting with building-level parent totals), but for the
        # matrix they are the authoritative per-column source.
        #
        # Building-level totals ('Koramangala', 'East End Enclave', etc.) are NOT used here
        # because they are parent sums of the unit-level ledgers above and would double-count.
        #
        # For buildings that have NO unit-level data (JPN Hotel, Prestige, JPN 202), the
        # building-level ledger (report_group='Sales Accounts', report_section='Income') is
        # used as a fallback.
        cols_with_unit_sales: set[str] = set()

        for item in self.raw_data:
            name = item["ledger_name"]
            amount = item["amount"]
            if amount <= 0:
                continue
            mapping = mappings.get(name)
            if not mapping or not mapping.cost_center:
                continue
            col = mapping.cost_center
            if col not in matrix_rows["Gross Sales"]:
                continue
            # Unit-level sales: Excluded status + positive Cr amount + "sales" in name
            if mapping.report_section == 'Excluded' and 'sales' in name.lower():
                matrix_rows["Gross Sales"][col] += amount
                matrix_rows["Net Sales"][col] += amount
                cols_with_unit_sales.add(col)

        # Fallback: buildings without any unit-level sales data
        for item in self.raw_data:
            mapping = mappings.get(item["ledger_name"])
            if (mapping and mapping.cost_center
                    and mapping.report_group == 'Sales Accounts'
                    and mapping.report_section == 'Income'):
                col = mapping.cost_center
                if col in matrix_rows["Gross Sales"] and col not in cols_with_unit_sales:
                    matrix_rows["Gross Sales"][col] += item["amount"]
                    matrix_rows["Net Sales"][col] += item["amount"]
        
        # 2. Iterate through 22 target Matrix columns for Expenses
        for col_name, tally_cost_centers in COST_CENTER_GROUPS.items():
            if col_name == "Total":
                continue 
                
            for t_cc in tally_cost_centers:
                ledgers = self.api.fetch_cost_center_breakup(self.from_date, self.to_date, t_cc)
                
                for ledger in ledgers:
                    name = ledger["ledger_name"]
                    amount = ledger["amount"]
                    
                    mapping = mappings.get(name)
                    if not mapping:
                        continue
                        
                    report_group = mapping.report_group
                    
                    # Matrix Row Standard Allocation Logic
                    if report_group == 'Sales Accounts':
                        pass # Processed globally above to avoid double-counting
                        
                    elif report_group == 'Indirect Incomes':
                        matrix_rows["Other Income"][col_name] += amount
                        
                    elif mapping.report_section == 'Direct Expenses' or report_group == 'Direct Expenses':
                        matrix_rows["Direct Expenses"][col_name] += amount
                        
                    elif 'Expenses' in mapping.report_section and 'Indirect' in report_group:
                        matrix_rows["Indirect Expenses"][col_name] += amount

            # Run Math Pivot Engine for Column (Gross Profit, EBIDTA, EBIDTA %)
            ns = matrix_rows["Net Sales"][col_name]
            oi = matrix_rows["Other Income"][col_name]
            de = matrix_rows["Direct Expenses"][col_name] # Dr = negative
            ie = matrix_rows["Indirect Expenses"][col_name] # Dr = negative
            
            matrix_rows["Gross Profit"][col_name] = ns + oi + de
            matrix_rows["EBIDTA"][col_name] = matrix_rows["Gross Profit"][col_name] + ie
            
            if ns != 0:
                matrix_rows["EBIDTA %"][col_name] = (matrix_rows["EBIDTA"][col_name] / ns) * 100
        
        # 4. Run "Total" sums across the rows
        ordered_row_names = ["Gross Sales", "Net Sales", "Other Income", "Direct Expenses", "Gross Profit", "Indirect Expenses", "EBIDTA", "EBIDTA %", "Occupancy %"]
        
        final_rows: list[MatrixRow] = [] # typed list matching schemas.py MatrixRow
        for r_name in ordered_row_names:
            row_data = matrix_rows[r_name]
            
            row_sum = sum(val for c, val in row_data.items() if c != "Total")
            
            if r_name == "EBIDTA %":
                tot_ns = matrix_rows["Net Sales"]["Total"] if "Net Sales" in matrix_rows else 0
                row_sum = (matrix_rows["EBIDTA"]["Total"] / tot_ns * 100) if tot_ns != 0 else 0
                
            row_data["Total"] = row_sum
            
            # Explicit type coercion for typed dict compliance
            final_rows.append({
                "row_name": r_name,
                "cost_centers": row_data,
                "total": row_sum
            })
            
        return [{
            "period": f"{self.from_date} to {self.to_date}",
            "rows": final_rows
        }]

    # ──────────────────────────────────────────────────────────────────────────
    # Unit-Wise P&L  (Phase 6)
    # ──────────────────────────────────────────────────────────────────────────

    def process_unit_report(self) -> dict:
        """
        Per-unit P&L matching the Excel "Unit-Wise" sheet.

        Data sources:
          • Sales      – trial balance (Excluded Sales A/c ledgers), matched by name
          • Expenses   – Tally CC breakup per individual unit cost center
          • GST / Host Fees – captured from CC breakup when ledger line_item name
                              contains 'gst' or 'host'/'platform'
          • General Office – aggregates all building-overhead General CCs
        """
        if not hasattr(self, 'raw_data'):
            self.raw_data = self.api.fetch_trial_balance(self.from_date, self.to_date)

        mappings = {m.tally_ledger_name: m for m in LedgerMapping.objects.all()}

        # ── Initialise per-unit data dicts ──────────────────────────────────
        unit_data: dict[str, dict] = {}
        for disp, cc, bldg in UNIT_COLUMNS:
            unit_data[disp] = {
                "building": bldg,
                "cc": cc,
                "gross_sales":      0.0,
                "gst":              0.0,
                "host_fees":        0.0,
                "indirect_income":  0.0,
                "direct_exp":       {},   # line_item → signed float (negative = cost)
                "indirect_exp":     {},   # line_item → signed float (negative = cost)
            }

        # ── Step 1: Net Sales from trial balance ────────────────────────────
        # Unit-level Sales A/c ledgers are Excluded in the P&L (to avoid
        # double-counting with building totals) but contain the per-unit net
        # sales amount — the amount CREDITED to the unit ledger in the voucher
        # (i.e. AFTER host fee netting by Airbnb, BEFORE adding back GST/Host).
        for item in self.raw_data:
            name   = item["ledger_name"]
            amount = item["amount"]
            if amount <= 0:
                continue
            mapping = mappings.get(name)
            if not mapping or mapping.report_section != "Excluded":
                continue
            if "sales" not in name.lower():
                continue
            matched = self._match_sales_ledger_to_unit(name)
            if matched and matched in unit_data:
                # Store as net_sales_ledger for now; gross_sales set in Step 1.5
                unit_data[matched]["gross_sales"] += amount

        # ── Step 1.5: Allocate GST and Host Fees from Ledger Vouchers ───────
        #
        # Output CGST, Output SGST, and Host Fees are SEPARATE company-wide
        # ledgers in Tally — they are NOT tagged to individual unit cost centres.
        # However, they ARE part of individual sales vouchers alongside a specific
        # unit Sales A/c (e.g., "Kora 1 Sales A/c").
        #
        # Strategy: Fetch all ledger vouchers for GST and Host Fees, find the
        # corresponding unit Sales A/c in that voucher, and allocate exactly to it.
        #
        # We query LedgerMapping directly to find all GST and Host Fee ledgers.
        # This is safer than scanning `self.raw_data` because the Tally Trial Balance
        # API omits ledgers with a 0.0 closing balance (which Host Fees often has).
        
        gst_ledgers: list[str] = list(
            LedgerMapping.objects.filter(
                tally_ledger_name__icontains='output'
            ).filter(
                tally_ledger_name__icontains='gst'
            ).values_list('tally_ledger_name', flat=True)
        )
        
        host_ledgers: list[str] = list(
            LedgerMapping.objects.filter(
                tally_ledger_name__icontains='host fee'
            ).values_list('tally_ledger_name', flat=True)
        )

        def _get_target_unit(voucher_lines: set[str]) -> str | None:
            """Finds the sales ledger in the voucher and maps it to a unit column."""
            for lname in voucher_lines:
                if 'sales' in lname.lower():
                    mapped_unit = self._match_sales_ledger_to_unit(lname)
                    if mapped_unit and mapped_unit in unit_data:
                        return mapped_unit
            return None

        # Fetch and allocate GST vouchers
        for gst_ledger in gst_ledgers:
            # Skip SGST to avoid Tally API encoding errors on corrupted spaces (\xef\xbf\xbd)
            if "sgst" in gst_ledger.lower():
                continue
                
            is_cgst = "cgst" in gst_ledger.lower()
            
            vouchers = self.api.fetch_ledger_vouchers(gst_ledger, self.from_date, self.to_date)
            for vch in vouchers:
                target_unit = _get_target_unit(vch["lines"])
                if target_unit:
                    # India GST rule: intra-state sales have equal CGST and SGST.
                    # We double CGST to account for SGST dynamically without needing to fetch SGST.
                    # If it is IGST, we add the exact amount (multiplier 1).
                    multiplier = 2.0 if is_cgst else 1.0
                    unit_data[target_unit]["gst"] += vch["amount"] * multiplier

        # Fetch and allocate Host Fee vouchers
        for host_ledger in host_ledgers:
            vouchers = self.api.fetch_ledger_vouchers(host_ledger, self.from_date, self.to_date)
            for vch in vouchers:
                target_unit = _get_target_unit(vch["lines"])
                if target_unit:
                    unit_data[target_unit]["host_fees"] += vch["amount"]

        # After exact allocation, back-calculate Gross Sales
        for d in unit_data.values():
            d["gross_sales"] = d["gross_sales"] + d["gst"] + d["host_fees"]

        # ── Step 2: Expenses from CC breakup ────────────────────────────────
        for disp, cc, bldg in UNIT_COLUMNS:
            if cc is None:
                # General Office: sum all building-overhead CCs
                all_ledgers = []
                for gen_cc in UNIT_GENERAL_CCS:
                    all_ledgers.extend(
                        self.api.fetch_cost_center_breakup(self.from_date, self.to_date, gen_cc)
                    )
            else:
                all_ledgers = self.api.fetch_cost_center_breakup(
                    self.from_date, self.to_date, cc
                )

            for ledger in all_ledgers:
                lname   = ledger["ledger_name"]
                lamount = -ledger["amount"] if ledger["dr_cr"] == "Dr" else ledger["amount"]
                lmap    = mappings.get(lname)
                if not lmap:
                    continue

                group   = lmap.report_group or ""
                section = lmap.report_section or ""
                line    = lmap.line_item or lname

                if group == "Sales Accounts":
                    continue   # handled from trial balance above

                if group == "Indirect Incomes":
                    unit_data[disp]["indirect_income"] += lamount
                elif section == "Direct Expenses" or group == "Direct Expenses":
                    unit_data[disp]["direct_exp"][line] = (
                        unit_data[disp]["direct_exp"].get(line, 0.0) + lamount
                    )
                elif "Indirect" in group or (section == "Expenses" and "Direct" not in group):
                    unit_data[disp]["indirect_exp"][line] = (
                        unit_data[disp]["indirect_exp"].get(line, 0.0) + lamount
                    )

        # ── Step 3: Derive calculated metrics ───────────────────────────────
        for disp, d in unit_data.items():
            # net_sales = gross_sales - gst - host_fees  (restores to unit ledger amount)
            d["net_sales"]         = d["gross_sales"] - d["gst"] - d["host_fees"]
            d["net_revenue"]       = d["net_sales"] + d["indirect_income"]
            d["total_direct_exp"]  = sum(d["direct_exp"].values())
            d["gross_profit"]      = d["net_sales"] + d["total_direct_exp"]
            d["total_indirect_exp"] = sum(d["indirect_exp"].values())
            d["ebitda"]            = d["gross_profit"] + d["total_indirect_exp"]
            d["interest"]          = 0.0
            d["depreciation"]      = 0.0
            d["pbt"]               = d["ebitda"]   # interest/depreciation not CC-tagged

        # ── Step 4: Collect all unique expense line-item names ───────────────
        all_direct_lines:   list[str] = []
        all_indirect_lines: list[str] = []
        seen_d: set[str] = set()
        seen_i: set[str] = set()
        for d in unit_data.values():
            for k in d["direct_exp"]:
                if k not in seen_d:
                    all_direct_lines.append(k)
                    seen_d.add(k)
            for k in d["indirect_exp"]:
                if k not in seen_i:
                    all_indirect_lines.append(k)
                    seen_i.add(k)

        # Preferred order for direct expense rows (matches Excel)
        DIRECT_ORDER = [
            "Rent", "Salary", "Consumables", "Electricity", "Water Bill",
            "Maintenance", "Repairs", "House Hold Items",
            "Pillow Covers/Bed Sheets/Clothing", "Brokerage",
        ]
        INDIRECT_ORDER = [
            "Office Admin", "Conveyance/ Travelling Expenses",
            "Professional Fees/GRM Salary", "Office Rent",
            "Rates and taxes", "In Eligible GST Input", "CXO Salary",
        ]
        def _order(names, preferred):
            ordered = [n for n in preferred if n in names]
            ordered += sorted(n for n in names if n not in preferred)
            return ordered

        direct_rows   = _order(all_direct_lines,   DIRECT_ORDER)
        indirect_rows = _order(all_indirect_lines, INDIRECT_ORDER)

        return {
            "period":         f"{self.from_date} to {self.to_date}",
            "columns":        [(disp, bldg) for disp, cc, bldg in UNIT_COLUMNS],
            "direct_rows":    direct_rows,
            "indirect_rows":  indirect_rows,
            "data":           unit_data,
        }

    def _match_sales_ledger_to_unit(self, ledger_name: str) -> str | None:
        """
        Map a unit-level Sales A/c ledger name to a UNIT_COLUMNS display_name.

        Special case – Kora 2 units:
          "Kora 2 201 Sales A/c"  →  display "Kora-201"  (CC = "Kora-201")
          "Kora 2 402 Sales A/c"  →  display "Kora 402"  (CC = "Kora 402")

        General case:
          Normalise both strings (strip spaces/hyphens/underscores, lowercase)
          and check if the CC norm appears as a substring of the ledger name norm.
          Longest CC match wins to avoid "KN 1" matching "KN 10".
        """
        name_lower = ledger_name.lower()

        # ── Kora-2 units ("Kora 2 NNN Sales A/c") ───────────────────────────
        # Match directly to display name "Koramangala-New NNN" to avoid any
        # conflict with small-building CCs "Kora-101/102/103".
        kora2_m = re.search(r"kora\s*2\s+(\d+)", name_lower)
        if kora2_m:
            num = kora2_m.group(1)
            target = f"Koramangala-New {num}"
            for disp, _, _ in UNIT_COLUMNS:
                if disp == target:
                    return disp
            return None

        # ── Koramangala small-building units ────────────────────────────────
        # Handles all known Tally naming variants:
        #   "Kormangala 1 Sales A/c"      (typo: Korm vs Kora)
        #   "Koramangala - 2 Sales A/c"   (spaces around hyphen)
        #   "Koramangala - 3 Sales A/C"   (capital C)
        # Unit number extracted → "Koramangala-{N}" → looked up in UNIT_COLUMNS
        kora_small_m = re.search(r"kor[a-z]*mangala?\s*[-\s]*(\d+)\s+sales", name_lower)
        if kora_small_m:
            num = kora_small_m.group(1)
            target = f"Koramangala-{num}"
            for disp, cc, _ in UNIT_COLUMNS:
                if disp == target:
                    return disp
            return None

        # ── General case: normalised substring match ─────────────────────────
        def _norm(s: str) -> str:
            return re.sub(r"[\s\-_]+", "", s.lower())

        name_norm = _norm(ledger_name)

        # Sort longest CC first to prefer precise matches
        candidates = sorted(
            [(d, c, b) for d, c, b in UNIT_COLUMNS if c],
            key=lambda x: len(x[1]),
            reverse=True,
        )
        for disp, cc, _ in candidates:
            if _norm(cc) in name_norm:
                return disp

        return None
