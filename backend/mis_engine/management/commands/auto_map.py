"""
auto_map.py  —  Django management command
==========================================
Automatically categorizes ledgers in LedgerMapping using two phases:

Phase 1 — apply_correct_mappings
    Idempotently applies the known-correct mappings for this company.
    Safe to re-run at any time. Will never overwrite a mapping that
    was manually set by the accountant to a non-Unmapped value,
    UNLESS --force is passed.

    Covers:
    • Sales Accounts  (building-level Cr ledgers — the Excel columns)
    • Direct Incomes  (Amazon Pay, Host Fees)
    • Indirect Incomes (FD interest, gift card discounts, other income)
    • Direct Expenses  (RENT, Electricity, Consumables, …)
    • Indirect Expenses (Salary, Professional Fees, Ineligible GST, …)
    • Excluded ledgers (Tally parent group totals + per-unit children
                        that would double-count the building totals)
    • Balance Sheet   (loans, deposits, fixed assets, …)

Phase 2 — heuristic fallback
    For any ledger that is STILL Unmapped after Phase 1, apply keyword
    heuristics. This catches new ledgers added to Tally in the future.
    The heuristics now produce specific line items instead of the old
    catch-all "Operating Expenses".

Usage
-----
    python manage.py auto_map            # safe — skips already-mapped
    python manage.py auto_map --force    # re-applies Phase 1 to every ledger
    python manage.py auto_map --phase1   # Phase 1 only (no heuristics)
"""

from django.core.management.base import BaseCommand
from mis_engine.models import LedgerMapping


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1  —  KNOWN-CORRECT EXPLICIT MAPPINGS
# These are derived from the actual Excel MIS report and the live Tally data.
# Format: "Tally ledger name": (section, group, line_item, cost_center_or_None)
# ─────────────────────────────────────────────────────────────────────────────

# Ledgers that are Tally parent-group aggregates OR per-unit children of a
# higher-level ledger we are already using. Including them would double-count.
EXCLUDED = {
    # Tally top-level group summary ledgers (their values = sum of children)
    "Sales Accounts",
    "Direct Expenses",
    "Indirect Expenses",
    "Income",
    "Expenses",
    # Balance Sheet parent group totals (children are mapped individually below)
    "Loans (Liability)",        # parent of Raiyan/Parvez/Rumsha/Ukhail/Arbaaz loans
    "Current Liabilities",      # parent of Landlord Payables + Rent Payable
    "Current Assets",           # parent of Bank/Security/FD/Loans&Advances
    "Loans & Advances (Asset)", # parent of individual advance ledgers
    # Children of Direct Expense parent ledgers
    "Mattress/Pillow/Cover",   # child of Pillow/Cover
    # Per-unit electricity bills — children of "Electiricty" parent
    "EB - COLES PARK", "EB - EAST END ENCLAVE", "EB - ECity",
    "EB - Hebbal", "EB - KALYAN NAGAR", "EB - KASTURI NAGAR / SRK / CMR",
    "EB - KORAMANGALA", "EB - KORAMANGALA-2", "EB - MYSORE",
    "EB - MYSORE FIRENZA", "EB - Manyata", "EB - Viman Nagar",
    "EB JPN", "EB Langford", "EB-Hennur", "EB-JPN Hotel",
    "EB Prestige Waterford 11013", "EB Prestige Waterford 12194",
    # Per-property rent ledgers — children of "RENT" parent
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
    # Parent income group totals
    "Direct Incomes", "Indirect Incomes",
}

