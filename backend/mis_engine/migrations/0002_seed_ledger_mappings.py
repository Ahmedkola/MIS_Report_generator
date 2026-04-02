"""
0002_seed_ledger_mappings.py
-----------------------------
Data migration: seeds the correct LedgerMapping rows on any fresh database.

This makes `python manage.py migrate` completely self-sufficient — no manual
scripts or management commands need to be run after a fresh install.

Logic is kept in-sync with auto_map.py Phase 1. The same dicts are declared
here (rather than imported) so this migration is a permanent, frozen snapshot
that will always replay correctly even if auto_map.py changes in the future.
"""

from django.db import migrations


# ─────────────────────────────────────────────────────────────────────────────
# Frozen snapshot of Phase 1 mappings at the time of this migration.
# Format: tally_ledger_name -> (report_section, report_group, line_item, cost_center_or_None)
# ─────────────────────────────────────────────────────────────────────────────

EXCLUDED_NAMES = {
    # Tally top-level group summaries — their value = sum of children already mapped
    "Sales Accounts",
    "Direct Expenses",
    "Indirect Expenses",
    "Income",
    "Expenses",
    "Direct Incomes",
    "Indirect Incomes",
    # Per-unit electricity bills
    "EB - COLES PARK", "EB - EAST END ENCLAVE", "EB - ECity",
    "EB - Hebbal", "EB - KALYAN NAGAR", "EB - KASTURI NAGAR / SRK / CMR",
    "EB - KORAMANGALA", "EB - KORAMANGALA-2", "EB - MYSORE",
    "EB - MYSORE FIRENZA", "EB - Manyata", "EB - Viman Nagar",
    "EB JPN", "EB Langford", "EB-Hennur", "EB-JPN Hotel",
    "EB Prestige Waterford 11013", "EB Prestige Waterford 12194",
    # Per-property rent ledgers
    "Brigade Eldorado Rent", "Coles Park Rent A/c", "ECity Rent",
    "East End Enclave Rent", "Hebbal Rent A/c", "Hennur Rent",
    "JPN Hotel Rent A/c", "JPN Hotel Security Deposit",
    "Kalyan Nagar -Rent A/c", "Kasturi Nagar Rent A/c",
    "Kormangala 2 Rent A/c", "Manyata Rent A/c",
    "Mysore Firenza Rent A/C", "Mysore Rent A/C",
    "Viman Nagar Rent A/c", "Lang Ford Rent A/c",
    "Mahaveer Celesse Rent A/c", "JPN 202 Rent A/c",
    "Kormangala 1 Rent A/c", "Langford Rent A/c", "Mahaveer  Rent A/c",
    "Mysore Rent A/c", "Rent Waterford", "Viman Nagar Rent",
}

