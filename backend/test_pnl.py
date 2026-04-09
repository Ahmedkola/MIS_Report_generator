import sys
import json
from mis_engine.reports.pnl_bs import StandardReportProcessor
from tally_api import TallyAPIClient

client = TallyAPIClient()
from_date = "20250401"
to_date = "20260131"

data = client.fetch_trial_balance(from_date, to_date)
# We need to mock mappings just in case base class complains
class DummyDBMapping:
    def get(self, name): return None

processor = StandardReportProcessor(client, from_date, to_date, data, DummyDBMapping())
reports = processor.process()

print("\n--- P&L Sections ---")
for sec, sec_data in reports["pnl"]["sections"].items():
    print(f"Section: {sec}")
    for group, group_data in sec_data.items():
        print(f"  [{group}] Subtotal: {group_data['subtotal']}")
        # print some ledgers
        print("   " + ", ".join(list(group_data['items'].keys())[:5]))

print("\nP&L Summary:", reports["pnl"]["summary"])