# Building-level Sales ledgers (Level 2 in Tally hierarchy).
# These are what the Excel P&L shows as property columns on the Cr side.
# cost_center maps to the matrix column name.
SALES_ACCOUNTS = {
    "Coles Park":              ("Income", "Sales Accounts", "Coles Park",        "Coles Park"),
    "East End Enclave":        ("Income", "Sales Accounts", "East End Enclave",   "EEE"),
    "El Dorado":               ("Income", "Sales Accounts", "El Dorado",          None),
    "Electronic City":         ("Income", "Sales Accounts", "Electronic City",    "E-City"),
    "Hebbal":                  ("Income", "Sales Accounts", "Hebbal",             "Hebbal"),
    "Hennur":                  ("Income", "Sales Accounts", "Hennur",             "Hennur"),
    "Kalyan Nagar":            ("Income", "Sales Accounts", "Kalyan Nagar",       "Kalyan Nagar"),
    "Kasturi Nagar":           ("Income", "Sales Accounts", "Kasturi Nagar",      "CMR"),
    # NOTE: In Tally, "Koramangala" ledger = the BIG building (Kora 2 units, Excel "Kora-2" column)
    #        "Koramangala-1" ledger = the SMALL location (Kormangala units, Excel "Koramangala" column)
    "Koramangala":             ("Income", "Sales Accounts", "Koramangala",        "Kora-2"),
    "Koramangala-1":           ("Income", "Sales Accounts", "Koramangala-1",      "Koramangala"),
    "Lang Ford":               ("Income", "Sales Accounts", "Lang Ford",          "Lang Ford"),
    "Mahaveer Celesse":        ("Income", "Sales Accounts", "Mahaveer Celesse",   "Mahaveer Celese"),
    "Manyata":                 ("Income", "Sales Accounts", "Manyata",            "Manyata"),
    "Mysore":                  ("Income", "Sales Accounts", "Mysore",             "Mysore"),
    "Mysore Firenza":          ("Income", "Sales Accounts", "Mysore Firenza",     "Mysore Frenza"),
    "Prestige Waterford":      ("Income", "Sales Accounts", "Prestige Waterford", "Prestige"),
    "Viman Nagar":             ("Income", "Sales Accounts", "Viman Nagar",        "Viman Nagar"),
    "JPN 202 Sales A/C":       ("Income", "Sales Accounts", "JPN 202",            "JPN 202"),
    "JPN Hotel-201 Sales A/c": ("Income", "Sales Accounts", "JPN Hotel",          "JPN-Hotel"),
}

# Per-unit sales ledgers are children of the building-level ledgers above.
# They must be excluded so we don't double-count.
# These are identified by the pattern: contain "Sales A" and belong to a unit prefix.
UNIT_SALES_PREFIXES = (
    "CMR ", "CP ", "Cp ", "E-CITY ", "ED J", "EEE ", "HB ", "HN ",
    "KN ", "Kora ", "Kora 2", "Kormangala", "Lang Ford 1F", "Lang Ford 2F",
    "Lang Ford 3F", "MC ", "MF ", "MN ", "Mysore 1", "Mysore 2", "Mysore 3",
    "Prestige Waterford 1", "VN ",
)

DIRECT_INCOMES = {
    "Amazon Pay":  ("Income", "Direct Incomes", "Amazon Pay",  None),
    "Host Fees":   ("Income", "Direct Incomes", "Host Fees",   None),
}

INDIRECT_INCOMES = {
    "Discount- Offers-Gift Cards":  ("Income", "Indirect Incomes", "Discount- Offers-Gift Cards", None),
    "Interest on Income Tax Refun": ("Income", "Indirect Incomes", "Interest on Income Tax Refun", None),
    "Int. on FD":                   ("Income", "Indirect Incomes", "Int. on FD",                  None),
    "Other Income":                 ("Income", "Indirect Incomes", "Other Income",                 None),
    "Deffered Income":              ("Income", "Indirect Incomes", "Deffered Income",              None),
}

