# payments/serializers.py

from rest_framework import serializers
from .models import (
    PaymentProvider, UserPaymentMethod, Payment,
    Wallet, WalletTransaction
)


class PaymentProviderSerializer(serializers.ModelSerializer):
    """Serializer pour les fournisseurs de paiement"""
    
    class Meta:
        model = PaymentProvider
        fields = [
            'id', 'name', 'display_name', 'logo',
            'is_active', 'fee_percentage', 'fee_fixed',
            'min_amount', 'max_amount'
        ]


class UserPaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer pour les méthodes de paiement utilisateur"""
    
    provider_name = serializers.CharField(source='provider.display_name', read_only=True)
    provider_logo = serializers.ImageField(source='provider.logo', read_only=True)
    
    class Meta:
        model = UserPaymentMethod
        fields = [
            'id', 'provider', 'provider_name', 'provider_logo',
            'phone_number', 'account_name',
            'is_default', 'is_verified',
            'created_at'
        ]
        read_only_fields = ['id', 'is_verified', 'created_at']


class UserPaymentMethodCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer une méthode de paiement"""
    
    class Meta:
        model = UserPaymentMethod
        fields = ['provider', 'phone_number', 'account_name', 'is_default']
    
    def validate_phone_number(self, value):
        # Normaliser le numéro de téléphone
        if not value.startswith('+'):
            # Ajouter le code pays par défaut (Cameroun)
            value = '+237' + value.lstrip('0')
        return value
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer pour les paiements"""
    
    provider_name = serializers.CharField(source='provider.display_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'reference', 'provider', 'provider_name',
            'type', 'type_display', 'status', 'status_display',
            'amount', 'fee', 'total_amount', 'currency',
            'description', 'recipient_phone',
            'initiated_at', 'completed_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'reference', 'status', 'fee', 'total_amount',
            'initiated_at', 'completed_at', 'created_at'
        ]


class DepositSerializer(serializers.Serializer):
    """Serializer pour initier un dépôt"""
    
    provider = serializers.UUIDField()
    phone_number = serializers.CharField(max_length=17)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    def validate_phone_number(self, value):
        if not value.startswith('+'):
            value = '+237' + value.lstrip('0')
        return value
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être positif")
        return value
    
    def validate(self, data):
        try:
            provider = PaymentProvider.objects.get(id=data['provider'], is_active=True)
        except PaymentProvider.DoesNotExist:
            raise serializers.ValidationError({'provider': 'Fournisseur non trouvé ou inactif'})
        
        if data['amount'] < provider.min_amount:
            raise serializers.ValidationError({
                'amount': f'Le montant minimum est {provider.min_amount} {provider.currency if hasattr(provider, "currency") else "XAF"}'
            })
        
        if data['amount'] > provider.max_amount:
            raise serializers.ValidationError({
                'amount': f'Le montant maximum est {provider.max_amount}'
            })
        
        data['provider_obj'] = provider
        return data


class WithdrawalSerializer(serializers.Serializer):
    """Serializer pour initier un retrait"""
    
    payment_method = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être positif")
        return value
    
    def validate(self, data):
        user = self.context['request'].user
        
        try:
            payment_method = UserPaymentMethod.objects.get(
                id=data['payment_method'],
                user=user
            )
        except UserPaymentMethod.DoesNotExist:
            raise serializers.ValidationError({'payment_method': 'Méthode de paiement non trouvée'})
        
        # Vérifier le solde du portefeuille
        try:
            wallet = user.wallet
            if data['amount'] > wallet.balance:
                raise serializers.ValidationError({'amount': 'Solde insuffisant'})
        except Wallet.DoesNotExist:
            raise serializers.ValidationError({'amount': 'Portefeuille non trouvé'})
        
        data['payment_method_obj'] = payment_method
        return data


class TransferSerializer(serializers.Serializer):
    """Serializer pour un transfert entre utilisateurs"""
    
    recipient_phone = serializers.CharField(max_length=17)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    
    def validate_recipient_phone(self, value):
        if not value.startswith('+'):
            value = '+237' + value.lstrip('0')
        return value
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être positif")
        return value
    
    def validate(self, data):
        user = self.context['request'].user
        
        # Vérifier le solde
        try:
            wallet = user.wallet
            if data['amount'] > wallet.balance:
                raise serializers.ValidationError({'amount': 'Solde insuffisant'})
        except Wallet.DoesNotExist:
            raise serializers.ValidationError({'amount': 'Portefeuille non trouvé'})
        
        return data


class WalletSerializer(serializers.ModelSerializer):
    """Serializer pour le portefeuille"""
    
    class Meta:
        model = Wallet
        fields = ['id', 'balance', 'currency', 'is_active', 'updated_at']
        read_only_fields = fields


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer pour les transactions du portefeuille"""
    
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'type', 'type_display', 'amount',
            'balance_after', 'description', 'payment',
            'created_at'
        ]
        read_only_fields = fields
