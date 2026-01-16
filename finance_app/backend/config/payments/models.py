# payments/models.py
# Modèles pour les paiements Mobile Money (Orange, MTN)

import uuid
import secrets
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from decimal import Decimal


class PaymentProvider(models.Model):
    """Fournisseur de paiement (Orange Money, MTN Mobile Money, etc.)"""
    
    PROVIDER_CHOICES = [
        ('orange_money', 'Orange Money'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('moov_money', 'Moov Money'),
        ('wave', 'Wave'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, choices=PROVIDER_CHOICES, unique=True)
    display_name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='payment_providers/', null=True, blank=True)
    
    # Configuration API (à remplir quand vous aurez les clés)
    api_base_url = models.URLField(blank=True, null=True)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    api_secret = models.CharField(max_length=255, blank=True, null=True)
    merchant_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Configuration spécifique (JSON)
    config = models.JSONField(default=dict, blank=True)
    
    is_active = models.BooleanField(default=False)
    is_sandbox = models.BooleanField(default=True, help_text="Mode test/sandbox")
    
    # Frais
    fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Frais en pourcentage"
    )
    fee_fixed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Frais fixes par transaction"
    )
    
    # Limites
    min_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('100.00')
    )
    max_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1000000.00')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Fournisseur de paiement"
        verbose_name_plural = "Fournisseurs de paiement"
    
    def __str__(self):
        return self.display_name
    
    def calculate_fee(self, amount):
        """Calcule les frais pour un montant donné"""
        percentage_fee = amount * (self.fee_percentage / 100)
        return percentage_fee + self.fee_fixed


class UserPaymentMethod(models.Model):
    """Méthode de paiement enregistrée par l'utilisateur"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    provider = models.ForeignKey(
        PaymentProvider,
        on_delete=models.PROTECT,
        related_name='user_methods'
    )
    
    # Numéro de téléphone (format international)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Le numéro doit être au format: '+999999999'. 9 à 15 chiffres autorisés."
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        verbose_name="Numéro de téléphone"
    )
    
    # Nom associé au compte
    account_name = models.CharField(max_length=100, blank=True)
    
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    # Métadonnées du provider
    provider_account_id = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Méthode de paiement"
        verbose_name_plural = "Méthodes de paiement"
        unique_together = ['user', 'provider', 'phone_number']
    
    def __str__(self):
        return f"{self.provider.display_name} - {self.phone_number}"
    
    def save(self, *args, **kwargs):
        # S'assurer qu'il n'y a qu'une seule méthode par défaut
        if self.is_default:
            UserPaymentMethod.objects.filter(
                user=self.user,
                is_default=True
            ).update(is_default=False)
        super().save(*args, **kwargs)


class Payment(models.Model):
    """Transaction de paiement"""
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En cours'),
        ('completed', 'Complété'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
        ('refunded', 'Remboursé'),
    ]
    
    TYPE_CHOICES = [
        ('deposit', 'Dépôt'),        # Ajouter de l'argent
        ('withdrawal', 'Retrait'),   # Retirer de l'argent
        ('transfer', 'Transfert'),   # Transfert entre utilisateurs
        ('payment', 'Paiement'),     # Paiement de facture/service
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Référence unique pour le suivi
    reference = models.CharField(max_length=50, unique=True, editable=False)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    payment_method = models.ForeignKey(
        UserPaymentMethod,
        on_delete=models.PROTECT,
        related_name='payments',
        null=True,
        blank=True
    )
    provider = models.ForeignKey(
        PaymentProvider,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    
    # Pour les transferts entre utilisateurs
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='received_payments',
        null=True,
        blank=True
    )
    recipient_phone = models.CharField(max_length=17, blank=True, null=True)
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='XAF')  # Franc CFA
    
    # Frais
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    description = models.TextField(blank=True)
    
    # Réponse du provider
    provider_reference = models.CharField(max_length=100, blank=True, null=True)
    provider_response = models.JSONField(default=dict, blank=True)
    
    # Dates
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Métadonnées
    metadata = models.JSONField(default=dict, blank=True)
    
    # Erreur en cas d'échec
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['reference']),
            models.Index(fields=['provider_reference']),
        ]
    
    def __str__(self):
        return f"{self.reference} - {self.amount} {self.currency}"
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_reference()
        if not self.total_amount:
            self.total_amount = self.amount + self.fee
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_reference():
        """Génère une référence unique"""
        import time
        timestamp = int(time.time() * 1000)
        random_part = secrets.token_hex(4).upper()
        return f"PAY-{timestamp}-{random_part}"


class PaymentWebhook(models.Model):
    """Log des webhooks reçus des providers"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        PaymentProvider,
        on_delete=models.CASCADE,
        related_name='webhooks'
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='webhooks'
    )
    
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Webhook de paiement"
        verbose_name_plural = "Webhooks de paiement"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.provider.name} - {self.event_type}"


class Wallet(models.Model):
    """Portefeuille utilisateur (solde interne)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(max_length=3, default='XAF')
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Portefeuille"
        verbose_name_plural = "Portefeuilles"
    
    def __str__(self):
        return f"{self.user.email} - {self.balance} {self.currency}"
    
    def credit(self, amount, description=""):
        """Créditer le portefeuille"""
        if amount <= 0:
            raise ValueError("Le montant doit être positif")
        
        self.balance += Decimal(str(amount))
        self.save()
        
        WalletTransaction.objects.create(
            wallet=self,
            type='credit',
            amount=amount,
            balance_after=self.balance,
            description=description
        )
        
        return self.balance
    
    def debit(self, amount, description=""):
        """Débiter le portefeuille"""
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Le montant doit être positif")
        if amount > self.balance:
            raise ValueError("Solde insuffisant")
        
        self.balance -= amount
        self.save()
        
        WalletTransaction.objects.create(
            wallet=self,
            type='debit',
            amount=amount,
            balance_after=self.balance,
            description=description
        )
        
        return self.balance


class WalletTransaction(models.Model):
    """Historique des transactions du portefeuille"""
    
    TYPE_CHOICES = [
        ('credit', 'Crédit'),
        ('debit', 'Débit'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Lien optionnel avec un paiement
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions'
    )
    
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Transaction portefeuille"
        verbose_name_plural = "Transactions portefeuille"
        ordering = ['-created_at']
    
    def __str__(self):
        sign = '+' if self.type == 'credit' else '-'
        return f"{sign}{self.amount} - {self.description[:30]}"
