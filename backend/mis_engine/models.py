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
