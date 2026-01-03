"""
Admin configuration for reminders app.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Reminder


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    """
    Configuration admin pour les rappels.
    """
    
    list_display = [
        'title', 'user', 'group', 'reminder_type',
        'display_status', 'reminder_date', 'is_recurring', 'created_at'
    ]
    list_filter = [
        'reminder_type', 'is_completed', 'is_recurring',
        'notification_sent', 'created_at'
    ]
    search_fields = ['title', 'description', 'user__email', 'group__name']
    ordering = ['reminder_date']
    date_hierarchy = 'reminder_date'
    
    raw_id_fields = ['user', 'group']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'group', 'title', 'description')
        }),
        ('Détails', {
            'fields': ('reminder_type', 'amount', 'reminder_date')
        }),
        ('Récurrence', {
            'fields': ('is_recurring', 'recurring_config'),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': (
                'is_completed', 'completed_at',
                'notification_sent', 'notification_sent_at'
            )
        }),
    )
    
    readonly_fields = ['completed_at', 'notification_sent_at']
    
    def display_status(self, obj):
        """Affiche le statut avec un indicateur visuel."""
        if obj.is_completed:
            return format_html(
                '<span style="color: green;">✓ Terminé</span>'
            )
        elif obj.is_overdue:
            return format_html(
                '<span style="color: red;">⚠ En retard</span>'
            )
        else:
            return format_html(
                '<span style="color: orange;">⏳ En attente</span>'
            )
    display_status.short_description = 'Statut'