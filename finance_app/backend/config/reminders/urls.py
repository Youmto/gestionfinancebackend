"""
URL patterns for reminders app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'reminders'

router = DefaultRouter()
router.register(r'', views.ReminderViewSet, basename='reminder')

urlpatterns = [
    # Custom endpoints (before router to avoid conflicts)
    path('upcoming/', views.UpcomingRemindersView.as_view(), name='upcoming'),
    path('stats/', views.ReminderStatsView.as_view(), name='stats'),
    
    # Router URLs (includes CRUD + complete action)
    path('', include(router.urls)),
]