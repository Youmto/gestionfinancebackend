"""
Admin configuration for finances app.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Transaction, ExpenseSplit


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Configuration admin pour les catégories.
    """
    
    list_display = [
        'name', 'display_icon', 'type', 'display_color',
        'is_system', 'user', 'created_at'
    ]
    list_filter = ['type', 'is_system', 'created_at']
    search_fields = ['name', 'user__email']
    ordering = ['name']
    
    def display_icon(self, obj):
        """Affiche l'icône emoji."""
        return obj.icon
    display_icon.short_description = 'Icône'
    
    def display_color(self, obj):
        """Affiche la couleur avec un aperçu."""
        return format_html(
            '<span style="background-color: {}; padding: 2px 10px; '
            'border-radius: 3px;">{}</span>',
            obj.color, obj.color
        )
    display_color.short_description = 'Couleur'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Configuration admin pour les transactions.
    """
    
    list_display = [
        'id', 'description_short', 'display_amount', 'type',
        'category', 'user', 'group', 'date', 'is_deleted'
    ]
    list_filter = ['type', 'is_deleted', 'is_recurring', 'date', 'created_at']
    search_fields = ['description', 'user__email', 'category__name']
    ordering = ['-date', '-created_at']
    date_hierarchy = 'date'
    
    raw_id_fields = ['user', 'category', 'group']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'type', 'amount', 'category', 'description')
        }),
        ('Groupe', {
            'fields': ('group',),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('date',)
        }),
        ('Récurrence', {
            'fields': ('is_recurring', 'recurring_config'),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('is_deleted', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def description_short(self, obj):
        """Affiche une version courte de la description."""
        if obj.description and len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description or '-'
    description_short.short_description = 'Description'
    
    def display_amount(self, obj):
        """Affiche le montant avec formatage."""
        color = 'green' if obj.type == 'income' else 'red'
        sign = '+' if obj.type == 'income' else '-'
        return format_html(
            '<span style="color: {};">{}{}</span>',
            color, sign, obj.amount
        )
    display_amount.short_description = 'Montant'


@admin.register(ExpenseSplit)
class ExpenseSplitAdmin(admin.ModelAdmin):
    """
    Configuration admin pour les partages de dépenses.
    """
    
    list_display = [
        'id', 'transaction', 'user', 'amount',
        'is_paid', 'paid_at', 'created_at'
    ]
    list_filter = ['is_paid', 'created_at']
    search_fields = ['transaction__description', 'user__email']
    ordering = ['-created_at']
    
    raw_id_fields = ['transaction', 'user']