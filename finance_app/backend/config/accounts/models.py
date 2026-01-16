"""
Accounts models - User and authentication related models
"""

import uuid
import secrets
import random
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from core.models import BaseModel

class UserManager(BaseUserManager):
    """
    Manager personnalisé pour le modèle User.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire")
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
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
    """
    
    CURRENCY_CHOICES = [
        ('XAF', 'Franc CFA CEMAC (FCFA)'),
        ('XOF', 'Franc CFA UEMOA (CFA)'),
        ('EUR', 'Euro (€)'),
        ('USD', 'Dollar US ($)'),
        ('GBP', 'Livre Sterling (£)'),
        ('CHF', 'Franc Suisse (CHF)'),
        ('CAD', 'Dollar Canadien (CA$)'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    email = models.EmailField(
        unique=True,
        max_length=255,
        verbose_name="Adresse email"
    )
    first_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prénom"
    )
    last_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nom"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Téléphone"
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='XAF',
        verbose_name="Devise préférée"
    )
    avatar = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Avatar"
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="Compte actif")
    is_verified = models.BooleanField(default=False, verbose_name="Email vérifié")
    is_staff = models.BooleanField(default=False, verbose_name="Accès administration")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
    last_login = models.DateTimeField(null=True, blank=True, verbose_name="Dernière connexion")
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
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
        return f"{self.first_name} {self.last_name}".strip() or self.email
    
    def get_short_name(self):
        return self.first_name
    
    def get_full_name(self):
        return self.full_name


class EmailVerificationCode(models.Model):
    """
    Code de vérification OTP envoyé par email (6 chiffres).
    
    Utilisé pour:
    - Inscription (registration)
    - Connexion sans mot de passe (login)
    - Réinitialisation de mot de passe (password_reset)
    - Changement d'email (email_change)
    """
    
    class Purpose(models.TextChoices):
        REGISTRATION = 'registration', 'Inscription'
        LOGIN = 'login', 'Connexion'
        PASSWORD_RESET = 'password_reset', 'Réinitialisation mot de passe'
        EMAIL_CHANGE = 'email_change', 'Changement email'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='verification_codes'
    )
    email = models.EmailField(verbose_name="Email")
    code = models.CharField(max_length=6, verbose_name="Code OTP")
    purpose = models.CharField(
        max_length=20,
        choices=Purpose.choices,
        verbose_name="Objectif"
    )
    
    # Sécurité
    attempts = models.IntegerField(default=0, verbose_name="Tentatives")
    max_attempts = models.IntegerField(default=5, verbose_name="Max tentatives")
    is_used = models.BooleanField(default=False, verbose_name="Utilisé")
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="Expire le")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="Utilisé le")
    
    class Meta:
        db_table = 'email_verification_codes'
        verbose_name = "Code de vérification"
        verbose_name_plural = "Codes de vérification"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'purpose', 'is_used']),
            models.Index(fields=['code', 'email']),
        ]
    
    def __str__(self):
        return f"{self.email} - {self.purpose} - {'✓' if self.is_used else '✗'}"
    
    @classmethod
    def generate_code(cls) -> str:
        """Génère un code à 6 chiffres."""
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    @classmethod
    def create_for_email(cls, email: str, purpose: str, user=None, validity_minutes: int = 15):
        """Crée un nouveau code de vérification."""
        # Invalider les anciens codes
        cls.objects.filter(
            email=email,
            purpose=purpose,
            is_used=False
        ).update(is_used=True)
        
        code = cls.generate_code()
        expires_at = timezone.now() + timedelta(minutes=validity_minutes)
        
        return cls.objects.create(
            user=user,
            email=email,
            code=code,
            purpose=purpose,
            expires_at=expires_at,
            max_attempts=5
        )
    
    def is_valid(self) -> bool:
        """Vérifie si le code est encore valide."""
        if self.is_used:
            return False
        if self.attempts >= self.max_attempts:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True
    
    def verify(self, code: str) -> bool:
        """Vérifie le code fourni."""
        if not self.is_valid():
            return False
        
        self.attempts += 1
        
        if self.code == code:
            self.is_used = True
            self.used_at = timezone.now()
            self.save()
            return True
        
        self.save()
        return False
    
    @property
    def remaining_attempts(self) -> int:
        return max(0, self.max_attempts - self.attempts)
    
    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at


class PasswordResetToken(models.Model):
    """
    Token de réinitialisation de mot de passe (lien unique).
    Alternative aux codes OTP pour reset par lien.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token = models.CharField(max_length=100, unique=True, verbose_name="Token")
    is_used = models.BooleanField(default=False, verbose_name="Utilisé")
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="Expire le")
    used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'password_reset_tokens'
        verbose_name = "Token de réinitialisation"
        verbose_name_plural = "Tokens de réinitialisation"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {'✓' if self.is_used else '✗'}"
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    @classmethod
    def create_for_user(cls, user, validity_hours: int = 24):
        """Crée un token de réinitialisation."""
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        
        return cls.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(hours=validity_hours)
        )
    
    @property
    def is_valid(self) -> bool:
        if self.is_used:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True
    
    def mark_as_used(self):
        self.is_used = True
        self.used_at = timezone.now()
        self.save()


class NotificationPreferences(models.Model):
    """
    Préférences de notification de l'utilisateur.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email
    email_reminders = models.BooleanField(default=True, verbose_name="Rappels par email")
    email_weekly_summary = models.BooleanField(default=True, verbose_name="Résumé hebdomadaire")
    email_group_activity = models.BooleanField(default=True, verbose_name="Activité des groupes")
    email_budget_alerts = models.BooleanField(default=True, verbose_name="Alertes budget")
    email_payment_notifications = models.BooleanField(default=True, verbose_name="Notifications paiement")
    email_monthly_summary = models.BooleanField(default=True)
    # Push
    push_enabled = models.BooleanField(default=False, verbose_name="Notifications push")
    
    # Heure des rappels
    reminder_time = models.TimeField(default='09:00:00', verbose_name="Heure des rappels")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_preferences'
        verbose_name = "Préférences de notification"
        verbose_name_plural = "Préférences de notification"
    
    def __str__(self):
        return f"Préférences de {self.user.email}"