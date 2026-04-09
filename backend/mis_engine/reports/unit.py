import re
from .base import BaseReportProcessor
from mis_engine.models import LedgerMapping
from schemas import UNIT_COLUMNS, UNIT_GENERAL_CCS, BUILDING_GENERAL_CC_MAPPING

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
            }

        for item in self.raw_data:
            name   = item["ledger_name"]
            amount = item["amount"]
            if amount <= 0:
                continue
            mapping = self.mappings.get(name)
            if not mapping or mapping.report_section != "Excluded":
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
                    unit_data[disp]["indirect_exp"][line] = (
                        unit_data[disp]["indirect_exp"].get(line, 0.0) + lamount
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

        for disp, d in unit_data.items():
            d["net_sales"]         = d["gross_sales"] - d["gst"] - d["host_fees"]
            d["net_revenue"]       = d["net_sales"] + d["indirect_income"]
            d["total_direct_exp"]  = sum(d["direct_exp"].values())
            d["gross_profit"]      = d["net_sales"] + d["total_direct_exp"]
            d["total_indirect_exp"] = sum(d["indirect_exp"].values())
            d["ebitda"]            = d["gross_profit"] + d["total_indirect_exp"]
            d["interest"]          = 0.0
            d["depreciation"]      = 0.0
            d["pbt"]               = d["ebitda"]

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
