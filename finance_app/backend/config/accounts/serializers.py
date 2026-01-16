"""
Accounts serializers - User and authentication serializers
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

# IMPORT CORRIGÉ - Suppression de EmailVerificationToken
from .models import User, PasswordResetToken, NotificationPreferences, EmailVerificationCode


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'inscription d'un nouvel utilisateur.
    """
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text="Minimum 8 caractères"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Confirmation du mot de passe"
    )
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 
            'password', 'password_confirm', 'currency'
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'currency': {'required': False, 'default': 'XAF'},
        }
    
    def validate_email(self, value):
        """Vérifie que l'email n'est pas déjà utilisé."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "Un compte existe déjà avec cette adresse email."
            )
        return value.lower()
    
    def validate_password(self, value):
        """Valide le mot de passe selon les règles Django."""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, attrs):
        """Vérifie que les mots de passe correspondent."""
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': "Les mots de passe ne correspondent pas."
            })
        return attrs
    
    def create(self, validated_data):
        """Crée l'utilisateur avec le mot de passe hashé."""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer pour la connexion.
    """
    
    email = serializers.EmailField(
        required=True,
        help_text="Adresse email"
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Mot de passe"
    )
    
    def validate(self, attrs):
        """Authentifie l'utilisateur."""
        email = attrs.get('email', '').lower()
        password = attrs.get('password', '')
        
        if not email or not password:
            raise serializers.ValidationError(
                "Email et mot de passe requis."
            )
        
        user = authenticate(
            request=self.context.get('request'),
            email=email,
            password=password
        )
        
        if not user:
            raise serializers.ValidationError(
                "Email ou mot de passe incorrect."
            )
        
        if not user.is_active:
            raise serializers.ValidationError(
                "Ce compte a été désactivé."
            )
        
        attrs['user'] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer pour le profil utilisateur.
    """
    
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'currency', 'avatar', 'is_verified', 
            'created_at', 'last_login'
        ]
        read_only_fields = ['id', 'email', 'is_verified', 'created_at', 'last_login']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour du profil.
    """
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'currency', 'avatar']
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'phone_number': {'required': False},
            'currency': {'required': False},
            'avatar': {'required': False},
        }


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer pour le changement de mot de passe.
    """
    
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="Mot de passe actuel"
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text="Nouveau mot de passe"
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirmation du nouveau mot de passe"
    )
    
    def validate_old_password(self, value):
        """Vérifie que l'ancien mot de passe est correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                "Le mot de passe actuel est incorrect."
            )
        return value
    
    def validate_new_password(self, value):
        """Valide le nouveau mot de passe."""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, attrs):
        """Vérifie que les nouveaux mots de passe correspondent."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Les mots de passe ne correspondent pas."
            })
        
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'new_password': "Le nouveau mot de passe doit être différent de l'ancien."
            })
        
        return attrs
    
    def save(self, **kwargs):
        """Change le mot de passe de l'utilisateur."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer pour la demande de réinitialisation de mot de passe.
    """
    
    email = serializers.EmailField(
        required=True,
        help_text="Adresse email du compte"
    )
    
    def validate_email(self, value):
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer pour la confirmation de réinitialisation de mot de passe.
    """
    
    token = serializers.CharField(
        required=True,
        help_text="Token de réinitialisation"
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text="Nouveau mot de passe"
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirmation du nouveau mot de passe"
    )
    
    def validate_token(self, value):
        """Vérifie que le token existe et est valide."""
        try:
            token = PasswordResetToken.objects.get(token=value)
            if not token.is_valid:
                raise serializers.ValidationError(
                    "Ce lien de réinitialisation a expiré ou a déjà été utilisé."
                )
            self.token_obj = token
            return value
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError(
                "Lien de réinitialisation invalide."
            )
    
    def validate_new_password(self, value):
        """Valide le nouveau mot de passe."""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, attrs):
        """Vérifie que les mots de passe correspondent."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Les mots de passe ne correspondent pas."
            })
        return attrs
    
    def save(self, **kwargs):
        """Réinitialise le mot de passe."""
        user = self.token_obj.user
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        
        self.token_obj.mark_as_used()
        
        return user


class ResendVerificationSerializer(serializers.Serializer):
    """
    Serializer pour renvoyer le code de vérification.
    """
    
    email = serializers.EmailField(
        required=True,
        help_text="Adresse email du compte"
    )
    
    def validate_email(self, value):
        """Vérifie que l'email existe et n'est pas déjà vérifié."""
        try:
            user = User.objects.get(email__iexact=value)
            if user.is_verified:
                raise serializers.ValidationError(
                    "Cette adresse email est déjà vérifiée."
                )
            self.user = user
            return value.lower()
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "Aucun compte trouvé avec cette adresse email."
            )
    
    def save(self, **kwargs):
        """Crée un nouveau code de vérification."""
        # Créer un nouveau code OTP
        verification = EmailVerificationCode.create_for_email(
            email=self.user.email,
            purpose='registration',
            user=self.user
        )
        return verification


class NotificationPreferencesSerializer(serializers.ModelSerializer):
    """
    Serializer pour les préférences de notification.
    """
    
    class Meta:
        model = NotificationPreferences
        fields = [
            'email_reminders',
            'email_group_activity',
            'email_weekly_summary',
            'email_budget_alerts',
            'email_payment_notifications',
            'push_enabled',
            'reminder_time'
        ]


class TokenResponseSerializer(serializers.Serializer):
    """
    Serializer pour la réponse avec tokens JWT.
    """
    
    access = serializers.CharField(help_text="Token d'accès JWT")
    refresh = serializers.CharField(help_text="Token de rafraîchissement JWT")
    user = UserProfileSerializer(help_text="Informations de l'utilisateur")


class UserMinimalSerializer(serializers.ModelSerializer):
    """
    Serializer minimal pour l'affichage d'un utilisateur.
    """
    
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'avatar']
        read_only_fields = fields


# ============================================================
# EMAIL VERIFICATION SERIALIZERS (OTP)
# ============================================================

class SendVerificationCodeSerializer(serializers.Serializer):
    """Serializer pour demander un code de vérification."""
    
    email = serializers.EmailField()
    purpose = serializers.ChoiceField(
        choices=['registration', 'login', 'password_reset', 'email_change'],
        default='registration'
    )
    
    def validate_email(self, value):
        return value.lower()
    
    def validate(self, attrs):
        """Validations croisées selon le purpose."""
        email = attrs['email']
        purpose = attrs['purpose']
        
        user_exists = User.objects.filter(email=email).exists()
        
        if purpose == 'registration' and user_exists:
            raise serializers.ValidationError({
                'email': "Un compte existe déjà avec cette adresse email."
            })
        
        if purpose in ['login', 'password_reset'] and not user_exists:
            raise serializers.ValidationError({
                'email': "Aucun compte trouvé avec cette adresse email."
            })
        
        return attrs


class VerifyCodeSerializer(serializers.Serializer):
    """Serializer pour vérifier un code OTP."""
    
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)
    purpose = serializers.ChoiceField(
        choices=['registration', 'login', 'password_reset', 'email_change']
    )
    
    def validate_email(self, value):
        return value.lower()
    
    def validate_code(self, value):
        """Vérifie que le code contient uniquement des chiffres."""
        if not value.isdigit():
            raise serializers.ValidationError("Le code doit contenir uniquement des chiffres.")
        return value


class RegisterWithCodeSerializer(serializers.Serializer):
    """Serializer pour l'inscription après vérification du code."""
    
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)
    password = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    
    def validate_email(self, value):
        return value.lower()
    
    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Le code doit contenir uniquement des chiffres.")
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Les mots de passe ne correspondent pas."
            })
        return attrs


class ResetPasswordWithCodeSerializer(serializers.Serializer):
    """Serializer pour réinitialiser le mot de passe avec un code."""
    
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)
    new_password_confirm = serializers.CharField(min_length=8, write_only=True)
    
    def validate_email(self, value):
        return value.lower()
    
    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Le code doit contenir uniquement des chiffres.")
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Les mots de passe ne correspondent pas."
            })
        return attrs


class ResendCodeSerializer(serializers.Serializer):
    """Serializer pour renvoyer un code."""
    
    email = serializers.EmailField()
    purpose = serializers.ChoiceField(
        choices=['registration', 'login', 'password_reset', 'email_change']
    )
    
    def validate_email(self, value):
        return value.lower()