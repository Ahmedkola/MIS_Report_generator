from schemas import MatrixReport, MatrixRow, COST_CENTERS, COST_CENTER_GROUPS
from .base import BaseReportProcessor

class MatrixReportProcessor(BaseReportProcessor):
    def process(self) -> list[MatrixReport]:
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
                matrix_rows["Net Sales"][col] += amount
                cols_with_unit_sales.add(col)

        for item in self.raw_data:
            mapping = self.mappings.get(item["ledger_name"])
            if (mapping and mapping.cost_center
                    and mapping.report_group == 'Sales Accounts'
                    and mapping.report_section == 'Income'):
                col = mapping.cost_center
                if col in matrix_rows["Gross Sales"] and col not in cols_with_unit_sales:
                    matrix_rows["Gross Sales"][col] += item["amount"]
                    matrix_rows["Net Sales"][col] += item["amount"]
        
        for col_name, tally_cost_centers in COST_CENTER_GROUPS.items():
            if col_name == "Total":
                continue 
                
            for t_cc in tally_cost_centers:
                ledgers = self.api.fetch_cost_center_breakup(self.from_date, self.to_date, t_cc)
                
                for ledger in ledgers:
                    name = ledger["ledger_name"]
                    amount = ledger["amount"]
                    
                    mapping = self.mappings.get(name)
                    if not mapping:
                        continue
                        
                    report_group = mapping.report_group
                    
                    if report_group == 'Sales Accounts':
                        pass 
                        
                    elif report_group == 'Indirect Incomes':
                        matrix_rows["Other Income"][col_name] += amount
                        
                    elif mapping.report_section == 'Direct Expenses' or report_group == 'Direct Expenses':
                        matrix_rows["Direct Expenses"][col_name] += amount
                        
                    elif 'Expenses' in mapping.report_section and 'Indirect' in report_group:
                        matrix_rows["Indirect Expenses"][col_name] += amount

            ns = matrix_rows["Net Sales"][col_name]
            oi = matrix_rows["Other Income"][col_name]
            de = matrix_rows["Direct Expenses"][col_name]
            ie = matrix_rows["Indirect Expenses"][col_name]
            
            matrix_rows["Gross Profit"][col_name] = ns + oi + de
            matrix_rows["EBIDTA"][col_name] = matrix_rows["Gross Profit"][col_name] + ie
            
            if ns != 0:
                matrix_rows["EBIDTA %"][col_name] = (matrix_rows["EBIDTA"][col_name] / ns) * 100
        
        ordered_row_names = ["Gross Sales", "Net Sales", "Other Income", "Direct Expenses", "Gross Profit", "Indirect Expenses", "EBIDTA", "EBIDTA %", "Occupancy %"]
        
        final_rows: list[MatrixRow] = []
        for r_name in ordered_row_names:
            row_data = matrix_rows[r_name]
            
            row_sum = sum(val for c, val in row_data.items() if c != "Total")
            
            if r_name == "EBIDTA %":
                tot_ns = matrix_rows["Net Sales"]["Total"] if "Net Sales" in matrix_rows else 0
                row_sum = (matrix_rows["EBIDTA"]["Total"] / tot_ns * 100) if tot_ns != 0 else 0
                
            row_data["Total"] = row_sum
            
            final_rows.append({
                "row_name": r_name,
                "cost_centers": row_data,
                "total": row_sum
            })
            
        return [{
            "period": f"{self.from_date} to {self.to_date}",
            "rows": final_rows
        }]
