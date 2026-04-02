from django.contrib import admin
from .models import LedgerMapping

@admin.register(LedgerMapping)
class LedgerMappingAdmin(admin.ModelAdmin):
    list_display = ('tally_ledger_name', 'report_section', 'report_group', 'line_item', 'cost_center')
    list_filter = ('report_section', 'report_group', 'cost_center')
    search_fields = ('tally_ledger_name', 'line_item')
    ordering = ('report_section', 'report_group', 'tally_ledger_name')
