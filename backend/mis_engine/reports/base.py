import re
from typing import Dict
from mis_engine.models import LedgerMapping

try:
    from schemas import (StandardReport, ReportGroup, LineItem, MatrixReport, MatrixRow,
                         COST_CENTERS, COST_CENTER_GROUPS, UNIT_COLUMNS, UNIT_GENERAL_CCS)
    from tally_api import TallyAPIClient, LedgerBalance
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from schemas import (StandardReport, ReportGroup, LineItem, MatrixReport, MatrixRow,
                         COST_CENTERS, COST_CENTER_GROUPS, UNIT_COLUMNS, UNIT_GENERAL_CCS)
    from tally_api import TallyAPIClient, LedgerBalance

class BaseReportProcessor:
    def __init__(self, from_date: str = "20250401", to_date: str = "20260131"):
        self.from_date = from_date
        self.to_date = to_date
        self.api = TallyAPIClient(timeout=120)
        self._raw_data = None
        self._mappings = None
        
    @property
    def raw_data(self):
        if self._raw_data is None:
            self._raw_data = self.api.fetch_trial_balance(self.from_date, self.to_date)
        return self._raw_data

    @property
    def mappings(self):
        if self._mappings is None:
            self._mappings = {m.tally_ledger_name: m for m in LedgerMapping.objects.all()}
        return self._mappings

    def _add_to_report(self, report: StandardReport, section: str, group: str, line_item: str, amount: float):
        if section not in report["sections"]:
            report["sections"][section] = {}
        sec = report["sections"][section]
        if group not in sec:
            sec[group] = { "group_name": group, "items": {}, "subtotal": 0.0 }
        grp = sec[group]
        if line_item not in grp["items"]:
            grp["items"][line_item] = { "name": line_item, "amount": 0.0, "breakdown": [] }
        grp["items"][line_item]["amount"] += amount
        grp["subtotal"] += amount

