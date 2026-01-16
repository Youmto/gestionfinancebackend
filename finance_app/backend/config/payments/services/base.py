# payments/services/base.py
# Service de base pour les paiements Mobile Money

from abc import ABC, abstractmethod
from typing import Dict, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class PaymentResult:
    """Résultat d'une opération de paiement"""
    
    def __init__(
        self,
        success: bool,
        reference: str = None,
        provider_reference: str = None,
        status: str = None,
        message: str = None,
        data: Dict = None
    ):
        self.success = success
        self.reference = reference
        self.provider_reference = provider_reference
        self.status = status
        self.message = message
        self.data = data or {}
    
    def to_dict(self):
        return {
            'success': self.success,
            'reference': self.reference,
            'provider_reference': self.provider_reference,
            'status': self.status,
            'message': self.message,
            'data': self.data
        }


class BasePaymentService(ABC):
    """
    Service de base abstrait pour les paiements Mobile Money.
    
    Chaque fournisseur (Orange, MTN, etc.) doit implémenter cette interface.
    """
    
    provider_name: str = None
    
    def __init__(self):
        self.provider = None
        self._load_provider()
    
    def _load_provider(self):
        """Charge la configuration du fournisseur depuis la base de données"""
        from payments.models import PaymentProvider
        
        try:
            self.provider = PaymentProvider.objects.get(
                name=self.provider_name,
                is_active=True
            )
        except PaymentProvider.DoesNotExist:
            logger.warning(f"Provider {self.provider_name} non trouvé ou inactif")
            self.provider = None
    
    @property
    def is_configured(self) -> bool:
        """Vérifie si le service est correctement configuré"""
        if not self.provider:
            return False
        return bool(self.provider.api_key and self.provider.api_secret)
    
    @property
    def is_sandbox(self) -> bool:
        """Vérifie si on est en mode sandbox/test"""
        return self.provider.is_sandbox if self.provider else True
    
    def get_api_url(self) -> str:
        """Retourne l'URL de l'API"""
        if not self.provider:
            return ""
        return self.provider.api_base_url or ""
    
    def calculate_fee(self, amount: Decimal) -> Decimal:
        """Calcule les frais pour un montant donné"""
        if not self.provider:
            return Decimal('0.00')
        return self.provider.calculate_fee(amount)
    
    # ==========================================
    # Méthodes abstraites à implémenter
    # ==========================================
    
    @abstractmethod
    def initiate_deposit(
        self,
        phone_number: str,
        amount: Decimal,
        reference: str,
        description: str = ""
    ) -> PaymentResult:
        """
        Initie un dépôt (collecte d'argent du client).
        
        Args:
            phone_number: Numéro de téléphone du client
            amount: Montant à collecter
            reference: Référence unique de la transaction
            description: Description de la transaction
            
        Returns:
            PaymentResult avec le statut de l'opération
        """
        pass
    
    @abstractmethod
    def initiate_withdrawal(
        self,
        phone_number: str,
        amount: Decimal,
        reference: str,
        description: str = ""
    ) -> PaymentResult:
        """
        Initie un retrait (envoi d'argent au client).
        
        Args:
            phone_number: Numéro de téléphone du client
            amount: Montant à envoyer
            reference: Référence unique de la transaction
            description: Description de la transaction
            
        Returns:
            PaymentResult avec le statut de l'opération
        """
        pass
    
    @abstractmethod
    def check_status(self, reference: str) -> PaymentResult:
        """
        Vérifie le statut d'une transaction.
        
        Args:
            reference: Référence de la transaction
            
        Returns:
            PaymentResult avec le statut actuel
        """
        pass
    
    @abstractmethod
    def verify_webhook(self, payload: Dict, signature: str) -> bool:
        """
        Vérifie l'authenticité d'un webhook.
        
        Args:
            payload: Données du webhook
            signature: Signature à vérifier
            
        Returns:
            True si le webhook est valide
        """
        pass
    
    @abstractmethod
    def process_webhook(self, payload: Dict) -> PaymentResult:
        """
        Traite un webhook reçu.
        
        Args:
            payload: Données du webhook
            
        Returns:
            PaymentResult avec les informations extraites
        """
        pass
    
    # ==========================================
    # Méthodes utilitaires
    # ==========================================
    
    def format_phone_number(self, phone_number: str, country_code: str = "237") -> str:
        """Formate un numéro de téléphone au format international"""
        # Supprimer les espaces et caractères spéciaux
        phone = ''.join(filter(str.isdigit, phone_number))
        
        # Ajouter le code pays si nécessaire
        if not phone.startswith(country_code):
            if phone.startswith('0'):
                phone = phone[1:]
            phone = country_code + phone
        
        return phone
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """Valide un numéro de téléphone"""
        phone = self.format_phone_number(phone_number)
        # Vérifier la longueur (9-12 chiffres + code pays)
        return 9 <= len(phone) <= 15
    
    def log_transaction(self, action: str, reference: str, data: Dict):
        """Log une transaction pour le débogage"""
        logger.info(f"[{self.provider_name}] {action} - Ref: {reference} - Data: {data}")
