"""
Reminders models - Reminder model for payment and bill reminders
"""

from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone

from core.models import BaseModel


class Reminder(BaseModel):
    """
    Rappel pour paiements, factures ou événements généraux.
    
    Peut être personnel (user_id only) ou de groupe (user_id + group_id).
    Envoie des notifications par email à l'heure prévue.
    
    Attributs:
        - user: Créateur du rappel
        - group: Groupe associé (NULL = rappel personnel)
        - title: Titre du rappel
        - description: Description détaillée
        - reminder_type: payment, bill, general
        - reminder_date: Date et heure du rappel
        - amount: Montant associé (optionnel)
        - is_recurring: Rappel récurrent
        - recurring_config: Configuration de récurrence (JSON)
        - is_completed: Rappel terminé
        - notification_sent: Email envoyé
    """
    
    class ReminderType(models.TextChoices):
        PAYMENT = 'payment', 'Paiement dû'
        BILL = 'bill', 'Facture'
        GENERAL = 'general', 'Général'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name="Utilisateur"
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reminders',
        verbose_name="Groupe"
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Titre"
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name="Description"
    )
    reminder_type = models.CharField(
        max_length=10,
        choices=ReminderType.choices,
        default=ReminderType.GENERAL,
        verbose_name="Type"
    )
    reminder_date = models.DateTimeField(
        verbose_name="Date du rappel"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant"
    )
    
    # Récurrence
    is_recurring = models.BooleanField(
        default=False,
        verbose_name="Récurrent"
    )
    recurring_config = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Configuration de récurrence",
        help_text="""
        Format JSON:
        {
            "frequency": "monthly",  // daily, weekly, monthly, yearly
            "interval": 1,           // tous les X périodes
            "end_date": "2025-12-31", // nullable = infini
            "day_of_month": 15       // pour monthly
        }
        """
    )
    
    # Statut
    is_completed = models.BooleanField(
        default=False,
        verbose_name="Terminé"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de completion"
    )
    notification_sent = models.BooleanField(
        default=False,
        verbose_name="Notification envoyée"
    )
    notification_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'envoi de notification"
    )
    
    class Meta:
        db_table = 'reminders'
        verbose_name = "Rappel"
        verbose_name_plural = "Rappels"
        ordering = ['reminder_date']
        indexes = [
            models.Index(fields=['user', 'reminder_date']),
            models.Index(fields=['group', 'reminder_date']),
            models.Index(fields=['reminder_date', 'notification_sent']),
            models.Index(fields=['is_completed', 'reminder_date']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.reminder_date.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def is_personal(self):
        """True si c'est un rappel personnel (pas de groupe)."""
        return self.group is None
    
    @property
    def is_overdue(self):
        """True si le rappel est en retard (date passée et non complété)."""
        return not self.is_completed and self.reminder_date < timezone.now()
    
    @property
    def is_upcoming(self):
        """True si le rappel est à venir dans les 24h."""
        now = timezone.now()
        return (
            not self.is_completed and 
            self.reminder_date > now and 
            self.reminder_date < now + timezone.timedelta(hours=24)
        )
    
    def mark_as_completed(self):
        """Marque le rappel comme terminé."""
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save(update_fields=['is_completed', 'completed_at', 'updated_at'])
    
    def mark_notification_sent(self):
        """Marque la notification comme envoyée."""
        self.notification_sent = True
        self.notification_sent_at = timezone.now()
        self.save(update_fields=['notification_sent', 'notification_sent_at', 'updated_at'])
    
    def reset(self):
        """Réinitialise le rappel (pour les rappels récurrents)."""
        self.is_completed = False
        self.completed_at = None
        self.notification_sent = False
        self.notification_sent_at = None
        self.save()
    
    def get_next_occurrence(self):
        """
        Calcule la prochaine occurrence pour un rappel récurrent.
        
        Returns:
            datetime: Date de la prochaine occurrence ou None si non récurrent
        """
        if not self.is_recurring or not self.recurring_config:
            return None
        
        from dateutil.relativedelta import relativedelta
        
        config = self.recurring_config
        frequency = config.get('frequency', 'monthly')
        interval = config.get('interval', 1)
        end_date = config.get('end_date')
        
        current_date = self.reminder_date
        
        # Calculer la prochaine date selon la fréquence
        if frequency == 'daily':
            next_date = current_date + relativedelta(days=interval)
        elif frequency == 'weekly':
            next_date = current_date + relativedelta(weeks=interval)
        elif frequency == 'monthly':
            next_date = current_date + relativedelta(months=interval)
            # Gérer le jour du mois spécifique
            day_of_month = config.get('day_of_month')
            if day_of_month:
                try:
                    next_date = next_date.replace(day=day_of_month)
                except ValueError:
                    # Si le jour n'existe pas dans ce mois, prendre le dernier jour
                    import calendar
                    last_day = calendar.monthrange(next_date.year, next_date.month)[1]
                    next_date = next_date.replace(day=last_day)
        elif frequency == 'yearly':
            next_date = current_date + relativedelta(years=interval)
        else:
            return None
        
        # Vérifier la date de fin
        if end_date:
            from datetime import datetime
            end = datetime.fromisoformat(end_date)
            if next_date.replace(tzinfo=None) > end:
                return None
        
        return next_date
    
    def create_next_occurrence(self):
        """
        Crée la prochaine occurrence d'un rappel récurrent.
        
        Returns:
            Reminder: Le nouveau rappel créé ou None si pas de prochaine occurrence
        """
        next_date = self.get_next_occurrence()
        if not next_date:
            return None
        
        return Reminder.objects.create(
            user=self.user,
            group=self.group,
            title=self.title,
            description=self.description,
            reminder_type=self.reminder_type,
            reminder_date=next_date,
            amount=self.amount,
            is_recurring=self.is_recurring,
            recurring_config=self.recurring_config,
        )
    
    @classmethod
    def get_pending_notifications(cls, minutes_ahead=60):
        """
        Retourne les rappels dont la notification doit être envoyée.
        
        Args:
            minutes_ahead: Envoyer les notifications X minutes avant
        
        Returns:
            QuerySet: Rappels à notifier
        """
        now = timezone.now()
        threshold = now + timezone.timedelta(minutes=minutes_ahead)
        
        return cls.objects.filter(
            is_completed=False,
            notification_sent=False,
            reminder_date__lte=threshold,
            reminder_date__gte=now
        ).select_related('user', 'group')
    
    @classmethod
    def get_user_upcoming(cls, user, days=7):
        """
        Retourne les rappels à venir pour un utilisateur.
        
        Args:
            user: L'utilisateur
            days: Nombre de jours à regarder
        
        Returns:
            QuerySet: Rappels à venir
        """
        now = timezone.now()
        end_date = now + timezone.timedelta(days=days)
        
        return cls.objects.filter(
            user=user,
            is_completed=False,
            reminder_date__gte=now,
            reminder_date__lte=end_date
        ).order_by('reminder_date')