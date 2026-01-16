"""
URL patterns for accounts app
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from .views_verification import (
    SendVerificationCodeView,
    VerifyCodeView,
    RegisterWithCodeView,
    ResetPasswordWithCodeView,
    ResendVerificationCodeView
)

app_name = 'accounts'

urlpatterns = [
    # Authentification existante
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profil
    path('me/', views.UserProfileView.as_view(), name='profile'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    
    # Vérification par code OTP
    path('send-code/', SendVerificationCodeView.as_view(), name='send_code'),
    path('verify-code/', VerifyCodeView.as_view(), name='verify_code'),
    path('register-with-code/', RegisterWithCodeView.as_view(), name='register_with_code'),
    path('reset-password-with-code/', ResetPasswordWithCodeView.as_view(), name='reset_password_with_code'),
    path('resend-code/', ResendVerificationCodeView.as_view(), name='resend_code'),
]