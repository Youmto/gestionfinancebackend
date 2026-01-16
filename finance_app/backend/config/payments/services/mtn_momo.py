# payments/services/mtn_momo.py
# Service de paiement MTN Mobile Money

import requests
import uuid
import hashlib
import hmac
import json
import base64
import logging
from typing import Dict
from decimal import Decimal
from datetime import datetime, timedelta

from .base import BasePaymentService, PaymentResult

logger = logging.getLogger(__name__)


class MTNMoMoService(BasePaymentService):
    """
    Service de paiement MTN Mobile Money (MoMo).
    
    Documentation API MTN MoMo:
    - Sandbox: https://momodeveloper.mtn.com/
    - Collection API (recevoir de l'argent)
    - Disbursement API (envoyer de l'argent)
    
    IMPORTANT: Remplacez les configurations par celles fournies par MTN
    quand vous aurez accès à l'API.
    """
    
    provider_name = 'mtn_momo'
    
    # URLs par défaut
    SANDBOX_URL = "https://sandbox.momodeveloper.mtn.com"
    PRODUCTION_URL = "https://proxy.momoapi.mtn.com"
    
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
    
    @property
    def subscription_key(self) -> str:
        """Retourne la clé d'abonnement (Ocp-Apim-Subscription-Key)"""
        if self.provider and self.provider.config:
            return self.provider.config.get('subscription_key', '')
        return ''
    
    @property
    def target_environment(self) -> str:
        """Retourne l'environnement cible"""
        return 'sandbox' if self.is_sandbox else 'mtnuganda'  # À adapter selon le pays
    
    def _get_access_token(self, api_type: str = 'collection') -> str:
        """
        Obtient un token d'accès OAuth2 pour MTN MoMo.
        
        Args:
            api_type: 'collection' ou 'disbursement'
        """
        
        if not self.is_configured:
            logger.error("MTN MoMo non configuré")
            return None
        
        # Vérifier si le token est encore valide
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._access_token
        
        try:
            # Créer les credentials Base64
            credentials = base64.b64encode(
                f"{self.provider.api_key}:{self.provider.api_secret}".encode()
            ).decode()
            
            auth_url = f"{self.api_url}/{api_type}/token/"
            
            headers = {
                'Authorization': f'Basic {credentials}',
                'Ocp-Apim-Subscription-Key': self.subscription_key,
                'Content-Type': 'application/json'
            }
            
            # TODO: Décommenter quand l'API sera configurée
            """
            response = requests.post(auth_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data['access_token']
                self._token_expires_at = datetime.now() + timedelta(seconds=data.get('expires_in', 3600))
                return self._access_token
            else:
                logger.error(f"Erreur auth MTN: {response.status_code} - {response.text}")
                return None
            """
            
            logger.warning("MTN MoMo: Authentification non implémentée")
            return None
            
        except Exception as e:
            logger.error(f"Erreur authentification MTN: {e}")
            return None
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        api_type: str = 'collection',
        reference_id: str = None
    ) -> Dict:
        """Effectue une requête à l'API MTN MoMo"""
        
        token = self._get_access_token(api_type)
        if not token:
            return {'error': 'Impossible d\'obtenir le token d\'accès'}
        
        url = f"{self.api_url}/{api_type}/v1_0/{endpoint}"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'X-Target-Environment': self.target_environment,
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Content-Type': 'application/json'
        }
        
        # Ajouter le X-Reference-Id pour les requêtes de paiement
        if reference_id:
            headers['X-Reference-Id'] = reference_id
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                return {'error': f'Méthode HTTP non supportée: {method}'}
            
            # MTN retourne 202 pour les requêtes asynchrones
            if response.status_code in [200, 202]:
                if response.content:
                    return response.json()
                return {'status_code': response.status_code}
            else:
                return {
                    'error': f'Erreur {response.status_code}',
                    'details': response.text
                }
            
        except requests.exceptions.Timeout:
            return {'error': 'Timeout de la requête'}
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}
        except json.JSONDecodeError:
            return {'status_code': response.status_code}
    
    def initiate_deposit(
        self,
        phone_number: str,
        amount: Decimal,
        reference: str,
        description: str = ""
    ) -> PaymentResult:
        """
        Initie une demande de paiement (Request to Pay).
        
        Le client recevra une notification sur son téléphone pour confirmer.
        """
        
        if not self.is_configured:
            return PaymentResult(
                success=False,
                reference=reference,
                status='failed',
                message="MTN MoMo non configuré. Veuillez contacter l'administrateur."
            )
        
        phone = self.format_phone_number(phone_number)
        
        # Générer un UUID pour cette transaction
        x_reference_id = str(uuid.uuid4())
        
        # Structure de la requête MTN MoMo
        payload = {
            'amount': str(int(amount)),  # MTN attend un entier
            'currency': 'XAF',
            'externalId': reference,
            'payer': {
                'partyIdType': 'MSISDN',
                'partyId': phone
            },
            'payerMessage': description or f"Paiement {reference}",
            'payeeNote': f"Ref: {reference}"
        }
        
        self.log_transaction('DEPOSIT_INIT', reference, {'phone': phone, 'amount': str(amount)})
        
        # TODO: Décommenter quand l'API sera configurée
        """
        response = self._make_request(
            'POST',
            'requesttopay',
            payload,
            api_type='collection',
            reference_id=x_reference_id
        )
        
        if 'error' in response:
            return PaymentResult(
                success=False,
                reference=reference,
                status='failed',
                message=response['error']
            )
        
        # MTN retourne 202 Accepted pour une requête réussie
        return PaymentResult(
            success=True,
            reference=reference,
            provider_reference=x_reference_id,
            status='pending',
            message='Paiement initié. Veuillez confirmer sur votre téléphone.',
            data={
                'x_reference_id': x_reference_id
            }
        )
        """
        
        # Simulation pour le développement
        return PaymentResult(
            success=True,
            reference=reference,
            provider_reference=x_reference_id,
            status='pending',
            message='[SIMULATION] Paiement MTN initié. En attente de configuration API.',
            data={
                'simulation': True,
                'x_reference_id': x_reference_id,
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
        Initie un transfert (envoi d'argent au client).
        
        Utilise l'API Disbursement de MTN MoMo.
        """
        
        if not self.is_configured:
            return PaymentResult(
                success=False,
                reference=reference,
                status='failed',
                message="MTN MoMo non configuré."
            )
        
        phone = self.format_phone_number(phone_number)
        x_reference_id = str(uuid.uuid4())
        
        # Structure pour le disbursement
        payload = {
            'amount': str(int(amount)),
            'currency': 'XAF',
            'externalId': reference,
            'payee': {
                'partyIdType': 'MSISDN',
                'partyId': phone
            },
            'payerMessage': description or f"Transfert {reference}",
            'payeeNote': f"Vous avez reçu {amount} XAF"
        }
        
        self.log_transaction('WITHDRAWAL_INIT', reference, {'phone': phone, 'amount': str(amount)})
        
        # Simulation
        return PaymentResult(
            success=True,
            reference=reference,
            provider_reference=x_reference_id,
            status='pending',
            message='[SIMULATION] Transfert MTN initié. En attente de configuration API.',
            data={
                'simulation': True,
                'x_reference_id': x_reference_id,
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
                message="MTN MoMo non configuré."
            )
        
        # TODO: Implémenter la vérification du statut
        """
        # Pour collection (requesttopay)
        response = self._make_request(
            'GET',
            f'requesttopay/{reference}',
            api_type='collection'
        )
        
        if 'error' in response:
            return PaymentResult(
                success=False,
                reference=reference,
                status='unknown',
                message=response['error']
            )
        
        status_mapping = {
            'PENDING': 'pending',
            'SUCCESSFUL': 'completed',
            'FAILED': 'failed'
        }
        
        return PaymentResult(
            success=response.get('status') == 'SUCCESSFUL',
            reference=reference,
            provider_reference=response.get('financialTransactionId'),
            status=status_mapping.get(response.get('status'), 'unknown'),
            message=response.get('reason', ''),
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
        """Vérifie la signature d'un webhook MTN MoMo"""
        
        # MTN utilise une signature HMAC-SHA256
        # TODO: Implémenter selon la documentation MTN
        
        return True  # À remplacer par la vraie vérification
    
    def process_webhook(self, payload: Dict) -> PaymentResult:
        """Traite un webhook MTN MoMo"""
        
        # Structure du callback MTN
        """
        {
            "financialTransactionId": "xxx",
            "externalId": "PAY-xxx",
            "amount": "1000",
            "currency": "XAF",
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": "237xxxxxxxxx"
            },
            "status": "SUCCESSFUL",
            "reason": null
        }
        """
        
        status_mapping = {
            'SUCCESSFUL': 'completed',
            'FAILED': 'failed',
            'PENDING': 'processing',
            'REJECTED': 'failed'
        }
        
        external_id = payload.get('externalId', '')
        status = payload.get('status', 'UNKNOWN')
        
        return PaymentResult(
            success=status == 'SUCCESSFUL',
            reference=external_id,
            provider_reference=payload.get('financialTransactionId'),
            status=status_mapping.get(status, 'unknown'),
            message=payload.get('reason') or '',
            data=payload
        )
    
    def get_account_balance(self) -> Dict:
        """Récupère le solde du compte MTN MoMo"""
        
        if not self.is_configured:
            return {'error': 'Non configuré'}
        
        # TODO: Implémenter
        """
        response = self._make_request('GET', 'account/balance', api_type='collection')
        return response
        """
        
        return {'simulation': True, 'balance': 'N/A'}