# Direct Expenses: operating costs directly tied to running the properties.
# Each maps to its own line item so the Dr side of the Trading Account matches Excel.
DIRECT_EXPENSES = {
    "Electiricty":          ("Direct Expenses", "Direct Expenses", "Electricity",                       None),  # Tally typo kept
    "RENT":                 ("Direct Expenses", "Direct Expenses", "Rent",                               None),
    "Salary A/c":           ("Direct Expenses", "Direct Expenses", "Salary",                            None),
    "Brokerage":            ("Direct Expenses", "Direct Expenses", "Brokerage",                         None),
    "Consumables":          ("Direct Expenses", "Direct Expenses", "Consumables",                       None),
    "Household Items":      ("Direct Expenses", "Direct Expenses", "House Hold Items",                  None),
    "Maintenance":          ("Direct Expenses", "Direct Expenses", "Maintenance",                       None),
    "Pillow/Cover":         ("Direct Expenses", "Direct Expenses", "Pillow Covers/Bed Sheets/Clothing",  None),
    "Repair":               ("Direct Expenses", "Direct Expenses", "Repairs",                           None),
    "Repairs & Maintenance":("Direct Expenses", "Direct Expenses", "Repairs",                           None),
}

# Indirect Expenses: overhead costs in the P&L Account section.
INDIRECT_EXPENSES = {
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
    "Write Off":                        ("Expenses", "Indirect Expenses", "Write Off",                       None),
}

# Balance Sheet ledgers
BALANCE_SHEET = {
    # Landlord payables — individual property owner accounts (Cr = we owe them rent)
    "AYAAN MOHAMMED U/G AMEENA FIRDOZE":              ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Aiman Nawaz":                                    ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Aksam Nawaz":                                    ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Ameena Firdoze":                                 ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Badruddin A Clipwala Reimburement":              ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Battu Madhavi":                                  ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Bhawna Sinha":                                   ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Brigade Eldorado Land Lord":                     ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "FARHANA FATHIMA":                                ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Farooq Ismail":                                  ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "JPN Landlord 1":                                 ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "JPN Landlord 2":                                 ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Mirza Nasrullah Baig":                           ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Mohammed Sadiq":                                 ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Mr. Dawood Shariff":                             ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Mr. H Jeelani Basha":                            ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Mr. Ishrath Abbas":                              ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Mr. K. Mohammed Sadiq & Ayshathul Fawzia Sadiq": ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Mr. Mohammed Ibrahim":                           ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Mr. harshitha G V":                              ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Mr.Khaja mohinuddin":                            ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Mr.Vishnu Prasad":                               ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Mrs.Shameem":                                    ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "NAVEEDA PERVEEN H S":                            ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Neeraja":                                        ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "PROTIUM FINANCE LIMITED":                        ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "SAFA ISMAIL U/G AMEENA FIRDOZE":                ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "SGLAM HOMES LLP":                               ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "SRI. C.M. Radhakrishna":                        ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    "Viman Nagar Land Lord":                          ("Equity & Liabilities", "Current Liabilities", "Landlord Payables", None),
    # Bank accounts (Dr = asset)
    "HDFC - Unreal":                                  ("Assets", "Current Assets", "Bank Accounts",       None),
    "HDFC-New":                                       ("Assets", "Current Assets", "Bank Accounts",       None),
    "Kotak - Unreal":                                 ("Assets", "Current Assets", "Bank Accounts",       None),
    "Arbaaz Reimburesement A/c":                      ("Assets", "Current Assets", "Loans & Advances",    None),
    "Security Depoosit -Mysore Firenza":              ("Assets", "Current Assets", "Security Deposits",   None),
    "Valley View Assagao":                            ("Assets", "Current Assets", "Security Deposits",   None),
    # Loans / liabilities
    "Raiyan Loan A/c":             ("Equity & Liabilities", "Loans (Liability)",    "Raiyan Loan",          None),
    "Parvez Loan":                 ("Equity & Liabilities", "Loans (Liability)",    "Parvez Loan",          None),
    "Rumsha Zuha Loan":            ("Equity & Liabilities", "Loans (Liability)",    "Rumsha Zuha Loan",     None),
    "Ukhail Loan A/c":             ("Equity & Liabilities", "Loans (Liability)",    "Ukhail Loan",          None),
    "Arbaaz Loan A/c":             ("Equity & Liabilities", "Loans (Liability)",    "Arbaaz Loan",          None),
    "Rent Payable":                ("Equity & Liabilities", "Current Liabilities",  "Rent Payable",         None),
    "Profit & Loss A/c":           ("Equity & Liabilities", "Capital Account",      "Retained Earnings",    None),
    # Assets
    "Security Deposit":            ("Assets", "Current Assets", "Security Deposits",         None),
    "Home Appliance":              ("Assets", "Fixed Assets",   "Home Appliances",            None),
    "HDFC Fixed Deposit":          ("Assets", "Current Assets", "Fixed Deposits",             None),
    "Lease Hold Improvement":      ("Assets", "Fixed Assets",   "Leasehold Improvements",     None),
    "Interior & Civil Work":       ("Assets", "Fixed Assets",   "Interior & Civil Works",     None),
}

