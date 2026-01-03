"""
URL patterns for finances app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'finances'

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')

urlpatterns = [
    # Dashboard and statistics
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('summary/', views.MonthlySummaryView.as_view(), name='summary'),
    path('charts/', views.ChartDataView.as_view(), name='charts'),
    path('init-categories/', views.InitCategoriesView.as_view(), name='init-categories'),
    
    # Expense splits
    path('splits/<uuid:pk>/', views.ExpenseSplitUpdateView.as_view(), name='split-detail'),
    
    # Router URLs
    path('', include(router.urls)),
]