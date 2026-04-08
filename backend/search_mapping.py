import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from mis_engine.models import LedgerMapping

print("Searching DB for terms...")
terms = ["house", "pillow", "brokerage", "water", "home", "mattress"]
for term in terms:
    print(f"\n--- Term: {term} ---")
    for m in LedgerMapping.objects.filter(tally_ledger_name__icontains=term):
        print(f"  {m.tally_ledger_name} -> {m.report_section} | {m.report_group} | {m.line_item}")
