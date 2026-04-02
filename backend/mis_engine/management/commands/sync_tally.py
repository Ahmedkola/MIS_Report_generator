"""
sync_tally.py — Django management command
==========================================
Fetches all ledgers from Tally and populates the LedgerMapping table.

After syncing, automatically runs Phase 1 + Phase 2 of auto_map logic on
any newly-added Unmapped ledgers, so the database is always fully categorised
after every sync — no manual step needed.

Usage:
    python manage.py sync_tally               # sync + auto-map new ledgers
    python manage.py sync_tally --no-automap  # sync only, skip auto-mapping
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from mis_engine.models import LedgerMapping

# Add project root to path so we can import tally_api
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from tally_api import TallyAPIClient


class Command(BaseCommand):
    help = (
        'Fetches all ledgers from Tally, populates the LedgerMapping table '
        'with new entries, and auto-maps any newly added Unmapped ledgers.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-automap',
            action='store_true',
            help='Skip the Phase 1 + Phase 2 auto-mapping step after sync.',
        )

    def handle(self, *args, **kwargs):
        no_automap = kwargs['no_automap']

        self.stdout.write("Connecting to Tally on port 9000...")

        api = TallyAPIClient()
        if not api.ping():
            self.stderr.write(self.style.ERROR("Could not connect to Tally XML server."))
            return

        self.stdout.write("Extracting active ledgers from Tally Trial Balance...")
        try:
            # Fetch a wide range to guarantee we catch all active ledgers
            ledgers = api.fetch_trial_balance("20250401", "20260131")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to fetch ledgers: {e}"))
            return

        if not ledgers:
            self.stderr.write(self.style.WARNING("Tally returned 0 ledgers. Check UI active company."))
            return

        self.stdout.write(f"Found {len(ledgers)} active ledgers. Syncing to Django database...")

        added = 0
        for ledger in ledgers:
            ledger_name = ledger["ledger_name"].strip()

            # get_or_create: never duplicates, never overwrites existing mappings
            obj, created = LedgerMapping.objects.get_or_create(
                tally_ledger_name=ledger_name,
                defaults={
                    'report_section': 'Unmapped',
                    'report_group': 'Unmapped',
                    'line_item': 'Unmapped',
                }
            )
            if created:
                added += 1

        self.stdout.write(self.style.SUCCESS(
            f"Sync complete! Added {added} new ledgers. "
            f"{len(ledgers) - added} already existed."
        ))

        # ── Auto-map any newly Unmapped ledgers ─────────────────────────────
        if no_automap:
            self.stdout.write(self.style.WARNING(
                "Skipping auto-map (--no-automap flag set). "
                "Run `python manage.py auto_map` manually to categorise new ledgers."
            ))
            return

        unmapped_count = LedgerMapping.objects.filter(report_section='Unmapped').count()
        if unmapped_count == 0:
            self.stdout.write(self.style.SUCCESS("All ledgers already mapped — nothing to auto-map."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{unmapped_count} Unmapped ledger(s) found — running auto_map Phase 1 + Phase 2..."
        ))

        # Delegate to auto_map management command (Phase 1 + Phase 2, no --force
        # so it only touches Unmapped ledgers, never overwrites existing mappings)
        call_command('auto_map', verbosity=1)
