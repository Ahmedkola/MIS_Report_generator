from django.db import models

class LedgerMapping(models.Model):
    """
    Stores the mapping of raw Tally ledgers to their exact MIS category.
    This database table drives the dynamic assembly of the final JSON reports.
    """
    tally_ledger_name = models.CharField(
        max_length=255, 
        unique=True,
        help_text="Exact ledger name as it appears in Tally XML"
    )
    
    # -------------------------------------------------------------
    # Standard Report Categorization (Balance Sheet / P&L)
    # -------------------------------------------------------------
    report_section = models.CharField(
        max_length=100,
        help_text="e.g., 'Assets', 'Equity & Liabilities', 'Income', 'Expenses'"
    )
    report_group = models.CharField(
        max_length=150,
        help_text="e.g., 'Loans (Liability)', 'Indirect Expenses'"
    )
    line_item = models.CharField(
        max_length=150,
        help_text="e.g., 'Salary A/c', 'Other Loans'"
    )
    
    # -------------------------------------------------------------
    # Matrix Report Categorization (Building Wise Data)
    # -------------------------------------------------------------
    cost_center = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional. The logical cost center group for Matrix reporting (e.g., 'BTM 12th Main')"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['report_section', 'report_group', 'tally_ledger_name']

    def __str__(self):
        return f"{self.tally_ledger_name} -> {self.report_group} / {self.line_item}"


class Building(models.Model):
    """One physical building / property group."""
    display_name = models.CharField(max_length=100, unique=True,
        help_text="UI label used as matrix column header, e.g. 'Kalyan Nagar'")
    general_cc   = models.CharField(max_length=150, blank=True, null=True,
        help_text="Exact Tally CC name for this building's General overhead CC. Null = none.")
    rent_ledger  = models.CharField(max_length=200, blank=True, null=True,
        help_text="Exact Tally ledger name for rent. Null = fall back to per-unit CC breakup.")
    column_order = models.PositiveSmallIntegerField(default=0,
        help_text="Left-to-right order in the matrix report.")
    is_active    = models.BooleanField(default=True)

    class Meta:
        ordering = ['column_order', 'display_name']

    def __str__(self):
        return self.display_name


class CostCenter(models.Model):
    """One unit/room within a building, or a standalone single-unit property."""
    building     = models.ForeignKey(
        Building, on_delete=models.CASCADE, related_name='cost_centers',
        null=True, blank=True,
        help_text="Parent building. Null only for the General Office virtual column.")
    display_name = models.CharField(max_length=100,
        help_text="UI column header, e.g. 'KN 101'")
    tally_cc     = models.CharField(max_length=150, blank=True, null=True,
        help_text="Exact Tally cost centre name. Null = General Office virtual column.")
    column_order = models.PositiveSmallIntegerField(default=0,
        help_text="Order within the building (left-to-right in unit-wise table).")
    is_excluded_from_split = models.BooleanField(default=False,
        help_text="True for Penthouse and General virtual columns — skip in salary/rent splits.")
    is_active    = models.BooleanField(default=True)

    class Meta:
        ordering = ['building__column_order', 'column_order', 'display_name']
        unique_together = [('building', 'display_name')]

    def __str__(self):
        bldg = self.building.display_name if self.building else "—"
        return f"{bldg} / {self.display_name}"
