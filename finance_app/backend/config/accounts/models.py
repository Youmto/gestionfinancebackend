"""
Accounts models - User and authentication related models
"""

import uuid
import secrets
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from core.models import BaseModel, TimeStampedModel


class UserManager(BaseUserManager):
    """
    Manager personnalisé pour le modèle User.
    Gère la création des utilisateurs et superutilisateurs.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Crée et sauvegarde un utilisateur avec l'email et le mot de passe donnés.
        """
        if not email:
            raise ValueError("L'adresse email est obligatoire")
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Crée et sauvegarde un superutilisateur avec l'email et le mot de passe donnés.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superutilisateur doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superutilisateur doit avoir is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Modèle utilisateur personnalisé utilisant l'email comme identifiant unique.
    
    Attributs:
        - id: UUID comme clé primaire
        - email: Adresse email unique
        - first_name: Prénom
        - last_name: Nom de famille
        - currency: Devise préférée (EUR par défaut)
        - avatar: URL de l'avatar
        - is_active: Compte actif
        - is_verified: Email vérifié
        - is_staff: Accès admin
    """
    
    CURRENCY_CHOICES = [
        ('EUR', 'Euro (€)'),
        ('USD', 'Dollar US ($)'),
        ('GBP', 'Livre Sterling (£)'),
        ('CHF', 'Franc Suisse (CHF)'),
        ('CAD', 'Dollar Canadien (CA$)'),
        ('XAF', 'Franc CFA CEMAC (FCFA)'),
        ('XOF', 'Franc CFA UEMOA (CFA)'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID"
    )
    email = models.EmailField(
        unique=True,
        max_length=255,
        verbose_name="Adresse email"
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name="Prénom"
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name="Nom"
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='EUR',
        verbose_name="Devise préférée"
    )
    avatar = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Avatar"
    )
    
    # Status fields
    is_active = models.BooleanField(
        default=True,
        verbose_name="Compte actif"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Email vérifié"
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Accès administration"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de modification"
    )
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Dernière connexion"
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        """Retourne le nom complet de l'utilisateur."""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Retourne le prénom de l'utilisateur."""
        return self.first_name
    
    def get_full_name(self):
        """Retourne le nom complet de l'utilisateur."""
        return self.full_name


class EmailVerificationToken(BaseModel):
    """
    Token de vérification d'email.
    Envoyé par email lors de l'inscription ou du changement d'email.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='verification_tokens',
        verbose_name="Utilisateur"
    )
    token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Token"
    )
    expires_at = models.DateTimeField(
        verbose_name="Date d'expiration"
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name="Utilisé"
    )
    
    class Meta:
        db_table = 'email_verification_tokens'
        verbose_name = "Token de vérification"
        verbose_name_plural = "Tokens de vérification"
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'is_used']),
        ]
    
    def __str__(self):
        return f"Verification token for {self.user.email}"
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        """Vérifie si le token est encore valide."""
        return not self.is_used and self.expires_at > timezone.now()
    
    def mark_as_used(self):
        """Marque le token comme utilisé."""
        self.is_used = True
        self.save(update_fields=['is_used', 'updated_at'])


class PasswordResetToken(BaseModel):
    """
    Token de réinitialisation de mot de passe.
    Généré lorsqu'un utilisateur demande à réinitialiser son mot de passe.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        verbose_name="Utilisateur"
    )
    token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Token"
    )
    expires_at = models.DateTimeField(
        verbose_name="Date d'expiration"
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name="Utilisé"
    )
    
    class Meta:
        db_table = 'password_reset_tokens'
        verbose_name = "Token de réinitialisation"
        verbose_name_plural = "Tokens de réinitialisation"
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'is_used']),
        ]
    
    def __str__(self):
        return f"Password reset token for {self.user.email}"
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            hours = getattr(settings, 'APP_SETTINGS', {}).get('PASSWORD_RESET_EXPIRY_HOURS', 24)
            self.expires_at = timezone.now() + timedelta(hours=hours)
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        """Vérifie si le token est encore valide."""
        return not self.is_used and self.expires_at > timezone.now()
    
    def mark_as_used(self):
        """Marque le token comme utilisé."""
        self.is_used = True
        self.save(update_fields=['is_used', 'updated_at'])


class NotificationPreferences(BaseModel):
    """
    Préférences de notification de l'utilisateur.
    Contrôle quels types de notifications l'utilisateur souhaite recevoir.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name="Utilisateur"
    )
    
    # Email notifications
    email_reminders = models.BooleanField(
        default=True,
        verbose_name="Rappels par email"
    )
    email_group_activity = models.BooleanField(
        default=True,
        verbose_name="Activité de groupe par email"
    )
    email_weekly_summary = models.BooleanField(
        default=True,
        verbose_name="Résumé hebdomadaire par email"
    )
    
    # Push notifications (pour usage futur)
    push_enabled = models.BooleanField(
        default=False,
        verbose_name="Notifications push activées"
    )
    
    class Meta:
        db_table = 'notification_preferences'
        verbose_name = "Préférences de notification"
        verbose_name_plural = "Préférences de notification"
    
    def __str__(self):
        return f"Notification preferences for {self.user.email}"