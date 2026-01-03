"""
Admin configuration for events app.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """
    Configuration admin pour les événements.
    """
    
    list_display = [
        'title', 'user', 'start_date', 'end_date',
        'all_day', 'display_color', 'has_transaction', 'has_reminder'
    ]
    list_filter = ['all_day', 'start_date', 'created_at']
    search_fields = ['title', 'description', 'user__email']
    ordering = ['-start_date']
    date_hierarchy = 'start_date'
    
    raw_id_fields = ['user', 'transaction', 'reminder']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'description')
        }),
        ('Dates et heures', {
            'fields': ('start_date', 'end_date', 'all_day')
        }),
        ('Apparence', {
            'fields': ('color',)
        }),
        ('Liens', {
            'fields': ('transaction', 'reminder'),
            'classes': ('collapse',)
        }),
    )
    
    def display_color(self, obj):
        """Affiche la couleur avec un aperçu."""
        return format_html(
            '<span style="background-color: {}; padding: 2px 10px; '
            'border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.color
        )
    display_color.short_description = 'Couleur'
    
    def has_transaction(self, obj):
        """Indique si lié à une transaction."""
        return obj.transaction is not None
    has_transaction.boolean = True
    has_transaction.short_description = 'Transaction'
    
    def has_reminder(self, obj):
        """Indique si lié à un rappel."""
        return obj.reminder is not None
    has_reminder.boolean = True
    has_reminder.short_description = 'Rappel'