# All known explicit mappings combined (except excluded — handled separately)
ALL_EXPLICIT = {
    **SALES_ACCOUNTS,
    **DIRECT_INCOMES,
    **INDIRECT_INCOMES,
    **DIRECT_EXPENSES,
    **INDIRECT_EXPENSES,
    **BALANCE_SHEET,
}


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2  —  HEURISTIC FALLBACK (for new/unknown ledgers)
# Returns (section, group, line_item) or None if no match found.
# ─────────────────────────────────────────────────────────────────────────────

def heuristic_map(ledger_name: str):
    n = ledger_name.lower()

    # Balance Sheet — Liabilities
    if 'capital' in n:
        return 'Equity & Liabilities', 'Capital Account', 'Capital'
    if 'loan' in n and 'advance' not in n:
        return 'Equity & Liabilities', 'Loans (Liability)', 'Other Loans'
    if any(x in n for x in ['gst', 'tds', 'tax payable', 'duty']):
        return 'Equity & Liabilities', 'Current Liabilities', 'Duties & Taxes'
    if 'payable' in n or 'creditor' in n:
        return 'Equity & Liabilities', 'Current Liabilities', 'Sundry Creditors'

    # Balance Sheet — Assets
    if 'bank' in n:
        return 'Assets', 'Current Assets', 'Bank Accounts'
    if 'cash' in n:
        return 'Assets', 'Current Assets', 'Cash-in-hand'
    if 'receivable' in n or 'debtor' in n:
        return 'Assets', 'Current Assets', 'Sundry Debtors'
    if any(x in n for x in ['security deposit', 'advance', 'reimburs']):
        return 'Assets', 'Current Assets', 'Loans & Advances (Asset)'
    if any(x in n for x in ['fixed asset', 'computer', 'furniture', 'equipment', 'appliance', 'capex']):
        return 'Assets', 'Fixed Assets', 'Fixed Assets'

    # Income — Sales
    if 'sale' in n or 'revenue' in n:
        return 'Income', 'Sales Accounts', ledger_name  # use actual name as line item

    # Income — Indirect
    if 'income' in n or 'interest received' in n or 'discount received' in n:
        return 'Income', 'Indirect Incomes', 'Other Income'

    # Direct Expenses (property-level operating costs)
    if any(x in n for x in ['electricity', 'eb ', 'consumable', 'laundry',
                             'housekeeping', 'cleaning', 'cable', 'water charge',
                             'pillow', 'household', 'brokerage']):
        return 'Direct Expenses', 'Direct Expenses', ledger_name

    if 'rent' in n and 'expense' not in n:
        return 'Direct Expenses', 'Direct Expenses', 'RENT'

    # Direct Expenses — unit-level operating costs (heuristic for new/unknown variants)
    if any(x in n for x in ['salary', 'wage', 'stipend']):
        return 'Direct Expenses', 'Direct Expenses', 'Salary'
    if any(x in n for x in ['repair', 'maintenance', 'maintain']):
        return 'Direct Expenses', 'Direct Expenses', 'Repairs'

    # Indirect Expenses — specific line items instead of old catch-all
    if 'professional fee' in n or 'audit fee' in n or 'legal fee' in n:
        return 'Expenses', 'Indirect Expenses', 'Professional Fees'
    if 'bank charge' in n or 'bank fee' in n:
        return 'Expenses', 'Indirect Expenses', 'Bank Charges'
    if 'depreciation' in n:
        return 'Expenses', 'Indirect Expenses', 'Depreciation'
    if 'conveyance' in n or 'travel' in n:
        return 'Expenses', 'Indirect Expenses', 'Conveyance / Travelling Expenses'
    if 'ineligible gst' in n or 'gst expense' in n:
        return 'Expenses', 'Indirect Expenses', 'Ineligible GST'
    if 'interest paid' in n or 'interest on loan' in n:
        return 'Expenses', 'Indirect Expenses', 'Interest Paid'
    if 'office' in n and 'admin' in n:
        return 'Expenses', 'Indirect Expenses', 'Office Admin'
    if any(x in n for x in ['rate', 'tax', 'stamp duty']):
        return 'Expenses', 'Indirect Expenses', 'Rates and Taxes'
    if any(x in n for x in ['fee', 'charge', 'exp']):
        return 'Expenses', 'Indirect Expenses', ledger_name  # keep original name

    # Landlord / property-owner accounts — Cr balances we owe as rent payable
    if any(x in n for x in ['landlord', 'land lord', 'property owner']):
        return 'Equity & Liabilities', 'Current Liabilities', 'Landlord Payables'

    return None  # genuinely unknown — stays Unmapped


