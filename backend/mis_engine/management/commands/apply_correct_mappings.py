"""
apply_correct_mappings.py — Django management command
======================================================
Idempotent replacement for the one-off `fix_mappings.py` script.

Applies the known-correct ledger mappings for this company's Tally chart of
accounts. Safe to run multiple times — uses update_or_create internally.

This command is also the "break-glass" repair tool: if auto_map or a manual
edit leaves the DB in a bad state, running this will restore the correct
mappings without touching ledgers that are not in its explicit list.

Usage:
    python manage.py apply_correct_mappings
    python manage.py apply_correct_mappings --dry-run   # preview only
"""

from django.core.management.base import BaseCommand
from mis_engine.models import LedgerMapping


# ─────────────────────────────────────────────────────────────────────────────
# Source-of-truth mappings for this company.
# These match the Excel "MIS January 2025-Final.xlsx" exactly.
# ─────────────────────────────────────────────────────────────────────────────

# Parent group totals + per-unit children that would double-count
EXCLUDED_NAMES = {
    # Tally top-level group summaries
    "Sales Accounts",
    "Direct Expenses",
    "Indirect Expenses",
    "Income",
    "Expenses",
    "Direct Incomes",       # parent group — must not appear as a P&L line item
    "Indirect Incomes",     # parent group — must not appear as a P&L line item
    # Per-unit electricity bills (children of "Electiricty" parent)
    "EB - COLES PARK", "EB - EAST END ENCLAVE", "EB - ECity",
    "EB - Hebbal", "EB - KALYAN NAGAR", "EB - KASTURI NAGAR / SRK / CMR",
    "EB - KORAMANGALA", "EB - KORAMANGALA-2", "EB - MYSORE",
    "EB - MYSORE FIRENZA", "EB - Manyata", "EB - Viman Nagar",
    "EB JPN", "EB Langford", "EB-Hennur", "EB-JPN Hotel",
    "EB Prestige Waterford 11013", "EB Prestige Waterford 12194",
    # Per-property rent ledgers (children of "RENT" parent)
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

# Explicit mappings: name -> (section, group, line_item, cost_center_or_None)
EXPLICIT_MAPPINGS = {
    # ── Sales Accounts (building-level — the Excel P&L columns) ─────────────
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

    # ── Direct Incomes ───────────────────────────────────────────────────────
    "Amazon Pay":  ("Income", "Direct Incomes", "Amazon Pay",  None),
    "Host Fees":   ("Income", "Direct Incomes", "Host Fees",   None),

    # ── Indirect Incomes ─────────────────────────────────────────────────────
    "Discount- Offers-Gift Cards":  ("Income", "Indirect Incomes", "Discount- Offers-Gift Cards", None),
    "Interest on Income Tax Refun": ("Income", "Indirect Incomes", "Interest on Income Tax Refun", None),
    "Int. on FD":                   ("Income", "Indirect Incomes", "Int. on FD",                  None),
    "Other Income":                 ("Income", "Indirect Incomes", "Other Income",                 None),
    "Deffered Income":              ("Income", "Indirect Incomes", "Deffered Income",              None),

    # ── Direct Expenses (property operating costs) ───────────────────────────
    "Electiricty":          ("Direct Expenses", "Direct Expenses", "Electricity",                      None),
    "RENT":                 ("Direct Expenses", "Direct Expenses", "Rent",                              None),
    "Salary A/c":           ("Direct Expenses", "Direct Expenses", "Salary",                           None),
    "Brokerage":            ("Direct Expenses", "Direct Expenses", "Brokerage",                        None),
    "Consumables":          ("Direct Expenses", "Direct Expenses", "Consumables",                      None),
    "Household Items":      ("Direct Expenses", "Direct Expenses", "House Hold Items",                 None),
    "Maintenance":          ("Direct Expenses", "Direct Expenses", "Maintenance",                      None),
    "Pillow/Cover":         ("Direct Expenses", "Direct Expenses", "Pillow Covers/Bed Sheets/Clothing", None),
    "Repair":               ("Direct Expenses", "Direct Expenses", "Repairs",                          None),
    "Repairs & Maintenance":("Direct Expenses", "Direct Expenses", "Repairs",                          None),

    # ── Indirect Expenses (overhead / P&L Account) ───────────────────────────
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

    # ── Balance Sheet — Equity & Liabilities ─────────────────────────────────
    "Loans (Liability)":        ("Equity & Liabilities", "Loans (Liability)",   "Total Loans",         None),
    "Raiyan Loan A/c":          ("Equity & Liabilities", "Loans (Liability)",   "Raiyan Loan",         None),
    "Parvez Loan":              ("Equity & Liabilities", "Loans (Liability)",   "Parvez Loan",         None),
    "Rumsha Zuha Loan":         ("Equity & Liabilities", "Loans (Liability)",   "Rumsha Zuha Loan",    None),
    "Ukhail Loan A/c":          ("Equity & Liabilities", "Loans (Liability)",   "Ukhail Loan",         None),
    "Arbaaz Loan A/c":          ("Equity & Liabilities", "Loans (Liability)",   "Arbaaz Loan",         None),
    "Rent Payable":             ("Equity & Liabilities", "Current Liabilities", "Rent Payable",        None),
    "Current Liabilities":      ("Equity & Liabilities", "Current Liabilities", "Current Liabilities", None),
    "Profit & Loss A/c":        ("Equity & Liabilities", "Capital Account",     "Retained Earnings",   None),

    # ── Balance Sheet — Assets ───────────────────────────────────────────────
    "Security Deposit":          ("Assets", "Current Assets", "Security Deposits",       None),
    "Home Appliance":            ("Assets", "Fixed Assets",   "Home Appliances",         None),
    "HDFC Fixed Deposit":        ("Assets", "Current Assets", "Fixed Deposits",          None),
    "Lease Hold Improvement":    ("Assets", "Fixed Assets",   "Leasehold Improvements",  None),
    "Interior & Civil Work":     ("Assets", "Fixed Assets",   "Interior & Civil Works",  None),
    "Current Assets":            ("Assets", "Current Assets", "Current Assets Total",    None),
    "Loans & Advances (Asset)":  ("Assets", "Current Assets", "Loans & Advances",        None),
}


class Command(BaseCommand):
    help = (
        'Idempotent: applies the known-correct ledger mappings for this company. '
        'Replaces the one-off fix_mappings.py script. Safe to run multiple times.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be changed without writing to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] No changes will be written.\n'))

        excluded_applied = 0
        explicit_applied = 0
        created_count    = 0
        updated_count    = 0

        # ── Phase 1: Excluded (parent group aggregates + per-unit children) ──
        self.stdout.write(self.style.MIGRATE_HEADING(
            '=== Phase 1: Excluding double-count parent ledgers ==='
        ))
        for name in sorted(EXCLUDED_NAMES):
            existing = LedgerMapping.objects.filter(tally_ledger_name=name).first()
            if existing:
                if existing.report_section != 'Excluded':
                    if not dry_run:
                        existing.report_section = 'Excluded'
                        existing.report_group   = 'Excluded'
                        existing.line_item      = name
                        existing.cost_center    = None
                        existing.save()
                    self.stdout.write(f'  [FIXED → Excluded] {name}')
                    updated_count += 1
                else:
                    self.stdout.write(f'  [OK] {name} (already Excluded)')
            else:
                if not dry_run:
                    LedgerMapping.objects.create(
                        tally_ledger_name=name,
                        report_section='Excluded',
                        report_group='Excluded',
                        line_item=name,
                    )
                self.stdout.write(f'  [CREATED] {name}')
                created_count += 1
            excluded_applied += 1

        # ── Phase 2: Explicit known mappings ──────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n=== Phase 2: Applying explicit known mappings ==='
        ))
        for name, (section, group, line_item, cc) in EXPLICIT_MAPPINGS.items():
            existing = LedgerMapping.objects.filter(tally_ledger_name=name).first()
            needs_update = (
                not existing or
                existing.report_section != section or
                existing.report_group   != group or
                existing.line_item      != line_item or
                existing.cost_center    != cc
            )

            if needs_update:
                if not dry_run:
                    LedgerMapping.objects.update_or_create(
                        tally_ledger_name=name,
                        defaults={
                            'report_section': section,
                            'report_group':   group,
                            'line_item':      line_item,
                            'cost_center':    cc,
                        }
                    )
                verb = 'CREATED' if not existing else 'UPDATED'
                self.stdout.write(f'  [{verb}] {name} → {section} / {group} / {line_item}')
                if existing:
                    updated_count += 1
                else:
                    created_count += 1
            else:
                self.stdout.write(f'  [OK] {name}')
            explicit_applied += 1

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(
            f'Done{"  [DRY RUN — nothing written]" if dry_run else ""}.\n'
            f'  Excluded entries processed : {excluded_applied}\n'
            f'  Explicit mappings processed: {explicit_applied}\n'
            f'  Created : {created_count}\n'
            f'  Updated : {updated_count}\n'
            f'  Unchanged: {excluded_applied + explicit_applied - created_count - updated_count}'
        ))

        if not dry_run:
            self.stdout.write(self.style.MIGRATE_HEADING(
                '\n=== Final Mapping Summary ==='
            ))
            from django.db.models import Count
            for row in (
                LedgerMapping.objects
                .values('report_section')
                .annotate(n=Count('id'))
                .order_by('-n')
            ):
                self.stdout.write(f"  {row['report_section']:<35} {row['n']:>4} ledgers")
