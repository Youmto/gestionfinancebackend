"""
URL patterns for accounts app
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # Email verification
    path('verify-email/<str:token>/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification/', views.ResendVerificationView.as_view(), name='resend-verification'),
    
    # Password reset
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    
    # User profile
    path('me/', views.UserProfileView.as_view(), name='profile'),
    path('me/password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('me/preferences/', views.NotificationPreferencesView.as_view(), name='preferences'),
]