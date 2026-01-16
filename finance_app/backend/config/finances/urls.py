"""
URL patterns for finances app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    TransactionViewSet,
    DashboardView,
    MonthlySummaryView,
    ChartDataView,
    InitCategoriesView,
    ExpenseSplitUpdateView,
    ExportTransactionsView,
    ExportBudgetReportView,
    ExportMonthlyReportView,
)

app_name = 'finances'

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'transactions', TransactionViewSet, basename='transaction')

urlpatterns = [
    # Dashboard
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('summary/', MonthlySummaryView.as_view(), name='summary'),
    path('charts/', ChartDataView.as_view(), name='charts'),
    path('init-categories/', InitCategoriesView.as_view(), name='init-categories'),
    
    # Splits
    path('splits/<uuid:pk>/', ExpenseSplitUpdateView.as_view(), name='split-detail'),
    
    # Exports
    path('export/transactions/', ExportTransactionsView.as_view(), name='export-transactions'),
    path('export/budget/', ExportBudgetReportView.as_view(), name='export-budget'),
    path('export/monthly/', ExportMonthlyReportView.as_view(), name='export-monthly'),
    
    # Router
    path('', include(router.urls)),
]