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
        'display_budget', 'budget_alert_threshold',
        'is_system', 'user', 'created_at'
    ]
    list_filter = ['type', 'is_system', 'created_at']
    search_fields = ['name', 'description', 'user__email']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at', 'display_budget_status']
    
    fieldsets = (
        ('Informations', {
            'fields': ('name', 'description', 'icon', 'color', 'type')
        }),
        ('Budget', {
            'fields': ('budget', 'budget_alert_threshold', 'display_budget_status'),
            'classes': ('collapse',),
            'description': 'Définir un budget mensuel pour suivre les dépenses de cette catégorie'
        }),
        ('Propriétaire', {
            'fields': ('is_system', 'user')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_icon(self, obj):
        """Affiche l'icône emoji."""
        return obj.icon
    display_icon.short_description = 'Icône'
    
    def display_color(self, obj):
        """Affiche la couleur avec un aperçu."""
        return format_html(
            '<span style="background-color: {}; padding: 2px 10px; '
            'border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.color
        )
    display_color.short_description = 'Couleur'
    
    def display_budget(self, obj):
        """Affiche le budget formaté."""
        if obj.budget:
            return format_html(
                '<span style="color: #059669; font-weight: bold;">{:,.0f} XAF</span>',
                obj.budget
            )
        return format_html('<span style="color: #9CA3AF;">-</span>')
    display_budget.short_description = 'Budget mensuel'
    display_budget.admin_order_field = 'budget'
    
    def display_budget_status(self, obj):
        """Affiche le statut du budget dans le formulaire."""
        status = obj.get_budget_status()
        if not status:
            return "Aucun budget défini pour cette catégorie."
        
        # Couleur selon le statut
        color = '#059669'  # Vert
        status_text = "✓ Bon"
        if status['is_over_budget']:
            color = '#DC2626'  # Rouge
            status_text = "✗ Dépassé"
        elif status['is_alert']:
            color = '#F59E0B'  # Orange
            status_text = "⚠ Alerte"
        
        return format_html(
            '''
            <div style="padding: 15px; background: #F9FAFB; border-radius: 8px; border-left: 4px solid {};">
                <p style="margin: 5px 0;"><strong>Budget mensuel:</strong> {:,.0f} XAF</p>
                <p style="margin: 5px 0;"><strong>Dépensé ce mois:</strong> {:,.0f} XAF</p>
                <p style="margin: 5px 0;"><strong>Restant:</strong> {:,.0f} XAF</p>
                <p style="margin: 5px 0;"><strong>Progression:</strong> 
                    <span style="color: {}; font-weight: bold;">{:.1f}%</span>
                </p>
                <p style="margin: 5px 0;"><strong>Statut:</strong> 
                    <span style="color: {}; font-weight: bold;">{}</span>
                </p>
            </div>
            ''',
            color,
            status['budget'],
            status['spent'],
            status['remaining'],
            color,
            status['percentage'],
            color,
            status_text
        )
    display_budget_status.short_description = 'Statut du budget (mois en cours)'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Configuration admin pour les transactions.
    """
    
    list_display = [
        'id', 'description_short', 'display_amount', 'type',
        'category', 'user', 'group', 'date', 'is_deleted'
    ]
    list_filter = ['type', 'is_deleted', 'is_recurring', 'date', 'created_at', 'category']
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
        ('Pièce jointe', {
            'fields': ('attachment',),
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
        color = '#059669' if obj.type == 'income' else '#DC2626'
        sign = '+' if obj.type == 'income' else '-'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{:,.0f} XAF</span>',
            color, sign, obj.amount
        )
    display_amount.short_description = 'Montant'
    display_amount.admin_order_field = 'amount'


@admin.register(ExpenseSplit)
class ExpenseSplitAdmin(admin.ModelAdmin):
    """
    Configuration admin pour les partages de dépenses.
    """
    
    list_display = [
        'id', 'transaction', 'user', 'display_amount',
        'display_status', 'paid_at', 'created_at'
    ]
    list_filter = ['is_paid', 'created_at', 'paid_at']
    search_fields = ['transaction__description', 'user__email']
    ordering = ['-created_at']
    
    raw_id_fields = ['transaction', 'user']
    
    def display_amount(self, obj):
        """Affiche le montant formaté."""
        return format_html(
            '<span style="font-weight: bold;">{:,.0f} XAF</span>',
            obj.amount
        )
    display_amount.short_description = 'Montant'
    
    def display_status(self, obj):
        """Affiche le statut de paiement."""
        if obj.is_paid:
            return format_html(
                '<span style="color: #059669; font-weight: bold;">✓ Payé</span>'
            )
        return format_html(
            '<span style="color: #F59E0B; font-weight: bold;">⏳ En attente</span>'
        )
    display_status.short_description = 'Statut'