from django.urls import path
from . import views

urlpatterns = [
    path('reports/all/',          views.get_all_reports,  name='get_all_reports'),
    path('reports/pnl/',          views.get_pnl,          name='get_pnl'),
    path('reports/balance-sheet/',views.get_balance_sheet,name='get_balance_sheet'),
    path('reports/matrix/',       views.get_matrix,       name='get_matrix'),
    path('reports/unit-wise/',    views.get_unit_wise,    name='get_unit_wise'),
    path('reports/cashflow/',     views.get_cash_flow,    name='get_cash_flow'),
    path('reports/download/',     views.download_report,  name='download_report'),
    path('reports/debug-tb/',     views.debug_tb,         name='debug_tb'),
]