EXPLICIT_MAPPINGS = {
    # Sales Accounts (building-level — the Excel P&L columns)
    "Coles Park":              ("Income", "Sales Accounts", "Coles Park",        "Coles Park"),
    "East End Enclave":        ("Income", "Sales Accounts", "East End Enclave",  "EEE"),
    "El Dorado":               ("Income", "Sales Accounts", "El Dorado",         None),
    "Electronic City":         ("Income", "Sales Accounts", "Electronic City",   "E-City"),
    "Hebbal":                  ("Income", "Sales Accounts", "Hebbal",            "Hebbal"),
    "Hennur":                  ("Income", "Sales Accounts", "Hennur",            "Hennur"),
    "Kalyan Nagar":            ("Income", "Sales Accounts", "Kalyan Nagar",      "Kalyan Nagar"),
    "Kasturi Nagar":           ("Income", "Sales Accounts", "Kasturi Nagar",     "CMR"),
    "Koramangala":             ("Income", "Sales Accounts", "Koramangala",       "Koramangala"),
    "Koramangala-1":           ("Income", "Sales Accounts", "Koramangala-1",     "Kora-2"),
    "Lang Ford":               ("Income", "Sales Accounts", "Lang Ford",         "Lang Ford"),
    "Mahaveer Celesse":        ("Income", "Sales Accounts", "Mahaveer Celesse",  "Mahaveer Celese"),
    "Manyata":                 ("Income", "Sales Accounts", "Manyata",           "Manyata"),
    "Mysore":                  ("Income", "Sales Accounts", "Mysore",            "Mysore"),
    "Mysore Firenza":          ("Income", "Sales Accounts", "Mysore Firenza",    "Mysore Frenza"),
    "Prestige Waterford":      ("Income", "Sales Accounts", "Prestige Waterford","Prestige"),
    "Viman Nagar":             ("Income", "Sales Accounts", "Viman Nagar",       "Viman Nagar"),
    "JPN 202 Sales A/C":       ("Income", "Sales Accounts", "JPN 202",           "JPN 202"),
    "JPN Hotel-201 Sales A/c": ("Income", "Sales Accounts", "JPN Hotel",         "JPN-Hotel"),

    # Direct Incomes
    "Amazon Pay":  ("Income", "Direct Incomes", "Amazon Pay",  None),
    "Host Fees":   ("Income", "Direct Incomes", "Host Fees",   None),

    # Indirect Incomes
    "Discount- Offers-Gift Cards":  ("Income", "Indirect Incomes", "Discount- Offers-Gift Cards", None),
    "Interest on Income Tax Refun": ("Income", "Indirect Incomes", "Interest on Income Tax Refun", None),
    "Int. on FD":                   ("Income", "Indirect Incomes", "Int. on FD",                  None),
    "Other Income":                 ("Income", "Indirect Incomes", "Other Income",                 None),
    "Deffered Income":              ("Income", "Indirect Incomes", "Deffered Income",              None),

    # Direct Expenses (property operating costs)
    "Electiricty":     ("Direct Expenses", "Direct Expenses", "Electricity",    None),
    "RENT":            ("Direct Expenses", "Direct Expenses", "RENT",           None),
    "Brokerage":       ("Direct Expenses", "Direct Expenses", "Brokerage",      None),
    "Consumables":     ("Direct Expenses", "Direct Expenses", "Consumables",    None),
    "Household Items": ("Direct Expenses", "Direct Expenses", "Household Items",None),
    "Maintenance":     ("Direct Expenses", "Direct Expenses", "Maintenance",    None),
    "Pillow/Cover":    ("Direct Expenses", "Direct Expenses", "Pillow/Cover",   None),
    "Repair":          ("Direct Expenses", "Direct Expenses", "Repair",         None),

    # Indirect Expenses (overhead / P&L Account)
    "Bank Charges":                     ("Expenses", "Indirect Expenses", "Bank Charges",                    None),
    "Conveyance / Travelling Expenses": ("Expenses", "Indirect Expenses", "Conveyance / Travelling Expenses", None),
    "Depreciation":                     ("Expenses", "Indirect Expenses", "Depreciation",                    None),
    "Employee Medical Insurance":       ("Expenses", "Indirect Expenses", "Employee Medical Insurance",       None),
    "Income Tax Expense":               ("Expenses", "Indirect Expenses", "Income Tax Expense",               None),
    "Ineligible GST":                   ("Expenses", "Indirect Expenses", "Ineligible GST",                  None),
    "Interest Paid":                    ("Expenses", "Indirect Expenses", "Interest Paid",                   None),
    "Int on Tax":                       ("Expenses", "Indirect Expenses", "Int on Tax",                      None),
    "Nasir Ahmed":                      ("Expenses", "Indirect Expenses", "Nasir Ahmed",                     None),
    "Office Admin":                     ("Expenses", "Indirect Expenses", "Office Admin",                    None),
    "Professional Fees":                ("Expenses", "Indirect Expenses", "Professional Fees",               None),
    "Rates and Taxes":                  ("Expenses", "Indirect Expenses", "Rates and Taxes",                 None),
    "Rent Expenses":                    ("Expenses", "Indirect Expenses", "Rent Expenses",                   None),
    "Round Off":                        ("Expenses", "Indirect Expenses", "Round Off",                       None),
    "Salary A/c":                       ("Expenses", "Indirect Expenses", "Salary A/c",                     None),
    "Write Off":                        ("Expenses", "Indirect Expenses", "Write Off",                       None),

    # Balance Sheet — Equity & Liabilities
    "Loans (Liability)":        ("Equity & Liabilities", "Loans (Liability)",   "Total Loans",         None),
    "Raiyan Loan A/c":          ("Equity & Liabilities", "Loans (Liability)",   "Raiyan Loan",         None),
    "Parvez Loan":              ("Equity & Liabilities", "Loans (Liability)",   "Parvez Loan",         None),
    "Rumsha Zuha Loan":         ("Equity & Liabilities", "Loans (Liability)",   "Rumsha Zuha Loan",    None),
    "Ukhail Loan A/c":          ("Equity & Liabilities", "Loans (Liability)",   "Ukhail Loan",         None),
    "Arbaaz Loan A/c":          ("Equity & Liabilities", "Loans (Liability)",   "Arbaaz Loan",         None),
    "Rent Payable":             ("Equity & Liabilities", "Current Liabilities", "Rent Payable",        None),
    "Current Liabilities":      ("Equity & Liabilities", "Current Liabilities", "Current Liabilities", None),
    "Profit & Loss A/c":        ("Equity & Liabilities", "Capital Account",     "Retained Earnings",   None),

    # Balance Sheet — Assets
    "Security Deposit":          ("Assets", "Current Assets", "Security Deposits",        None),
    "Home Appliance":            ("Assets", "Fixed Assets",   "Home Appliances",           None),
    "HDFC Fixed Deposit":        ("Assets", "Current Assets", "Fixed Deposits",            None),
    "Lease Hold Improvement":    ("Assets", "Fixed Assets",   "Leasehold Improvements",    None),
    "Interior & Civil Work":     ("Assets", "Fixed Assets",   "Interior & Civil Works",    None),
    "Current Assets":            ("Assets", "Current Assets", "Current Assets Total",      None),
    "Loans & Advances (Asset)":  ("Assets", "Current Assets", "Loans & Advances",          None),
}


def seed_mappings(apps, schema_editor):
    """
    Forward migration: upsert all known-correct ledger mappings.
    Uses update_or_create so it is safe to re-apply (idempotent).
    """
    LedgerMapping = apps.get_model("mis_engine", "LedgerMapping")

    # 1. Apply Excluded rows
    for name in EXCLUDED_NAMES:
        LedgerMapping.objects.update_or_create(
            tally_ledger_name=name,
            defaults={
                "report_section": "Excluded",
                "report_group":   "Excluded",
                "line_item":      name,
                "cost_center":    None,
            },
        )

    # 2. Apply explicit mappings
    for name, (section, group, line_item, cc) in EXPLICIT_MAPPINGS.items():
        LedgerMapping.objects.update_or_create(
            tally_ledger_name=name,
            defaults={
                "report_section": section,
                "report_group":   group,
                "line_item":      line_item,
                "cost_center":    cc,
            },
        )


def unseed_mappings(apps, schema_editor):
    """
    Reverse migration: remove only the rows this migration created.
    Rows that existed before (from sync_tally) are left untouched.
    """
    LedgerMapping = apps.get_model("mis_engine", "LedgerMapping")
    all_names = set(EXCLUDED_NAMES) | set(EXPLICIT_MAPPINGS.keys())
    LedgerMapping.objects.filter(tally_ledger_name__in=all_names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("mis_engine", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_mappings, reverse_code=unseed_mappings),
    ]
