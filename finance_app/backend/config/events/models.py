"""
Events models - Event model for calendar and planning
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.models import BaseModel


class Event(BaseModel):
    """
    Événement du calendrier/planificateur.
    
    Peut être lié à une transaction ou un rappel.
    Affiché dans la vue calendrier mensuelle.
    
    Attributs:
        - user: Créateur de l'événement
        - title: Titre de l'événement
        - description: Description détaillée
        - start_date: Date/heure de début
        - end_date: Date/heure de fin (optionnel)
        - all_day: Événement sur journée entière
        - color: Couleur d'affichage
        - transaction: Transaction liée (optionnel)
        - reminder: Rappel lié (optionnel)
    """
    
    # Couleurs prédéfinies pour les événements
    COLOR_CHOICES = [
        ('#3B82F6', 'Bleu'),
        ('#EF4444', 'Rouge'),
        ('#10B981', 'Vert'),
        ('#F59E0B', 'Orange'),
        ('#8B5CF6', 'Violet'),
        ('#EC4899', 'Rose'),
        ('#14B8A6', 'Turquoise'),
        ('#6B7280', 'Gris'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name="Utilisateur"
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
    start_date = models.DateTimeField(
        verbose_name="Date de début"
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de fin"
    )
    all_day = models.BooleanField(
        default=False,
        verbose_name="Journée entière"
    )
    color = models.CharField(
        max_length=7,
        choices=COLOR_CHOICES,
        default='#3B82F6',
        verbose_name="Couleur"
    )
    
    # Relations optionnelles
    transaction = models.ForeignKey(
        'finances.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        verbose_name="Transaction liée"
    )
    reminder = models.ForeignKey(
        'reminders.Reminder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        verbose_name="Rappel lié"
    )
    
    class Meta:
        db_table = 'events'
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ['start_date']
        indexes = [
            models.Index(fields=['user', 'start_date']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.start_date.strftime('%d/%m/%Y')}"
    
    def clean(self):
        """Validations métier."""
        # La date de fin doit être après la date de début
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({
                'end_date': "La date de fin doit être après la date de début."
            })
        
        # Si journée entière, les heures sont à minuit
        if self.all_day:
            self.start_date = self.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            if self.end_date:
                self.end_date = self.end_date.replace(hour=23, minute=59, second=59, microsecond=0)
    
    @property
    def duration(self):
        """Retourne la durée de l'événement."""
        if not self.end_date:
            return None
        return self.end_date - self.start_date
    
    @property
    def is_past(self):
        """True si l'événement est passé."""
        end = self.end_date or self.start_date
        return end < timezone.now()
    
    @property
    def is_ongoing(self):
        """True si l'événement est en cours."""
        now = timezone.now()
        end = self.end_date or self.start_date
        return self.start_date <= now <= end
    
    @property
    def is_upcoming(self):
        """True si l'événement est à venir."""
        return self.start_date > timezone.now()
    
    @classmethod
    def get_calendar_events(cls, user, year, month):
        """
        Retourne les événements pour un mois donné (vue calendrier).
        
        Args:
            user: L'utilisateur
            year: Année
            month: Mois (1-12)
        
        Returns:
            QuerySet: Événements du mois
        """
        from datetime import datetime
        from calendar import monthrange
        
        # Premier et dernier jour du mois
        first_day = datetime(year, month, 1, tzinfo=timezone.get_current_timezone())
        last_day_num = monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59, tzinfo=timezone.get_current_timezone())
        
        # Événements qui sont dans le mois ou qui le chevauchent
        return cls.objects.filter(
            user=user
        ).filter(
            models.Q(start_date__range=(first_day, last_day)) |
            models.Q(end_date__range=(first_day, last_day)) |
            models.Q(start_date__lte=first_day, end_date__gte=last_day)
        ).order_by('start_date')
    
    @classmethod
    def get_date_events(cls, user, date):
        """
        Retourne les événements pour une date spécifique.
        
        Args:
            user: L'utilisateur
            date: Date (datetime.date ou datetime.datetime)
        
        Returns:
            QuerySet: Événements de la date
        """
        from datetime import datetime, time
        
        if hasattr(date, 'date'):
            date = date.date()
        
        start_of_day = datetime.combine(date, time.min).replace(tzinfo=timezone.get_current_timezone())
        end_of_day = datetime.combine(date, time.max).replace(tzinfo=timezone.get_current_timezone())
        
        return cls.objects.filter(
            user=user
        ).filter(
            models.Q(start_date__range=(start_of_day, end_of_day)) |
            models.Q(end_date__range=(start_of_day, end_of_day)) |
            models.Q(start_date__lte=start_of_day, end_date__gte=end_of_day)
        ).order_by('start_date')
    
    @classmethod
    def get_upcoming_events(cls, user, days=7):
        """
        Retourne les événements à venir pour un utilisateur.
        
        Args:
            user: L'utilisateur
            days: Nombre de jours à regarder
        
        Returns:
            QuerySet: Événements à venir
        """
        now = timezone.now()
        end_date = now + timezone.timedelta(days=days)
        
        return cls.objects.filter(
            user=user,
            start_date__gte=now,
            start_date__lte=end_date
        ).order_by('start_date')
    
    @classmethod
    def create_from_reminder(cls, reminder):
        """
        Crée un événement à partir d'un rappel.
        
        Args:
            reminder: Le rappel source
        
        Returns:
            Event: L'événement créé
        """
        return cls.objects.create(
            user=reminder.user,
            title=reminder.title,
            description=reminder.description,
            start_date=reminder.reminder_date,
            all_day=False,
            color='#EF4444',  # Rouge pour les rappels
            reminder=reminder
        )
    
    @classmethod
    def create_from_transaction(cls, transaction):
        """
        Crée un événement à partir d'une transaction.
        
        Args:
            transaction: La transaction source
        
        Returns:
            Event: L'événement créé
        """
        from datetime import datetime
        
        # Convertir la date en datetime
        start = datetime.combine(
            transaction.date,
            datetime.min.time()
        ).replace(tzinfo=timezone.get_current_timezone())
        
        # Couleur selon le type
        color = '#10B981' if transaction.type == 'income' else '#EF4444'
        
        return cls.objects.create(
            user=transaction.user,
            title=f"{transaction.category.name}: {transaction.amount}",
            description=transaction.description,
            start_date=start,
            all_day=True,
            color=color,
            transaction=transaction
        )