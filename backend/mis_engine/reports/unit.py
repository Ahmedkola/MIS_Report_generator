import re
from .base import BaseReportProcessor
from mis_engine.models import LedgerMapping
from schemas import UNIT_COLUMNS, UNIT_GENERAL_CCS, BUILDING_GENERAL_CC_MAPPING, BUILDING_RENT_LEDGER

class UnitReportProcessor(BaseReportProcessor):
    def process(self) -> dict:
        unit_data: dict[str, dict] = {}
        for disp, cc, bldg in UNIT_COLUMNS:
            unit_data[disp] = {
                "building": bldg,
                "cc": cc,
                "gross_sales":      0.0,
                "gst":              0.0,
                "host_fees":        0.0,
                "indirect_income":  0.0,
                "direct_exp":       {},
                "indirect_exp":     {},
                "interest":         0.0,
            }

        for item in self.raw_data:
            name   = item["ledger_name"]
            amount = item["amount"]
            if amount <= 0:
                continue
            if "sales" not in name.lower():
                continue
            matched = self._match_sales_ledger_to_unit(name)
            if matched and matched in unit_data:
                unit_data[matched]["gross_sales"] += amount
        
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
            for lname in voucher_lines:
                if 'sales' in lname.lower():
                    mapped_unit = self._match_sales_ledger_to_unit(lname)
                    if mapped_unit and mapped_unit in unit_data:
                        return mapped_unit
            return None

        for gst_ledger in gst_ledgers:
            if "sgst" in gst_ledger.lower():
                continue
                
            is_cgst = "cgst" in gst_ledger.lower()
            
            vouchers = self.api.fetch_ledger_vouchers(gst_ledger, self.from_date, self.to_date)
            for vch in vouchers:
                target_unit = _get_target_unit(vch["lines"])
                if target_unit:
                    multiplier = 2.0 if is_cgst else 1.0
                    unit_data[target_unit]["gst"] += vch["amount"] * multiplier

        for host_ledger in host_ledgers:
            vouchers = self.api.fetch_ledger_vouchers(host_ledger, self.from_date, self.to_date)
            for vch in vouchers:
                target_unit = _get_target_unit(vch["lines"])
                if target_unit:
                    unit_data[target_unit]["host_fees"] += vch["amount"]

        for d in unit_data.values():
            d["gross_sales"] = d["gross_sales"] + d["gst"] + d["host_fees"]

        # ── Pre-fetch: General CC salary and consumables shares per unit ───────
        building_salary_shares:      dict[str, float] = {}
        building_consumables_shares: dict[str, float] = {}
        building_electricity_shares: dict[str, float] = {}
        building_maintenance_shares: dict[str, float] = {}

        # Count eligible units per building (exclude cc=None, bldg="General", penthouse)
        eligible_units_per_building: dict[str, list[str]] = {}
        for disp, cc, bldg in UNIT_COLUMNS:
            if cc is None or bldg == "General":
                continue
            if "penthouse" in cc.lower():
                continue
            eligible_units_per_building.setdefault(bldg, []).append(disp)

        # ── Pre-fetch: building-level rent from trial balance ─────────────────
        # Index trial balance by ledger name for O(1) lookup (no extra API call)
        _tb_by_name = {lb["ledger_name"]: lb for lb in self.raw_data}

        building_rent_shares: dict[str, float] = {}
        for bldg, rent_ledger in BUILDING_RENT_LEDGER.items():
            if rent_ledger is None:
                continue
            eligible_disps = eligible_units_per_building.get(bldg, [])
            num_units = len(eligible_disps)
            if num_units == 0:
                continue
            tb_entry = _tb_by_name.get(rent_ledger)
            if tb_entry is None or tb_entry["amount"] == 0:
                continue  # ledger not found or zero → fall back to CC breakup
            # trial balance amount is already signed (negative = Dr/expense)
            per_unit = tb_entry["amount"] / num_units
            for disp in eligible_disps:
                building_rent_shares[disp] = per_unit
        # ── End rent pre-fetch ────────────────────────────────────────────────

        # Fetch each building's General CC once; compute per-unit salary & consumables
        for bldg, general_cc in BUILDING_GENERAL_CC_MAPPING.items():
            if general_cc is None:
                continue
            eligible_disps = eligible_units_per_building.get(bldg, [])
            num_units = len(eligible_disps)
            if num_units == 0:
                continue

            gen_ledgers = self.api.fetch_cost_center_breakup(
                self.from_date, self.to_date, general_cc
            )
            total_salary      = 0.0
            total_consumables = 0.0
            total_electricity = 0.0
            total_maintenance = 0.0
            for ledger in gen_ledgers:
                lamount = -ledger["amount"] if ledger["dr_cr"] == "Dr" else ledger["amount"]
                lmap = self.mappings.get(ledger["ledger_name"])
                if not lmap:
                    continue
                line = lmap.line_item or ledger["ledger_name"]
                if line == "Salary":
                    total_salary += lamount
                elif line == "Consumables":
                    total_consumables += lamount
                elif line == "Electricity":
                    total_electricity += lamount
                elif line == "Maintenance":
                    total_maintenance += lamount

            salary_per_unit      = total_salary      / num_units
            consumables_per_unit = total_consumables / num_units
            electricity_per_unit = total_electricity / num_units
            maintenance_per_unit = total_maintenance / num_units
            for disp in eligible_disps:
                building_salary_shares[disp]      = salary_per_unit
                building_consumables_shares[disp] = consumables_per_unit
                building_electricity_shares[disp] = electricity_per_unit
                building_maintenance_shares[disp] = maintenance_per_unit
        # ── End pre-fetch ──────────────────────────────────────────────────────

        # Canonical indirect key names (normalise DB line_item spelling variants)
        _INDIRECT_KEY_MAP: dict[str, str] = {
            "Conveyance / Travelling Expenses":  "Conveyance/ Travelling Expenses",
            "Conveyance/Travelling Expenses":    "Conveyance/ Travelling Expenses",
            "Rates and Taxes":                   "Rates and taxes",
        }

        for disp, cc, bldg in UNIT_COLUMNS:
            if cc is None:
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
                # New direct CC Breakup parser: Dr amounts come as positive abs() value
                # with dr_cr="Dr". Expenses should be negative for the sum() to work correctly.
                lamount = -ledger["amount"] if ledger["dr_cr"] == "Dr" else ledger["amount"]
                lmap    = self.mappings.get(lname)
                if not lmap:
                    continue

                group   = lmap.report_group or ""
                section = lmap.report_section or ""
                line    = lmap.line_item or lname

                if group == "Sales Accounts":
                    continue

                if group == "Indirect Incomes":
                    unit_data[disp]["indirect_income"] += lamount
                elif section == "Direct Expenses" or group == "Direct Expenses":
                    if line == "Salary":
                        pass  # Salary comes from General CC only; skip per-unit CC salary
                    else:
                        unit_data[disp]["direct_exp"][line] = (
                            unit_data[disp]["direct_exp"].get(line, 0.0) + lamount
                        )
                elif "Indirect" in group or (section == "Expenses" and "Direct" not in group):
                    if "interest" in line.lower():
                        unit_data[disp]["interest"] += lamount  # Excluded from EBITDA
                    else:
                        _key = _INDIRECT_KEY_MAP.get(line, line)
                        unit_data[disp]["indirect_exp"][_key] = (
                            unit_data[disp]["indirect_exp"].get(_key, 0.0) + lamount
                        )

            # Apply General CC salary and consumables shares to eligible units
            if cc is not None and bldg != "General":
                salary_share = building_salary_shares.get(disp, 0.0)
                if salary_share != 0.0:
                    unit_data[disp]["direct_exp"]["Salary"] = (
                        unit_data[disp]["direct_exp"].get("Salary", 0.0) + salary_share
                    )
                consumables_share = building_consumables_shares.get(disp, 0.0)
                if consumables_share != 0.0:
                    unit_data[disp]["direct_exp"]["Consumables"] = (
                        unit_data[disp]["direct_exp"].get("Consumables", 0.0) + consumables_share
                    )
                electricity_share = building_electricity_shares.get(disp, 0.0)
                if electricity_share != 0.0:
                    unit_data[disp]["direct_exp"]["Electricity"] = (
                        unit_data[disp]["direct_exp"].get("Electricity", 0.0) + electricity_share
                    )
                maintenance_share = building_maintenance_shares.get(disp, 0.0)
                if maintenance_share != 0.0:
                    unit_data[disp]["direct_exp"]["Maintenance"] = (
                        unit_data[disp]["direct_exp"].get("Maintenance", 0.0) + maintenance_share
                    )

            # Override Rent with building-level ledger value (avoids CC breakup double-count).
            # Falls back to CC breakup value if no pre-fetched share exists.
            if cc is not None and bldg != "General" and disp in building_rent_shares:
                rent_share = building_rent_shares[disp]
                if rent_share != 0.0:
                    unit_data[disp]["direct_exp"]["Rent"] = rent_share

        # ── Post-loop: "General" CC — company-level overhead ──────────────────
        # Fetch once; route to General Office column (with special handling for
        # Salary A/c and Interest Paid), then distribute shares to units with rent.
        _GENERAL_CC = "General"
        gen_ledgers = self.api.fetch_cost_center_breakup(
            self.from_date, self.to_date, _GENERAL_CC
        )

        # Totals to distribute across units with rent
        _gen_office_admin  = 0.0
        _gen_conveyance    = 0.0
        _gen_prof_salary   = 0.0   # Professional Fees + Salary A/c combined

        # Route full amounts into General Office column
        _go = "General Office"
        for _ledger in gen_ledgers:
            _lname   = _ledger["ledger_name"]
            _lamount = -_ledger["amount"] if _ledger["dr_cr"] == "Dr" else _ledger["amount"]
            _lmap    = self.mappings.get(_lname)
            _line    = (_lmap.line_item or _lname) if _lmap else _lname
            _group   = (_lmap.report_group or "") if _lmap else ""
            _section = (_lmap.report_section or "") if _lmap else ""

            if _group == "Sales Accounts":
                continue

            # Capture distribution totals
            if "office admin" in _line.lower() or "office admin" in _lname.lower():
                _gen_office_admin += _lamount
            elif "conveyance" in _line.lower() or "travelling" in _line.lower():
                _gen_conveyance += _lamount
            elif "professional" in _line.lower() or "professional" in _lname.lower():
                _gen_prof_salary += _lamount
            elif _line == "Salary":
                _gen_prof_salary += _lamount   # GRM salary in General CC

            # Route into General Office column
            if _go in unit_data:
                if _group == "Indirect Incomes":
                    unit_data[_go]["indirect_income"] += _lamount
                elif _section == "Direct Expenses" or _group == "Direct Expenses":
                    if _line == "Salary":
                        # GRM salary → indirect, combined as Professional Fees/GRM Salary
                        unit_data[_go]["indirect_exp"]["Professional Fees/GRM Salary"] = (
                            unit_data[_go]["indirect_exp"].get("Professional Fees/GRM Salary", 0.0) + _lamount
                        )
                    else:
                        unit_data[_go]["direct_exp"][_line] = (
                            unit_data[_go]["direct_exp"].get(_line, 0.0) + _lamount
                        )
                elif "Indirect" in _group or (_section == "Expenses" and "Direct" not in _group):
                    if "interest" in _line.lower():
                        unit_data[_go]["interest"] += _lamount
                    elif "professional" in _line.lower() or "professional" in _lname.lower():
                        unit_data[_go]["indirect_exp"]["Professional Fees/GRM Salary"] = (
                            unit_data[_go]["indirect_exp"].get("Professional Fees/GRM Salary", 0.0) + _lamount
                        )
                    else:
                        _key = _INDIRECT_KEY_MAP.get(_line, _line)
                        unit_data[_go]["indirect_exp"][_key] = (
                            unit_data[_go]["indirect_exp"].get(_key, 0.0) + _lamount
                        )

        # Distribute overhead shares to units with rent
        _units_with_rent = [
            disp for disp, d in unit_data.items()
            if d.get("direct_exp", {}).get("Rent", 0.0) != 0.0
            and d["cc"] is not None and d["building"] != "General"
        ]
        _n_rent = len(_units_with_rent)
        if _n_rent > 0:
            _office_share  = _gen_office_admin / _n_rent
            _conv_share    = _gen_conveyance   / _n_rent
            _prof_share    = _gen_prof_salary  / _n_rent
            for _disp in _units_with_rent:
                if _office_share != 0.0:
                    unit_data[_disp]["indirect_exp"]["Office Admin"] = (
                        unit_data[_disp]["indirect_exp"].get("Office Admin", 0.0) + _office_share
                    )
                if _conv_share != 0.0:
                    unit_data[_disp]["indirect_exp"]["Conveyance/ Travelling Expenses"] = (
                        unit_data[_disp]["indirect_exp"].get("Conveyance/ Travelling Expenses", 0.0) + _conv_share
                    )
                if _prof_share != 0.0:
                    unit_data[_disp]["indirect_exp"]["Professional Fees/GRM Salary"] = (
                        unit_data[_disp]["indirect_exp"].get("Professional Fees/GRM Salary", 0.0) + _prof_share
                    )
        # ── End General CC post-loop ───────────────────────────────────────────

        for disp, d in unit_data.items():
            d["net_sales"]          = d["gross_sales"] - d["gst"] - d["host_fees"]
            d["net_revenue"]        = d["net_sales"] + d["indirect_income"]
            d["total_direct_exp"]   = sum(d["direct_exp"].values())
            d["gross_profit"]       = d["net_sales"] + d["total_direct_exp"]
            d["total_indirect_exp"] = sum(d["indirect_exp"].values())
            d["ebitda"]             = d["gross_profit"] + d["total_indirect_exp"]
            # d["interest"] already accumulated above (negative = expense)
            d["depreciation"]       = 0.0
            d["pbt"]                = d["ebitda"] + d["interest"]  # interest is negative → reduces PBT

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
        name_lower = ledger_name.lower()

        kora2_m = re.search(r"kora\s*2\s+(\d+)", name_lower)
        if kora2_m:
            num = kora2_m.group(1)
            target = f"Koramangala-New {num}"
            for disp, _, _ in UNIT_COLUMNS:
                if disp == target:
                    return disp
            return None

        kora_small_m = re.search(r"kor[a-z]*mangala?\s*[-\s]*(\d+)\s+sales", name_lower)
        if kora_small_m:
            num = kora_small_m.group(1)
            target = f"Koramangala-{num}"
            for disp, cc, _ in UNIT_COLUMNS:
                if disp == target:
                    return disp
            return None

        # Lang Ford: "Lang Ford 1F Sales A/c" or "Lang Ford 1 F Sales A/c" → "LF 1"
        lf_m = re.search(r"lang\s*ford\s*(\d+)\s*f", name_lower)
        if lf_m:
            target = f"LF {lf_m.group(1)}"
            for disp, _, _ in UNIT_COLUMNS:
                if disp == target:
                    return disp
            return None

        # Brigade: "ED J 701 Sales A/c" → "ED 701" (cc "ED 701")
        ed_m = re.search(r"ed\b.*?\b(\d{3})\b", name_lower)
        if ed_m:
            target = f"ED {ed_m.group(1)}"
            for disp, _, _ in UNIT_COLUMNS:
                if disp == target:
                    return disp

        def _norm(s: str) -> str:
            return re.sub(r"[\s\-_]+", "", s.lower())

        name_norm = _norm(ledger_name)

        candidates = sorted(
            [(d, c, b) for d, c, b in UNIT_COLUMNS if c],
            key=lambda x: len(x[1]),
            reverse=True,
        )
        for disp, cc, _ in candidates:
            if _norm(cc) in name_norm:
                return disp

        return None
