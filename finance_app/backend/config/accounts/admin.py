"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, EmailVerificationToken, PasswordResetToken, NotificationPreferences


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Configuration admin pour le modèle User personnalisé.
    """
    
    list_display = [
        'email', 'first_name', 'last_name', 
        'is_verified', 'is_active', 'is_staff', 
        'created_at'
    ]
    list_filter = [
        'is_verified', 'is_active', 'is_staff', 
        'is_superuser', 'currency'
    ]
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informations personnelles'), {
            'fields': ('first_name', 'last_name', 'avatar')
        }),
        (_('Préférences'), {
            'fields': ('currency',)
        }),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_verified', 'is_staff', 
                'is_superuser', 'groups', 'user_permissions'
            ),
        }),
        (_('Dates importantes'), {
            'fields': ('last_login', 'created_at', 'updated_at'),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name',
                'password1', 'password2', 'is_verified'
            ),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login']


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    """
    Configuration admin pour les tokens de vérification email.
    """
    
    list_display = ['user', 'token', 'is_used', 'expires_at', 'created_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'token']
    ordering = ['-created_at']
    readonly_fields = ['token', 'created_at']


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """
    Configuration admin pour les tokens de réinitialisation.
    """
    
    list_display = ['user', 'token', 'is_used', 'expires_at', 'created_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'token']
    ordering = ['-created_at']
    readonly_fields = ['token', 'created_at']


@admin.register(NotificationPreferences)
class NotificationPreferencesAdmin(admin.ModelAdmin):
    """
    Configuration admin pour les préférences de notification.
    """
    
    list_display = [
        'user', 'email_reminders', 'email_group_activity',
        'email_weekly_summary', 'push_enabled'
    ]
    list_filter = [
        'email_reminders', 'email_group_activity',
        'email_weekly_summary', 'push_enabled'
    ]
    search_fields = ['user__email']