# payments/services/orange_money.py
# Service de paiement Orange Money

import requests
import hashlib
import hmac
import json
import logging
from typing import Dict
from decimal import Decimal
from datetime import datetime

from .base import BasePaymentService, PaymentResult

logger = logging.getLogger(__name__)


class OrangeMoneyService(BasePaymentService):
    """
    Service de paiement Orange Money.
    
    Documentation API Orange Money:
    - Sandbox: https://developer.orange.com/apis/om-webpay-cm-sandbox
    - Production: https://developer.orange.com/apis/om-webpay-cm
    
    IMPORTANT: Remplacez les URLs et configurations par celles fournies par Orange
    quand vous aurez accès à l'API.
    """
    
    provider_name = 'orange_money'
    
    # URLs par défaut (à remplacer par les vraies URLs)
    SANDBOX_URL = "https://api.orange.com/orange-money-webpay/cm/v1"
    PRODUCTION_URL = "https://api.orange.com/orange-money-webpay/cm/v1"
    
    def __init__(self):
        super().__init__()
        self._access_token = None
        self._token_expires_at = None
    
    @property
    def api_url(self) -> str:
        """Retourne l'URL de l'API selon le mode"""
        if self.provider and self.provider.api_base_url:
            return self.provider.api_base_url
        return self.SANDBOX_URL if self.is_sandbox else self.PRODUCTION_URL
    
    def _get_access_token(self) -> str:
        """
        Obtient un token d'accès OAuth2.
        
        Note: Cette méthode devra être adaptée selon la documentation Orange.
        """
        if not self.is_configured:
            logger.error("Orange Money non configuré")
            return None
        
        # Vérifier si le token est encore valide
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._access_token
        
        try:
            # TODO: Implémenter l'authentification OAuth2 Orange
            # Exemple de structure (à adapter):
            """
            auth_url = "https://api.orange.com/oauth/v3/token"
            
            response = requests.post(
                auth_url,
                headers={
                    'Authorization': f'Basic {base64_credentials}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data={
                    'grant_type': 'client_credentials'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data['access_token']
                self._token_expires_at = datetime.now() + timedelta(seconds=data['expires_in'])
                return self._access_token
            """
            
            # Pour le moment, retourner None (pas encore configuré)
            logger.warning("Orange Money: Authentification non implémentée")
            return None
            
        except Exception as e:
            logger.error(f"Erreur authentification Orange: {e}")
            return None
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Effectue une requête à l'API Orange Money"""
        
        token = self._get_access_token()
        if not token:
            return {'error': 'Impossible d\'obtenir le token d\'accès'}
        
        url = f"{self.api_url}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                return {'error': f'Méthode HTTP non supportée: {method}'}
            
            return response.json()
            
        except requests.exceptions.Timeout:
            return {'error': 'Timeout de la requête'}
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}
        except json.JSONDecodeError:
            return {'error': 'Réponse invalide du serveur'}
    
    def initiate_deposit(
        self,
        phone_number: str,
        amount: Decimal,
        reference: str,
        description: str = ""
    ) -> PaymentResult:
        """
        Initie un paiement (collecte d'argent).
        
        Le client recevra une notification sur son téléphone pour confirmer le paiement.
        """
        
        if not self.is_configured:
            return PaymentResult(
                success=False,
                reference=reference,
                status='failed',
                message="Orange Money non configuré. Veuillez contacter l'administrateur."
            )
        
        phone = self.format_phone_number(phone_number)
        
        # Structure de la requête (à adapter selon la doc Orange)
        payload = {
            'merchant_key': self.provider.merchant_id,
            'currency': 'XAF',
            'order_id': reference,
            'amount': str(amount),
            'return_url': f"{self.provider.config.get('return_url', '')}/payment/callback",
            'cancel_url': f"{self.provider.config.get('cancel_url', '')}/payment/cancel",
            'notif_url': f"{self.provider.config.get('webhook_url', '')}/api/v1/payments/webhook/orange/",
            'lang': 'fr',
            'reference': description or f"Dépôt {reference}",
            'msisdn': phone,  # Numéro du client
        }
        
        self.log_transaction('DEPOSIT_INIT', reference, {'phone': phone, 'amount': str(amount)})
        
        # TODO: Décommenter quand l'API sera configurée
        """
        response = self._make_request('POST', 'webpayment', payload)
        
        if 'error' in response:
            return PaymentResult(
                success=False,
                reference=reference,
                status='failed',
                message=response['error']
            )
        
        # Extraire les informations de la réponse
        return PaymentResult(
            success=True,
            reference=reference,
            provider_reference=response.get('pay_token'),
            status='pending',
            message='Paiement initié. Veuillez confirmer sur votre téléphone.',
            data={
                'payment_url': response.get('payment_url'),
                'pay_token': response.get('pay_token')
            }
        )
        """
        
        # Simulation pour le développement
        return PaymentResult(
            success=True,
            reference=reference,
            provider_reference=f"OM-{reference}",
            status='pending',
            message='[SIMULATION] Paiement initié. En attente de configuration API Orange.',
            data={
                'simulation': True,
                'phone': phone,
                'amount': str(amount)
            }
        )
    
    def initiate_withdrawal(
        self,
        phone_number: str,
        amount: Decimal,
        reference: str,
        description: str = ""
    ) -> PaymentResult:
        """
        Initie un retrait (envoi d'argent au client).
        """
        
        if not self.is_configured:
            return PaymentResult(
                success=False,
                reference=reference,
                status='failed',
                message="Orange Money non configuré."
            )
        
        phone = self.format_phone_number(phone_number)
        
        # Structure de la requête pour le disbursement (à adapter)
        payload = {
            'merchant_key': self.provider.merchant_id,
            'currency': 'XAF',
            'order_id': reference,
            'amount': str(amount),
            'subscriber_msisdn': phone,
            'reference': description or f"Retrait {reference}",
        }
        
        self.log_transaction('WITHDRAWAL_INIT', reference, {'phone': phone, 'amount': str(amount)})
        
        # Simulation
        return PaymentResult(
            success=True,
            reference=reference,
            provider_reference=f"OM-OUT-{reference}",
            status='pending',
            message='[SIMULATION] Retrait initié. En attente de configuration API Orange.',
            data={
                'simulation': True,
                'phone': phone,
                'amount': str(amount)
            }
        )
    
    def check_status(self, reference: str) -> PaymentResult:
        """Vérifie le statut d'une transaction"""
        
        if not self.is_configured:
            return PaymentResult(
                success=False,
                reference=reference,
                status='unknown',
                message="Orange Money non configuré."
            )
        
        # TODO: Implémenter la vérification du statut
        """
        response = self._make_request('GET', f'webpayment/{reference}/status')
        
        if 'error' in response:
            return PaymentResult(
                success=False,
                reference=reference,
                status='unknown',
                message=response['error']
            )
        
        status_mapping = {
            'INITIATED': 'pending',
            'PENDING': 'processing',
            'SUCCESS': 'completed',
            'FAILED': 'failed',
            'CANCELLED': 'cancelled',
            'EXPIRED': 'failed'
        }
        
        return PaymentResult(
            success=True,
            reference=reference,
            provider_reference=response.get('txnid'),
            status=status_mapping.get(response.get('status'), 'unknown'),
            message=response.get('message', ''),
            data=response
        )
        """
        
        # Simulation
        return PaymentResult(
            success=True,
            reference=reference,
            status='pending',
            message='[SIMULATION] Statut non disponible sans configuration API.'
        )
    
    def verify_webhook(self, payload: Dict, signature: str) -> bool:
        """Vérifie la signature d'un webhook Orange Money"""
        
        if not self.provider or not self.provider.api_secret:
            return False
        
        # TODO: Implémenter la vérification de signature selon la doc Orange
        """
        # Exemple de vérification HMAC
        expected_signature = hmac.new(
            self.provider.api_secret.encode(),
            json.dumps(payload, sort_keys=True).encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
        """
        
        return True  # À remplacer par la vraie vérification
    
    def process_webhook(self, payload: Dict) -> PaymentResult:
        """Traite un webhook Orange Money"""
        
        # Structure attendue (à adapter selon la doc Orange)
        """
        {
            "status": "SUCCESS",
            "order_id": "PAY-xxx",
            "txnid": "OM-xxx",
            "amount": "1000",
            "message": "Transaction successful"
        }
        """
        
        status_mapping = {
            'SUCCESS': 'completed',
            'FAILED': 'failed',
            'CANCELLED': 'cancelled',
            'PENDING': 'processing'
        }
        
        order_id = payload.get('order_id', payload.get('reference', ''))
        status = payload.get('status', 'UNKNOWN')
        
        return PaymentResult(
            success=status == 'SUCCESS',
            reference=order_id,
            provider_reference=payload.get('txnid'),
            status=status_mapping.get(status, 'unknown'),
            message=payload.get('message', ''),
            data=payload
        )
