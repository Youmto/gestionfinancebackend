# payments/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PaymentProviderViewSet,
    UserPaymentMethodViewSet,
    PaymentViewSet,
    DepositView,
    WithdrawalView,
    TransferView,
    WalletView,
    WalletTransactionsView,
    WebhookView
)

router = DefaultRouter()
router.register(r'providers', PaymentProviderViewSet, basename='payment-providers')
router.register(r'methods', UserPaymentMethodViewSet, basename='payment-methods')
router.register(r'', PaymentViewSet, basename='payments')

urlpatterns = [
    # Opérations de paiement
    path('deposit/', DepositView.as_view(), name='payment-deposit'),
    path('withdraw/', WithdrawalView.as_view(), name='payment-withdraw'),
    path('transfer/', TransferView.as_view(), name='payment-transfer'),
    
    # Portefeuille
    path('wallet/', WalletView.as_view(), name='wallet'),
    path('wallet/transactions/', WalletTransactionsView.as_view(), name='wallet-transactions'),
    
    # Webhooks
    path('webhook/<str:provider_name>/', WebhookView.as_view(), name='payment-webhook'),
    
    # Router
    path('', include(router.urls)),
]
