import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from mis_engine.models import LedgerMapping

fixes = [
    ("Household Items", "Direct Expenses", "Direct Expenses", "House Hold Items"),
    ("Pillow/Cover", "Direct Expenses", "Direct Expenses", "Pillow Covers/Bed Sheets/Clothing"),
    ("Brokerage", "Direct Expenses", "Direct Expenses", "Brokerage"),
]

for name, sec, grp, line in fixes:
    n = LedgerMapping.objects.filter(tally_ledger_name=name).update(
        report_section=sec,
        report_group=grp,
        line_item=line
    )
    print(f"Updated {n} rows for {name} -> {sec} / {line}")

