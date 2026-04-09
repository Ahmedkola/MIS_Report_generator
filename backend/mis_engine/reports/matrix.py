from schemas import MatrixReport, MatrixRow, COST_CENTERS, COST_CENTER_GROUPS, UNIT_COLUMNS, BUILDING_GENERAL_CC_MAPPING
from .base import BaseReportProcessor

class MatrixReportProcessor(BaseReportProcessor):
    def process(self) -> list[MatrixReport]:
        matrix_rows = {
            "Gross Sales":      { c: 0.0 for c in COST_CENTERS },
            "Net Sales":        { c: 0.0 for c in COST_CENTERS },
            "Other Income":     { c: 0.0 for c in COST_CENTERS },
            "Direct Expenses":  { c: 0.0 for c in COST_CENTERS },
            "Gross Profit":     { c: 0.0 for c in COST_CENTERS },
            "Indirect Expenses":{ c: 0.0 for c in COST_CENTERS },
            "Interest":         { c: 0.0 for c in COST_CENTERS },
            "EBIDTA":           { c: 0.0 for c in COST_CENTERS },
            "EBIDTA %":         { c: 0.0 for c in COST_CENTERS },
            "PBT":              { c: 0.0 for c in COST_CENTERS },
            "Occupancy %":      { c: 0.0 for c in COST_CENTERS },
        }

        cols_with_unit_sales: set[str] = set()

        for item in self.raw_data:
            name = item["ledger_name"]
            amount = item["amount"]
            if amount <= 0:
                continue
            mapping = self.mappings.get(name)
            if not mapping or not mapping.cost_center:
                continue
            col = mapping.cost_center
            if col not in matrix_rows["Gross Sales"]:
                continue
            if mapping.report_section == 'Excluded' and 'sales' in name.lower():
                matrix_rows["Gross Sales"][col] += amount
                matrix_rows["Net Sales"][col]   += amount
                cols_with_unit_sales.add(col)

        for item in self.raw_data:
            mapping = self.mappings.get(item["ledger_name"])
            if (mapping and mapping.cost_center
                    and mapping.report_group == 'Sales Accounts'
                    and mapping.report_section == 'Income'):
                col = mapping.cost_center
                if col in matrix_rows["Gross Sales"] and col not in cols_with_unit_sales:
                    matrix_rows["Gross Sales"][col] += item["amount"]
                    matrix_rows["Net Sales"][col]   += item["amount"]

        # ── Accumulate expenses per building column ────────────────────────────
        for col_name, tally_cost_centers in COST_CENTER_GROUPS.items():
            if col_name == "Total":
                continue

            for t_cc in tally_cost_centers:
                ledgers = self.api.fetch_cost_center_breakup(self.from_date, self.to_date, t_cc)

                for ledger in ledgers:
                    name   = ledger["ledger_name"]
                    amount = ledger["amount"]   # absolute value

                    mapping = self.mappings.get(name)
                    if not mapping:
                        continue

                    report_group = mapping.report_group or ""
                    section      = mapping.report_section or ""
                    line         = mapping.line_item or name

                    if report_group == 'Sales Accounts':
                        pass

                    elif report_group == 'Indirect Incomes':
                        matrix_rows["Other Income"][col_name] += amount

                    elif section == 'Direct Expenses' or report_group == 'Direct Expenses':
                        matrix_rows["Direct Expenses"][col_name] += amount

                    elif 'Expenses' in section and 'Indirect' in report_group:
                        if "interest" in line.lower():
                            matrix_rows["Interest"][col_name] += amount
                        else:
                            matrix_rows["Indirect Expenses"][col_name] += amount

        # ── Distribute "General" CC overhead to each building column ───────────
        # Count eligible units per building (same exclusion rules as unit report)
        eligible_per_bldg: dict[str, int] = {}
        for _disp, _cc, _bldg in UNIT_COLUMNS:
            if _cc is None or _bldg == "General":
                continue
            if "penthouse" in _cc.lower():
                continue
            eligible_per_bldg[_bldg] = eligible_per_bldg.get(_bldg, 0) + 1

        total_eligible = sum(eligible_per_bldg.values())

        if total_eligible > 0:
            gen_ledgers = self.api.fetch_cost_center_breakup(
                self.from_date, self.to_date, "General"
            )
            _gen_office_admin = 0.0
            _gen_conveyance   = 0.0
            _gen_prof_salary  = 0.0

            for _ledger in gen_ledgers:
                _lname  = _ledger["ledger_name"]
                _amount = _ledger["amount"]   # absolute value
                _lmap   = self.mappings.get(_lname)
                _line   = (_lmap.line_item or _lname) if _lmap else _lname

                if "office admin" in _line.lower() or "office admin" in _lname.lower():
                    _gen_office_admin += _amount
                elif "conveyance" in _line.lower() or "travelling" in _line.lower():
                    _gen_conveyance += _amount
                elif "professional" in _line.lower() or "professional" in _lname.lower():
                    _gen_prof_salary += _amount
                elif _line == "Salary":
                    _gen_prof_salary += _amount   # GRM salary

            # Add per-building share = per_unit_share × units_in_building
            for col_name, n_units in eligible_per_bldg.items():
                if col_name not in matrix_rows["Indirect Expenses"]:
                    continue
                share = n_units / total_eligible
                matrix_rows["Indirect Expenses"][col_name] += (
                    (_gen_office_admin + _gen_conveyance + _gen_prof_salary) * share
                )
        # ── End overhead distribution ──────────────────────────────────────────

        # ── Compute derived rows per column ───────────────────────────────────
        for col_name in COST_CENTERS:
            if col_name == "Total":
                continue

            ns = matrix_rows["Net Sales"][col_name]
            oi = matrix_rows["Other Income"][col_name]
            de = matrix_rows["Direct Expenses"][col_name]
            ie = matrix_rows["Indirect Expenses"][col_name]
            interest = matrix_rows["Interest"][col_name]

            gp   = ns + oi - de                 # Gross Profit = Revenue - Direct Expenses
            ebitda = gp - ie                    # EBITDA = GP - Indirect (excl. interest)
            pbt  = ebitda - interest            # PBT = EBITDA - Interest

            matrix_rows["Gross Profit"][col_name] = gp
            matrix_rows["EBIDTA"][col_name]       = ebitda
            matrix_rows["PBT"][col_name]          = pbt

            if ns != 0:
                matrix_rows["EBIDTA %"][col_name] = (ebitda / ns) * 100

        # ── Build output rows with Totals ──────────────────────────────────────
        ordered_row_names = [
            "Gross Sales", "Net Sales", "Other Income",
            "Direct Expenses", "Gross Profit",
            "Indirect Expenses", "EBIDTA", "EBIDTA %",
            "Interest", "PBT",
            "Occupancy %",
        ]

        final_rows: list[MatrixRow] = []
        for r_name in ordered_row_names:
            row_data = matrix_rows[r_name]

            row_sum = sum(val for c, val in row_data.items() if c != "Total")

            if r_name == "EBIDTA %":
                tot_ns = matrix_rows["Net Sales"].get("Total", 0)
                if tot_ns == 0:
                    # recompute from scratch before Total is set
                    tot_ns = sum(v for c, v in matrix_rows["Net Sales"].items() if c != "Total")
                row_sum = (matrix_rows["EBIDTA"].get("Total", 0) / tot_ns * 100) if tot_ns != 0 else 0

            row_data["Total"] = row_sum

            final_rows.append({
                "row_name":    r_name,
                "cost_centers": row_data,
                "total":        row_sum,
            })

        return [{
            "period": f"{self.from_date} to {self.to_date}",
            "rows":   final_rows,
        }]
