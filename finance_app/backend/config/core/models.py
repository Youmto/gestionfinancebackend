"""
Core models - Base models and mixins for the application
"""

import uuid
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Modèle abstrait qui fournit les champs created_at et updated_at
    auto-gérés pour tous les modèles qui en héritent.
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de modification"
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


class UUIDModel(models.Model):
    """
    Modèle abstrait qui utilise UUID comme clé primaire.
    Plus sécurisé et adapté aux APIs RESTful.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID"
    )

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    """
    Modèle de base combinant UUID et timestamps.
    Tous les modèles principaux de l'application héritent de celui-ci.
    """

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Modèle abstrait pour la suppression douce (soft delete).
    Les enregistrements ne sont pas supprimés mais marqués comme supprimés.
    """
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Supprimé"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de suppression"
    )

    class Meta:
        abstract = True

    def soft_delete(self):
        """Marque l'enregistrement comme supprimé."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        """Restaure un enregistrement supprimé."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class SoftDeleteManager(models.Manager):
    """
    Manager personnalisé qui exclut les enregistrements supprimés par défaut.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """
    Manager qui inclut tous les enregistrements, y compris les supprimés.
    """
    pass


class SoftDeleteBaseModel(BaseModel, SoftDeleteModel):
    """
    Modèle de base avec soft delete intégré.
    Utiliser pour les données importantes qui ne doivent pas être perdues.
    """
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True


class NotificationLog(BaseModel):
    """
    Journal des notifications envoyées.
    
    Garde une trace de toutes les notifications (email, push, in-app)
    pour audit et débogage.
    """
    
    class NotificationType(models.TextChoices):
        EMAIL = 'email', 'Email'
        PUSH = 'push', 'Push'
        IN_APP = 'in_app', 'In-App'
    
    class NotificationStatus(models.TextChoices):
        PENDING = 'pending', 'En attente'
        SENT = 'sent', 'Envoyée'
        FAILED = 'failed', 'Échec'
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notification_logs',
        verbose_name="Utilisateur"
    )
    type = models.CharField(
        max_length=10,
        choices=NotificationType.choices,
        default=NotificationType.EMAIL,
        verbose_name="Type"
    )
    subject = models.CharField(
        max_length=200,
        verbose_name="Sujet"
    )
    content = models.TextField(
        verbose_name="Contenu"
    )
    
    # Référence à l'objet lié (polymorphisme simple)
    related_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Type d'objet lié"
    )
    related_id = models.UUIDField(
        blank=True,
        null=True,
        verbose_name="ID de l'objet lié"
    )
    
    status = models.CharField(
        max_length=10,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        verbose_name="Statut"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Message d'erreur"
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'envoi"
    )
    
    class Meta:
        db_table = 'notification_logs'
        verbose_name = "Log de notification"
        verbose_name_plural = "Logs de notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['type', 'status']),
            models.Index(fields=['related_type', 'related_id']),
        ]
    
    def __str__(self):
        return f"{self.type} - {self.subject} ({self.status})"
    
    def mark_as_sent(self):
        """Marque la notification comme envoyée."""
        self.status = self.NotificationStatus.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at', 'updated_at'])
    
    def mark_as_failed(self, error_message=None):
        """Marque la notification comme échouée."""
        self.status = self.NotificationStatus.FAILED
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])