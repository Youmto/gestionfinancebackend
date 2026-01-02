"""
Views for accounts app - Authentication and user management
"""

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import User, EmailVerificationToken, PasswordResetToken, NotificationPreferences
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    NotificationPreferencesSerializer,
)


class RegisterView(generics.CreateAPIView):
    """
    Inscription d'un nouvel utilisateur.
    
    Crée un compte utilisateur et envoie un email de vérification.
    """
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    @extend_schema(
        tags=['Authentication'],
        summary="Inscription utilisateur",
        description="Crée un nouveau compte utilisateur"
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Générer les tokens JWT
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'Compte créé avec succès. Vérifiez votre email.',
            'data': {
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    Connexion utilisateur.
    
    Authentifie l'utilisateur et retourne les tokens JWT.
    """
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer
    
    @extend_schema(
        tags=['Authentication'],
        summary="Connexion utilisateur",
        description="Authentifie un utilisateur et retourne les tokens JWT"
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(request, email=email, password=password)
        
        if user is None:
            return Response({
                'success': False,
                'error': {
                    'code': 'INVALID_CREDENTIALS',
                    'message': 'Email ou mot de passe incorrect'
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                'success': False,
                'error': {
                    'code': 'ACCOUNT_DISABLED',
                    'message': 'Ce compte a été désactivé'
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Mettre à jour last_login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Générer les tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'Connexion réussie',
            'data': {
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }
        })


class LogoutView(APIView):
    """
    Déconnexion utilisateur.
    
    Invalide le refresh token.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Authentication'],
        summary="Déconnexion",
        description="Invalide le refresh token de l'utilisateur"
    )
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'success': True,
                'message': 'Déconnexion réussie'
            })
        except Exception:
            return Response({
                'success': True,
                'message': 'Déconnexion réussie'
            })


class VerifyEmailView(APIView):
    """
    Vérification de l'adresse email.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Authentication'],
        summary="Vérifier l'email",
        description="Vérifie l'adresse email avec le token reçu"
    )
    def get(self, request, token):
        try:
            verification = EmailVerificationToken.objects.get(token=token)
            
            if not verification.is_valid:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'INVALID_TOKEN',
                        'message': 'Ce lien de vérification est invalide ou expiré'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Marquer l'email comme vérifié
            verification.user.is_verified = True
            verification.user.save(update_fields=['is_verified'])
            verification.mark_as_used()
            
            return Response({
                'success': True,
                'message': 'Email vérifié avec succès'
            })
            
        except EmailVerificationToken.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'TOKEN_NOT_FOUND',
                    'message': 'Token de vérification non trouvé'
                }
            }, status=status.HTTP_404_NOT_FOUND)


class ResendVerificationView(APIView):
    """
    Renvoyer l'email de vérification.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Authentication'],
        summary="Renvoyer la vérification",
        description="Envoie un nouveau lien de vérification par email"
    )
    def post(self, request):
        user = request.user
        
        if user.is_verified:
            return Response({
                'success': False,
                'error': {
                    'code': 'ALREADY_VERIFIED',
                    'message': 'Cet email est déjà vérifié'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Invalider les anciens tokens
        EmailVerificationToken.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Créer un nouveau token
        verification = EmailVerificationToken.objects.create(user=user)
        
        # TODO: Envoyer l'email de vérification
        # send_verification_email(user, verification.token)
        
        return Response({
            'success': True,
            'message': 'Email de vérification envoyé'
        })


class PasswordResetRequestView(APIView):
    """
    Demande de réinitialisation du mot de passe.
    """
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer
    
    @extend_schema(
        tags=['Authentication'],
        summary="Demander réinitialisation",
        description="Envoie un email pour réinitialiser le mot de passe"
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            
            # Invalider les anciens tokens
            PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
            
            # Créer un nouveau token
            reset_token = PasswordResetToken.objects.create(user=user)
            
            # TODO: Envoyer l'email de réinitialisation
            # send_password_reset_email(user, reset_token.token)
            
        except User.DoesNotExist:
            pass  # Ne pas révéler si l'email existe
        
        return Response({
            'success': True,
            'message': 'Si cet email existe, un lien de réinitialisation a été envoyé'
        })


class PasswordResetConfirmView(APIView):
    """
    Confirmation de réinitialisation du mot de passe.
    """
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer
    
    @extend_schema(
        tags=['Authentication'],
        summary="Confirmer réinitialisation",
        description="Réinitialise le mot de passe avec le token reçu"
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            
            if not reset_token.is_valid:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'INVALID_TOKEN',
                        'message': 'Ce lien de réinitialisation est invalide ou expiré'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Changer le mot de passe
            user = reset_token.user
            user.set_password(new_password)
            user.save()
            
            # Marquer le token comme utilisé
            reset_token.mark_as_used()
            
            return Response({
                'success': True,
                'message': 'Mot de passe réinitialisé avec succès'
            })
            
        except PasswordResetToken.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'TOKEN_NOT_FOUND',
                    'message': 'Token de réinitialisation non trouvé'
                }
            }, status=status.HTTP_404_NOT_FOUND)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Profil de l'utilisateur connecté.
    
    GET: Récupère le profil
    PATCH: Met à jour le profil
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return self.request.user
    
    @extend_schema(
        tags=['User'],
        summary="Mon profil",
        description="Récupère le profil de l'utilisateur connecté"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        tags=['User'],
        summary="Mettre à jour mon profil",
        description="Met à jour le profil de l'utilisateur connecté"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class ChangePasswordView(APIView):
    """
    Changement de mot de passe.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    
    @extend_schema(
        tags=['User'],
        summary="Changer le mot de passe",
        description="Change le mot de passe de l'utilisateur connecté"
    )
    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        # Vérifier l'ancien mot de passe
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({
                'success': False,
                'error': {
                    'code': 'INVALID_PASSWORD',
                    'message': 'Mot de passe actuel incorrect'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Changer le mot de passe
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'success': True,
            'message': 'Mot de passe changé avec succès'
        })


class NotificationPreferencesView(generics.RetrieveUpdateAPIView):
    """
    Préférences de notification de l'utilisateur.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationPreferencesSerializer
    
    def get_object(self):
        preferences, created = NotificationPreferences.objects.get_or_create(
            user=self.request.user
        )
        return preferences
    
    @extend_schema(
        tags=['User'],
        summary="Mes préférences de notification",
        description="Récupère les préférences de notification"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        tags=['User'],
        summary="Mettre à jour mes préférences",
        description="Met à jour les préférences de notification"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)