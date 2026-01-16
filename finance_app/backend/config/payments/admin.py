# payments/admin.py

from django.contrib import admin
from .models import (
    PaymentProvider, UserPaymentMethod, Payment,
    PaymentWebhook, Wallet, WalletTransaction
)


@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'is_active', 'is_sandbox', 'fee_percentage', 'fee_fixed']
    list_filter = ['is_active', 'is_sandbox', 'name']
    search_fields = ['name', 'display_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserPaymentMethod)
class UserPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider', 'phone_number', 'is_default', 'is_verified', 'created_at']
    list_filter = ['provider', 'is_default', 'is_verified']
    search_fields = ['user__email', 'phone_number', 'account_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['reference', 'user', 'provider', 'type', 'amount', 'currency', 'status', 'created_at']
    list_filter = ['status', 'type', 'provider', 'currency']
    search_fields = ['reference', 'user__email', 'provider_reference']
    readonly_fields = ['reference', 'created_at', 'updated_at', 'initiated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('reference', 'user', 'provider', 'payment_method', 'type', 'status')
        }),
        ('Montants', {
            'fields': ('amount', 'fee', 'total_amount', 'currency')
        }),
        ('Transfert', {
            'fields': ('recipient', 'recipient_phone'),
            'classes': ('collapse',)
        }),
        ('Provider', {
            'fields': ('provider_reference', 'provider_response', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('initiated_at', 'completed_at', 'created_at', 'updated_at')
        }),
    )


@admin.register(PaymentWebhook)
class PaymentWebhookAdmin(admin.ModelAdmin):
    list_display = ['provider', 'event_type', 'payment', 'is_processed', 'created_at']
    list_filter = ['provider', 'is_processed', 'event_type']
    search_fields = ['event_type', 'payment__reference']
    readonly_fields = ['created_at']


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'currency', 'is_active', 'updated_at']
    list_filter = ['is_active', 'currency']
    search_fields = ['user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'type', 'amount', 'balance_after', 'created_at']
    list_filter = ['type']
    search_fields = ['wallet__user__email', 'description']
    readonly_fields = ['created_at']
