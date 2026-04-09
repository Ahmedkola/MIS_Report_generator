import sys
from tally_api import TallyAPIClient

client = TallyAPIClient()
res = client.fetch_balance_sheet_group("Direct Expenses", "20260131")
print(res)
