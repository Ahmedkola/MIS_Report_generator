from schemas import MatrixReport, MatrixRow
from mis_engine.models import Building
from .base import BaseReportProcessor


def aggregate_from_unit(unit_report: dict) -> list[MatrixReport]:
    """
    Build the building-wise matrix by summing unit-wise data per building.
    This guarantees matrix totals match the unit-wise report exactly.
    """
    buildings_ordered = list(
        Building.objects.filter(is_active=True).order_by('column_order')
        .values_list('display_name', flat=True)
    )
    cost_centers = buildings_ordered + ["Total"]

    def zero_row():
        return {c: 0.0 for c in cost_centers}

    matrix = {
        "Gross Sales":       zero_row(),
        "Net Sales":         zero_row(),
        "Other Income":      zero_row(),
        "Direct Expenses":   zero_row(),
        "Gross Profit":      zero_row(),
        "Indirect Expenses": zero_row(),
        "Interest":          zero_row(),
        "EBIDTA":            zero_row(),
        "EBIDTA %":          zero_row(),
        "PBT":               zero_row(),
        "Occupancy %":       zero_row(),
    }

    for disp, d in unit_report["data"].items():
        bldg = d.get("building")
        if not bldg or bldg == "General" or bldg not in matrix["Gross Sales"]:
            continue

        matrix["Gross Sales"][bldg]       += d.get("gross_sales", 0.0)
        matrix["Net Sales"][bldg]         += d.get("net_sales", 0.0)
        matrix["Other Income"][bldg]      += d.get("indirect_income", 0.0)
        # direct_exp values are negative (Dr = expense); total_direct_exp is negative sum
        matrix["Direct Expenses"][bldg]   += abs(d.get("total_direct_exp", 0.0))
        matrix["Indirect Expenses"][bldg] += abs(d.get("total_indirect_exp", 0.0))
        matrix["Interest"][bldg]          += abs(d.get("interest", 0.0))
        matrix["Gross Profit"][bldg]      += d.get("gross_profit", 0.0)
        matrix["EBIDTA"][bldg]            += d.get("ebitda", 0.0)
        matrix["PBT"][bldg]               += d.get("pbt", 0.0)

    # Compute EBIDTA % per building
    for bldg in buildings_ordered:
        ns = matrix["Net Sales"][bldg]
        if ns != 0:
            matrix["EBIDTA %"][bldg] = (matrix["EBIDTA"][bldg] / ns) * 100

    # Compute totals
    for metric in ["Gross Sales", "Net Sales", "Other Income", "Direct Expenses",
                   "Gross Profit", "Indirect Expenses", "Interest", "EBIDTA", "PBT"]:
        matrix[metric]["Total"] = sum(
            v for c, v in matrix[metric].items() if c != "Total"
        )

    tot_ns = matrix["Net Sales"]["Total"]
    if tot_ns != 0:
        matrix["EBIDTA %"]["Total"] = (matrix["EBIDTA"]["Total"] / tot_ns) * 100

    ordered_rows = [
        "Gross Sales", "Net Sales", "Other Income",
        "Direct Expenses", "Gross Profit",
        "Indirect Expenses", "EBIDTA", "EBIDTA %",
        "Interest", "PBT", "Occupancy %",
    ]

    final_rows: list[MatrixRow] = []
    for r_name in ordered_rows:
        row_data = matrix[r_name]
        final_rows.append({
            "row_name":     r_name,
            "cost_centers": row_data,
            "total":        row_data["Total"],
        })

    return [{
        "period": unit_report["period"],
        "rows":   final_rows,
    }]


class MatrixReportProcessor(BaseReportProcessor):
    def process(self) -> list[MatrixReport]:
        from .unit import UnitReportProcessor
        unit_report = UnitReportProcessor(self.from_date, self.to_date).process()
        return aggregate_from_unit(unit_report)
