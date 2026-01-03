"""
URL patterns for groups app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'groups'

router = DefaultRouter()
router.register(r'', views.GroupViewSet, basename='group')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Group invitations
    path('<uuid:group_id>/invite/', views.InviteToGroupView.as_view(), name='invite'),
    path('invitations/<str:token>/', views.AcceptInvitationView.as_view(), name='accept-invitation'),
    
    # Group members
    path('<uuid:group_id>/members/', views.GroupMembersView.as_view(), name='members'),
    path('<uuid:group_id>/members/<uuid:user_id>/', views.GroupMemberDetailView.as_view(), name='member-detail'),
    
    # Group actions
    path('<uuid:group_id>/leave/', views.LeaveGroupView.as_view(), name='leave'),
    path('<uuid:group_id>/balance/', views.GroupBalanceView.as_view(), name='balance'),
    path('<uuid:group_id>/transactions/', views.GroupTransactionsView.as_view(), name='transactions'),
]