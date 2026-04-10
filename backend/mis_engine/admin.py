from django.contrib import admin
from .models import LedgerMapping, Building, CostCenter


@admin.register(LedgerMapping)
class LedgerMappingAdmin(admin.ModelAdmin):
    list_display  = ('tally_ledger_name', 'report_section', 'report_group', 'line_item', 'cost_center')
    list_filter   = ('report_section', 'report_group', 'cost_center')
    search_fields = ('tally_ledger_name', 'line_item')
    ordering      = ('report_section', 'report_group', 'tally_ledger_name')


class CostCenterInline(admin.TabularInline):
    model  = CostCenter
    extra  = 0
    fields = ('display_name', 'tally_cc', 'column_order', 'is_excluded_from_split', 'is_active')


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display  = ('display_name', 'general_cc', 'rent_ledger', 'column_order', 'is_active')
    list_editable = ('column_order', 'is_active')
    search_fields = ('display_name', 'general_cc', 'rent_ledger')
    inlines       = [CostCenterInline]


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display  = ('display_name', 'building', 'tally_cc', 'column_order',
                     'is_excluded_from_split', 'is_active')
    list_editable = ('column_order', 'is_excluded_from_split', 'is_active')
    list_filter   = ('building', 'is_active', 'is_excluded_from_split')
    search_fields = ('display_name', 'tally_cc')
    ordering      = ('building__column_order', 'column_order')