def _is_unit_sale(name: str) -> bool:
    """Return True if this is a per-unit sales ledger (child of a building total)."""
    up = name.upper()
    return ('SALES A' in up or 'SALES A/' in up) and any(
        up.startswith(p.upper()) for p in UNIT_SALES_PREFIXES
    )


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND
# ─────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = (
        'Categorizes ledgers into P&L / Balance Sheet sections. '
        'Phase 1 applies known-correct explicit mappings. '
        'Phase 2 applies heuristics to anything still Unmapped.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-apply Phase 1 explicit mappings even if already mapped.',
        )
        parser.add_argument(
            '--phase1',
            action='store_true',
            help='Run Phase 1 only (skip heuristic fallback).',
        )

    def handle(self, *args, **options):
        force    = options['force']
        phase1_only = options['phase1']

        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n=== auto_map: Phase 1 — Explicit Mappings ==='
        ))
        p1_excluded = p1_mapped = 0

        for ledger in LedgerMapping.objects.all():
            name = ledger.tally_ledger_name

            # ── Skip already-mapped unless --force ──
            already_mapped = ledger.report_section not in ('Unmapped', 'Excluded')
            if already_mapped and not force:
                continue

            # ── Excluded (double-count prevention) ──
            if name in EXCLUDED or _is_unit_sale(name):
                ledger.report_section = 'Excluded'
                ledger.report_group   = 'Excluded'
                ledger.line_item      = name
                ledger.save()
                p1_excluded += 1
                self.stdout.write(f'  [EXCLUDED] {name}')
                continue

            # ── Explicit known mapping ──
            if name in ALL_EXPLICIT:
                sec, grp, line, cc = ALL_EXPLICIT[name]
                ledger.report_section = sec
                ledger.report_group   = grp
                ledger.line_item      = line
                if cc is not None:
                    ledger.cost_center = cc
                ledger.save()
                p1_mapped += 1
                self.stdout.write(f'  [OK] {name} ->{sec} / {grp} / {line}')

        self.stdout.write(self.style.SUCCESS(
            f'\nPhase 1 done: {p1_mapped} explicit mappings applied, '
            f'{p1_excluded} ledgers excluded (double-count prevention).'
        ))

        if phase1_only:
            return

        # ─────────────────────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n=== auto_map: Phase 2 — Heuristic Fallback ==='
        ))

        still_unmapped = LedgerMapping.objects.filter(report_section='Unmapped')
        total_unmapped = still_unmapped.count()
        self.stdout.write(f'  {total_unmapped} ledgers still Unmapped after Phase 1.')

        p2_mapped = p2_skipped = 0

        for ledger in still_unmapped:
            result = heuristic_map(ledger.tally_ledger_name)
            if result:
                sec, grp, line = result
                ledger.report_section = sec
                ledger.report_group   = grp
                ledger.line_item      = line
                ledger.save()
                p2_mapped += 1
                self.stdout.write(
                    f'  [HEURISTIC] {ledger.tally_ledger_name} ->{sec} / {grp} / {line}'
                )
            else:
                p2_skipped += 1
                self.stdout.write(
                    self.style.WARNING(f'  [STILL UNMAPPED] {ledger.tally_ledger_name}')
                )

        # ── Phase 2b: Cost-center assignment for sales ledgers ──
        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n=== auto_map: Phase 2b — Sales Cost-Center Assignment ==='
        ))
        cc_count = 0
        for ledger in LedgerMapping.objects.filter(
            report_group='Sales Accounts', cost_center=None
        ):
            up = ledger.tally_ledger_name.upper()
            cc = None
            if up.startswith('KORA 2') or up.startswith('KORA2'):
                # "Kora 2 xxx Sales A/c" = BIG Koramangala building = Excel "Kora-2" column
                cc = 'Kora-2'
            elif up.startswith('KORA') or 'KORMANGALA' in up:
                # "Kora-101 etc." and "Kormangala x" = SMALL location = Excel "Koramangala" column
                cc = 'Koramangala'
            elif up.startswith('E-CITY') or up.startswith('ECITY'):
                cc = 'E-City'
            elif up.startswith('EEE'):
                cc = 'EEE'
            elif up.startswith('HB '):
                cc = 'Hebbal'
            elif up.startswith('HN '):
                cc = 'Hennur'
            elif 'JPN' in up and 'HOTEL' in up:
                cc = 'JPN-Hotel'
            elif up.startswith('JPN'):
                cc = 'JPN 202'
            elif up.startswith('KN '):
                cc = 'Kalyan Nagar'
            elif up.startswith('LANG FORD') or up.startswith('LF '):
                cc = 'Lang Ford'
            elif up.startswith('MC '):
                cc = 'Mahaveer Celese'
            elif up.startswith('MF'):
                cc = 'Mysore Frenza'
            elif up.startswith('MN'):
                cc = 'Manyata'
            elif up.startswith('MYSORE'):
                cc = 'Mysore'
            elif up.startswith('PRESTIGE'):
                cc = 'Prestige'
            elif up.startswith('ED ') or up.startswith('ED\t') or 'EL DORADO' in up or 'BRIGADE' in up:
                cc = 'Brigade'
            elif up.startswith('VN '):
                cc = 'Viman Nagar'
            elif up.startswith('CP ') or up.startswith('CP\t'):
                cc = 'Coles Park'
            elif up.startswith('CMR'):
                cc = 'CMR'
            elif 'KASTURI' in up or 'SRK' in up:
                cc = 'CMR'

            if cc:
                ledger.cost_center = cc
                ledger.save()
                cc_count += 1
                self.stdout.write(f'  [CC] {ledger.tally_ledger_name} ->{cc}')

        self.stdout.write(self.style.SUCCESS(
            f'\nPhase 2 done: {p2_mapped} heuristic mappings, '
            f'{p2_skipped} still unmapped, {cc_count} cost-centers assigned.'
        ))

        # ── Final summary ──
        from django.db.models import Count
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Final Mapping Summary ==='))
        for row in LedgerMapping.objects.values('report_section').annotate(
            n=Count('id')
        ).order_by('-n'):
            self.stdout.write(f"  {row['report_section']:<35} {row['n']:>4} ledgers")
