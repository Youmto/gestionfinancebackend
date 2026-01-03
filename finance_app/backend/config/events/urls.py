"""
URL patterns for events app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'events'

router = DefaultRouter()
router.register(r'', views.EventViewSet, basename='event')

urlpatterns = [
    # Custom endpoints (before router to avoid conflicts)
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('calendar/<int:year>/<int:month>/', views.MonthCalendarView.as_view(), name='month-calendar'),
    path('upcoming/', views.UpcomingEventsView.as_view(), name='upcoming'),
    path('today/', views.TodayEventsView.as_view(), name='today'),
    path('date/', views.DateEventsView.as_view(), name='date-events'),
    path('stats/', views.EventStatsView.as_view(), name='stats'),
    
    # Router URLs
    path('', include(router.urls)),
]