# payments/services/__init__.py

from .base import BasePaymentService
from .orange_money import OrangeMoneyService
from .mtn_momo import MTNMoMoService

__all__ = ['BasePaymentService', 'OrangeMoneyService', 'MTNMoMoService']


def get_payment_service(provider_name):
    """Factory pour obtenir le service de paiement approprié"""
    services = {
        'orange_money': OrangeMoneyService,
        'mtn_momo': MTNMoMoService,
    }
    
    service_class = services.get(provider_name)
    if not service_class:
        raise ValueError(f"Service de paiement inconnu: {provider_name}")
    
    return service_class()
