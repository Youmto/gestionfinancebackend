"""
Views pour la vérification par code email (OTP).
"""

from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

# IMPORTS CORRIGÉS
from core.services.email_service import EmailService
from .models import User, EmailVerificationCode, PasswordResetToken
from .serializers import (
    SendVerificationCodeSerializer,
    VerifyCodeSerializer,
    RegisterWithCodeSerializer,
    ResetPasswordWithCodeSerializer,
    ResendCodeSerializer,
    UserProfileSerializer
)


class SendVerificationCodeView(APIView):
    """
    POST /api/v1/auth/send-code/
    
    Envoie un code de vérification par email.
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Envoyer un code de vérification",
        description="Envoie un code OTP à 6 chiffres par email.",
        request=SendVerificationCodeSerializer,
        tags=['Authentification']
    )
    def post(self, request):
        serializer = SendVerificationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        purpose = serializer.validated_data['purpose']
        
        # Rate limiting: vérifier si un code récent existe
        recent_code = EmailVerificationCode.objects.filter(
            email=email,
            purpose=purpose,
            is_used=False,
            created_at__gte=timezone.now() - timedelta(minutes=1)
        ).first()
        
        if recent_code:
            wait_seconds = 60 - (timezone.now() - recent_code.created_at).seconds
            return Response({
                'error': 'Un code a déjà été envoyé. Veuillez attendre.',
                'retry_after': wait_seconds
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Récupérer l'utilisateur si existe
        user = User.objects.filter(email=email).first()
        
        # Créer le code
        validity_minutes = getattr(settings, 'OTP_VALIDITY_MINUTES', 15)
        verification = EmailVerificationCode.create_for_email(
            email=email,
            purpose=purpose,
            user=user,
            validity_minutes=validity_minutes
        )
        
        # Envoyer l'email
        email_sent = EmailService.send_verification_code(
            email=email,
            code=verification.code,
            purpose=purpose
        )
        
        if not email_sent:
            return Response({
                'error': "Erreur lors de l'envoi de l'email. Veuillez réessayer."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'message': 'Code de vérification envoyé avec succès.',
            'email': email,
            'expires_in': validity_minutes * 60,
            'purpose': purpose
        })


class VerifyCodeView(APIView):
    """
    POST /api/v1/auth/verify-code/
    
    Vérifie un code OTP.
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Vérifier un code",
        description="Vérifie le code OTP et retourne le résultat.",
        request=VerifyCodeSerializer,
        tags=['Authentification']
    )
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        purpose = serializer.validated_data['purpose']
        
        # Chercher le code
        verification = EmailVerificationCode.objects.filter(
            email=email,
            purpose=purpose,
            is_used=False
        ).order_by('-created_at').first()
        
        if not verification:
            return Response({
                'verified': False,
                'error': 'Aucun code valide trouvé. Veuillez en demander un nouveau.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if verification.is_expired:
            return Response({
                'verified': False,
                'error': 'Code expiré. Veuillez en demander un nouveau.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if verification.remaining_attempts <= 0:
            return Response({
                'verified': False,
                'error': 'Nombre maximum de tentatives atteint. Veuillez demander un nouveau code.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier le code
        if not verification.verify(code):
            return Response({
                'verified': False,
                'error': f'Code incorrect. {verification.remaining_attempts} tentative(s) restante(s).',
                'remaining_attempts': verification.remaining_attempts
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Code valide
        response_data = {
            'verified': True,
            'message': 'Code vérifié avec succès.',
            'email': email,
            'purpose': purpose
        }
        
        # Si c'est pour login, connecter directement
        if purpose == 'login':
            user = User.objects.get(email=email)
            refresh = RefreshToken.for_user(user)
            response_data['tokens'] = {
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }
            response_data['user'] = UserProfileSerializer(user).data
        
        # Si c'est pour password_reset, générer un token temporaire
        elif purpose == 'password_reset':
            user = User.objects.get(email=email)
            reset_token = PasswordResetToken.create_for_user(user)
            response_data['reset_token'] = reset_token.token
        
        # Si c'est pour registration, indiquer qu'on peut créer le compte
        elif purpose == 'registration':
            response_data['can_create_account'] = True
        
        return Response(response_data)


class RegisterWithCodeView(APIView):
    """
    POST /api/v1/auth/register-with-code/
    
    Crée un compte après vérification du code.
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Inscription avec code",
        description="Crée un compte après vérification du code OTP.",
        request=RegisterWithCodeSerializer,
        tags=['Authentification']
    )
    def post(self, request):
        serializer = RegisterWithCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        
        # Vérifier que l'email n'est pas déjà utilisé
        if User.objects.filter(email=email).exists():
            return Response({
                'error': 'Un compte existe déjà avec cette adresse email.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier le code
        verification = EmailVerificationCode.objects.filter(
            email=email,
            purpose='registration',
            is_used=False
        ).order_by('-created_at').first()
        
        if not verification:
            return Response({
                'error': 'Veuillez d\'abord demander un code de vérification.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not verification.verify(code):
            return Response({
                'error': 'Code incorrect ou expiré.',
                'remaining_attempts': verification.remaining_attempts
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Créer l'utilisateur
        user = User.objects.create_user(
            email=email,
            password=serializer.validated_data['password'],
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            is_verified=True
        )
        
        # Générer les tokens
        refresh = RefreshToken.for_user(user)
        
        # Envoyer l'email de bienvenue
        EmailService.send_welcome_email(user)
        
        return Response({
            'message': 'Compte créé avec succès.',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }
        }, status=status.HTTP_201_CREATED)


class ResetPasswordWithCodeView(APIView):
    """
    POST /api/v1/auth/reset-password-with-code/
    
    Réinitialise le mot de passe après vérification du code.
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Réinitialiser mot de passe avec code",
        description="Change le mot de passe après vérification du code OTP.",
        request=ResetPasswordWithCodeSerializer,
        tags=['Authentification']
    )
    def post(self, request):
        serializer = ResetPasswordWithCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        
        # Récupérer l'utilisateur
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'error': 'Utilisateur non trouvé.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Vérifier le code
        verification = EmailVerificationCode.objects.filter(
            email=email,
            purpose='password_reset',
            is_used=False
        ).order_by('-created_at').first()
        
        if not verification:
            return Response({
                'error': 'Veuillez d\'abord demander un code de vérification.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not verification.verify(code):
            return Response({
                'error': 'Code incorrect ou expiré.',
                'remaining_attempts': verification.remaining_attempts
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Changer le mot de passe
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Envoyer notification
        EmailService.send_password_changed_notification(user)
        
        return Response({
            'message': 'Mot de passe modifié avec succès. Vous pouvez maintenant vous connecter.'
        })


class ResendVerificationCodeView(APIView):
    """
    POST /api/v1/auth/resend-code/
    
    Renvoie un code de vérification.
    """
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Renvoyer un code",
        description="Renvoie un nouveau code de vérification.",
        request=ResendCodeSerializer,
        tags=['Authentification']
    )
    def post(self, request):
        serializer = ResendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        purpose = serializer.validated_data['purpose']
        
        # Rate limiting
        recent_code = EmailVerificationCode.objects.filter(
            email=email,
            purpose=purpose,
            created_at__gte=timezone.now() - timedelta(minutes=1)
        ).first()
        
        if recent_code:
            wait_seconds = 60 - (timezone.now() - recent_code.created_at).seconds
            return Response({
                'error': f'Veuillez attendre {wait_seconds} secondes.',
                'retry_after': wait_seconds
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Récupérer l'utilisateur si existe
        user = User.objects.filter(email=email).first()
        
        # Vérifications selon le purpose
        if purpose == 'registration' and user:
            return Response({
                'error': 'Un compte existe déjà avec cette adresse email.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if purpose in ['login', 'password_reset'] and not user:
            return Response({
                'error': 'Aucun compte trouvé avec cette adresse email.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Créer et envoyer le nouveau code
        validity_minutes = getattr(settings, 'OTP_VALIDITY_MINUTES', 15)
        verification = EmailVerificationCode.create_for_email(
            email=email,
            purpose=purpose,
            user=user,
            validity_minutes=validity_minutes
        )
        
        email_sent = EmailService.send_verification_code(
            email=email,
            code=verification.code,
            purpose=purpose
        )
        
        if not email_sent:
            return Response({
                'error': "Erreur lors de l'envoi de l'email."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'message': 'Nouveau code envoyé avec succès.',
            'email': email,
            'expires_in': validity_minutes * 60
        })