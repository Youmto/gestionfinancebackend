"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    User, 
    EmailVerificationCode, 
    PasswordResetToken, 
    NotificationPreferences
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Configuration admin pour le modèle User personnalisé."""
    
    list_display = [
        'email', 'first_name', 'last_name', 
        'is_verified', 'is_active', 'is_staff', 
        'created_at'
    ]
    list_filter = [
        'is_verified', 'is_active', 'is_staff', 
        'is_superuser', 'currency'
    ]
    search_fields = ['email', 'first_name', 'last_name', 'phone_number']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informations personnelles'), {
            'fields': ('first_name', 'last_name', 'phone_number', 'avatar')
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


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    """Admin pour les codes de vérification OTP."""
    
    list_display = [
        'email', 'purpose', 'code', 'display_status',
        'attempts', 'created_at', 'expires_at'
    ]
    list_filter = ['purpose', 'is_used', 'created_at']
    search_fields = ['email', 'code']
    ordering = ['-created_at']
    readonly_fields = ['code', 'created_at', 'used_at']
    
    fieldsets = (
        (None, {
            'fields': ('email', 'user', 'code', 'purpose')
        }),
        ('Statut', {
            'fields': ('is_used', 'attempts', 'max_attempts')
        }),
        ('Dates', {
            'fields': ('created_at', 'expires_at', 'used_at')
        }),
    )
    
    def display_status(self, obj):
        if obj.is_used:
            return format_html('<span style="color: #10B981;">✓ Utilisé</span>')
        if obj.is_expired:
            return format_html('<span style="color: #EF4444;">✗ Expiré</span>')
        if obj.remaining_attempts <= 0:
            return format_html('<span style="color: #EF4444;">✗ Bloqué</span>')
        return format_html('<span style="color: #F59E0B;">⏳ En attente</span>')
    display_status.short_description = 'Statut'


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """Admin pour les tokens de réinitialisation."""
    
    list_display = ['user', 'display_token', 'display_status', 'created_at', 'expires_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'token']
    ordering = ['-created_at']
    readonly_fields = ['token', 'created_at', 'used_at']
    
    def display_token(self, obj):
        return f"{obj.token[:20]}..."
    display_token.short_description = 'Token'
    
    def display_status(self, obj):
        if obj.is_used:
            return format_html('<span style="color: #10B981;">✓ Utilisé</span>')
        if not obj.is_valid:
            return format_html('<span style="color: #EF4444;">✗ Expiré</span>')
        return format_html('<span style="color: #F59E0B;">⏳ Valide</span>')
    display_status.short_description = 'Statut'


@admin.register(NotificationPreferences)
class NotificationPreferencesAdmin(admin.ModelAdmin):
    """Admin pour les préférences de notification."""
    
    list_display = [
        'user', 'email_reminders', 'email_budget_alerts',
        'email_weekly_summary', 'push_enabled'
    ]
    list_filter = [
        'email_reminders', 'email_budget_alerts',
        'email_weekly_summary', 'push_enabled'
    ]
    search_fields = ['user__email']
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user',)
        }),
        ('Notifications Email', {
            'fields': (
                'email_reminders', 'email_weekly_summary',
                'email_group_activity', 'email_budget_alerts',
                'email_payment_notifications'
            )
        }),
        ('Notifications Push', {
            'fields': ('push_enabled',)
        }),
        ('Paramètres', {
            'fields': ('reminder_time',)
        }),
    )