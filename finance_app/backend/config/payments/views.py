# payments/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.utils import timezone
from django.db import transaction

from .models import (
    PaymentProvider, UserPaymentMethod, Payment,
    PaymentWebhook, Wallet, WalletTransaction
)
from .serializers import (
    PaymentProviderSerializer, UserPaymentMethodSerializer,
    UserPaymentMethodCreateSerializer, PaymentSerializer,
    DepositSerializer, WithdrawalSerializer, TransferSerializer,
    WalletSerializer, WalletTransactionSerializer
)
from .services import get_payment_service


class PaymentProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API pour lister les fournisseurs de paiement disponibles.
    
    GET /api/v1/payments/providers/
    """
    
    queryset = PaymentProvider.objects.filter(is_active=True)
    serializer_class = PaymentProviderSerializer
    permission_classes = [IsAuthenticated]


class UserPaymentMethodViewSet(viewsets.ModelViewSet):
    """
    API pour gérer les méthodes de paiement de l'utilisateur.
    
    GET /api/v1/payments/methods/
    POST /api/v1/payments/methods/
    DELETE /api/v1/payments/methods/{id}/
    """
    
    serializer_class = UserPaymentMethodSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserPaymentMethod.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserPaymentMethodCreateSerializer
        return UserPaymentMethodSerializer
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Définir comme méthode par défaut"""
        method = self.get_object()
        method.is_default = True
        method.save()
        return Response({'message': 'Méthode définie par défaut'})


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API pour consulter l'historique des paiements.
    
    GET /api/v1/payments/
    GET /api/v1/payments/{id}/
    """
    
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Vérifier le statut d'un paiement"""
        payment = self.get_object()
        
        if payment.status in ['completed', 'failed', 'cancelled']:
            return Response({
                'status': payment.status,
                'message': 'Transaction terminée'
            })
        
        try:
            service = get_payment_service(payment.provider.name)
            result = service.check_status(payment.provider_reference or str(payment.reference))
            
            if result.status != payment.status:
                payment.status = result.status
                if result.status == 'completed':
                    payment.completed_at = timezone.now()
                payment.save()
            
            return Response({
                'status': payment.status,
                'message': result.message
            })
            
        except Exception as e:
            return Response({
                'status': payment.status,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DepositView(APIView):
    """
    Initier un dépôt (ajouter de l'argent au portefeuille).
    
    POST /api/v1/payments/deposit/
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = DepositSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        provider = data['provider_obj']
        
        # Calculer les frais
        fee = provider.calculate_fee(data['amount'])
        
        try:
            # Créer le paiement
            payment = Payment.objects.create(
                user=request.user,
                provider=provider,
                type='deposit',
                amount=data['amount'],
                fee=fee,
                total_amount=data['amount'] + fee,
                description=f"Dépôt via {provider.display_name}"
            )
            
            # Initier le paiement via le service
            service = get_payment_service(provider.name)
            result = service.initiate_deposit(
                phone_number=data['phone_number'],
                amount=data['amount'],
                reference=str(payment.reference),
                description=payment.description
            )
            
            if result.success:
                payment.provider_reference = result.provider_reference
                payment.status = result.status
                payment.provider_response = result.data
                payment.save()
                
                return Response({
                    'success': True,
                    'payment': PaymentSerializer(payment).data,
                    'message': result.message,
                    'data': result.data
                }, status=status.HTTP_201_CREATED)
            else:
                payment.status = 'failed'
                payment.error_message = result.message
                payment.save()
                
                return Response({
                    'success': False,
                    'message': result.message
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WithdrawalView(APIView):
    """
    Initier un retrait (retirer de l'argent du portefeuille).
    
    POST /api/v1/payments/withdraw/
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = WithdrawalSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        payment_method = data['payment_method_obj']
        provider = payment_method.provider
        
        # Calculer les frais
        fee = provider.calculate_fee(data['amount'])
        total = data['amount'] + fee
        
        try:
            with transaction.atomic():
                # Vérifier et débiter le portefeuille
                wallet = request.user.wallet
                wallet.debit(total, f"Retrait vers {payment_method.phone_number}")
                
                # Créer le paiement
                payment = Payment.objects.create(
                    user=request.user,
                    provider=provider,
                    payment_method=payment_method,
                    type='withdrawal',
                    amount=data['amount'],
                    fee=fee,
                    total_amount=total,
                    recipient_phone=payment_method.phone_number,
                    description=f"Retrait vers {payment_method.phone_number}"
                )
                
                # Initier le retrait via le service
                service = get_payment_service(provider.name)
                result = service.initiate_withdrawal(
                    phone_number=payment_method.phone_number,
                    amount=data['amount'],
                    reference=str(payment.reference),
                    description=payment.description
                )
                
                if result.success:
                    payment.provider_reference = result.provider_reference
                    payment.status = result.status
                    payment.provider_response = result.data
                    payment.save()
                    
                    return Response({
                        'success': True,
                        'payment': PaymentSerializer(payment).data,
                        'message': result.message
                    }, status=status.HTTP_201_CREATED)
                else:
                    # Rembourser en cas d'échec
                    wallet.credit(total, f"Remboursement retrait échoué")
                    payment.status = 'failed'
                    payment.error_message = result.message
                    payment.save()
                    
                    return Response({
                        'success': False,
                        'message': result.message
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
        except ValueError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TransferView(APIView):
    """
    Transférer de l'argent à un autre utilisateur.
    
    POST /api/v1/payments/transfer/
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = TransferSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            with transaction.atomic():
                sender_wallet = request.user.wallet
                
                # Rechercher le destinataire par numéro de téléphone
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                # Chercher dans les méthodes de paiement
                recipient_method = UserPaymentMethod.objects.filter(
                    phone_number=data['recipient_phone']
                ).first()
                
                recipient = recipient_method.user if recipient_method else None
                
                # Créer le paiement
                payment = Payment.objects.create(
                    user=request.user,
                    provider=PaymentProvider.objects.filter(is_active=True).first(),
                    type='transfer',
                    amount=data['amount'],
                    recipient=recipient,
                    recipient_phone=data['recipient_phone'],
                    description=data.get('description', f"Transfert vers {data['recipient_phone']}")
                )
                
                # Débiter l'expéditeur
                sender_wallet.debit(data['amount'], f"Transfert vers {data['recipient_phone']}")
                
                # Créditer le destinataire s'il est dans le système
                if recipient:
                    recipient_wallet, _ = Wallet.objects.get_or_create(user=recipient)
                    recipient_wallet.credit(
                        data['amount'],
                        f"Transfert reçu de {request.user.email}"
                    )
                    payment.status = 'completed'
                    payment.completed_at = timezone.now()
                else:
                    # Destinataire externe - initier un paiement mobile
                    payment.status = 'pending'
                    # TODO: Initier le paiement vers le numéro externe
                
                payment.save()
                
                return Response({
                    'success': True,
                    'payment': PaymentSerializer(payment).data,
                    'message': 'Transfert effectué avec succès'
                }, status=status.HTTP_201_CREATED)
                
        except ValueError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WalletView(APIView):
    """
    Consulter le portefeuille de l'utilisateur.
    
    GET /api/v1/payments/wallet/
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        
        # Récupérer les dernières transactions
        transactions = WalletTransaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')[:10]
        
        return Response({
            'wallet': WalletSerializer(wallet).data,
            'recent_transactions': WalletTransactionSerializer(transactions, many=True).data
        })


class WalletTransactionsView(APIView):
    """
    Historique des transactions du portefeuille.
    
    GET /api/v1/payments/wallet/transactions/
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            wallet = request.user.wallet
        except Wallet.DoesNotExist:
            return Response({'transactions': []})
        
        transactions = WalletTransaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')
        
        # Pagination simple
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        return Response({
            'count': transactions.count(),
            'transactions': WalletTransactionSerializer(
                transactions[start:end], many=True
            ).data
        })


class WebhookView(APIView):
    """
    Recevoir les webhooks des fournisseurs de paiement.
    
    POST /api/v1/payments/webhook/{provider}/
    """
    
    permission_classes = [AllowAny]  # Les webhooks viennent de l'extérieur
    
    def post(self, request, provider_name):
        # Récupérer le fournisseur
        try:
            provider = PaymentProvider.objects.get(name=provider_name)
        except PaymentProvider.DoesNotExist:
            return Response({'error': 'Provider inconnu'}, status=status.HTTP_404_NOT_FOUND)
        
        # Logger le webhook
        webhook = PaymentWebhook.objects.create(
            provider=provider,
            event_type=request.data.get('event', 'unknown'),
            payload=request.data,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        try:
            # Vérifier la signature
            signature = request.headers.get('X-Signature', '')
            service = get_payment_service(provider_name)
            
            if not service.verify_webhook(request.data, signature):
                webhook.is_processed = True
                webhook.save()
                return Response({'error': 'Signature invalide'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Traiter le webhook
            result = service.process_webhook(request.data)
            
            # Mettre à jour le paiement
            if result.reference:
                try:
                    payment = Payment.objects.get(reference=result.reference)
                    payment.status = result.status
                    payment.provider_response = result.data
                    
                    if result.status == 'completed':
                        payment.completed_at = timezone.now()
                        
                        # Créditer le portefeuille pour les dépôts
                        if payment.type == 'deposit':
                            wallet = payment.user.wallet
                            wallet.credit(payment.amount, f"Dépôt {payment.reference}")
                    
                    payment.save()
                    webhook.payment = payment
                    
                except Payment.DoesNotExist:
                    pass
            
            webhook.is_processed = True
            webhook.processed_at = timezone.now()
            webhook.save()
            
            return Response({'success': True})
            
        except Exception as e:
            webhook.is_processed = True
            webhook.save()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
