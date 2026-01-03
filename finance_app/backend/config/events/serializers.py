"""
Events serializers - Event serializers
"""

from django.utils import timezone
from rest_framework import serializers

from accounts.serializers import UserMinimalSerializer
from finances.serializers import TransactionListSerializer
from reminders.serializers import ReminderListSerializer
from .models import Event


class EventSerializer(serializers.ModelSerializer):
    """
    Serializer pour les événements.
    
    Affiche les détails complets d'un événement avec les relations.
    """
    
    user_details = UserMinimalSerializer(source='user', read_only=True)
    transaction_details = TransactionListSerializer(source='transaction', read_only=True)
    reminder_details = ReminderListSerializer(source='reminder', read_only=True)
    duration = serializers.SerializerMethodField()
    is_past = serializers.ReadOnlyField()
    is_ongoing = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'user', 'user_details',
            'title', 'description',
            'start_date', 'end_date', 'all_day', 'color',
            'transaction', 'transaction_details',
            'reminder', 'reminder_details',
            'duration', 'is_past', 'is_ongoing', 'is_upcoming',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at'
        ]
    
    def get_duration(self, obj):
        """Retourne la durée en minutes."""
        duration = obj.duration
        if duration:
            return int(duration.total_seconds() / 60)
        return None


class EventCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création/modification d'événement.
    """
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'start_date', 'end_date',
            'all_day', 'color', 'transaction', 'reminder'
        ]
        extra_kwargs = {
            'description': {'required': False, 'default': ''},
            'end_date': {'required': False},
            'all_day': {'required': False, 'default': False},
            'color': {'required': False, 'default': '#3B82F6'},
            'transaction': {'required': False},
            'reminder': {'required': False},
        }
    
    def validate_title(self, value):
        """Vérifie que le titre n'est pas vide."""
        if not value.strip():
            raise serializers.ValidationError(
                "Le titre ne peut pas être vide."
            )
        return value.strip()
    
    def validate_color(self, value):
        """Vérifie que la couleur est valide."""
        if value and not value.startswith('#'):
            raise serializers.ValidationError(
                "La couleur doit être au format hexadécimal (#XXXXXX)."
            )
        if value and len(value) != 7:
            raise serializers.ValidationError(
                "La couleur doit être au format hexadécimal (#XXXXXX)."
            )
        return value
    
    def validate_transaction(self, value):
        """Vérifie que la transaction appartient à l'utilisateur."""
        if value:
            user = self.context['request'].user
            if value.user != user:
                raise serializers.ValidationError(
                    "Cette transaction ne vous appartient pas."
                )
        return value
    
    def validate_reminder(self, value):
        """Vérifie que le rappel appartient à l'utilisateur."""
        if value:
            user = self.context['request'].user
            if value.user != user:
                raise serializers.ValidationError(
                    "Ce rappel ne vous appartient pas."
                )
        return value
    
    def validate(self, attrs):
        """Validations croisées."""
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        all_day = attrs.get('all_day', False)
        
        # La date de fin doit être après la date de début
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': "La date de fin doit être après la date de début."
            })
        
        # Si événement toute la journée, ajuster les heures
        if all_day and start_date:
            attrs['start_date'] = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            if end_date:
                attrs['end_date'] = end_date.replace(hour=23, minute=59, second=59, microsecond=0)
        
        return attrs
    
    def create(self, validated_data):
        """Crée l'événement pour l'utilisateur connecté."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class EventUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour d'événement.
    """
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'start_date', 'end_date',
            'all_day', 'color'
        ]
        extra_kwargs = {
            'title': {'required': False},
            'description': {'required': False},
            'start_date': {'required': False},
            'end_date': {'required': False},
            'all_day': {'required': False},
            'color': {'required': False},
        }
    
    def validate_title(self, value):
        """Vérifie que le titre n'est pas vide."""
        if value is not None and not value.strip():
            raise serializers.ValidationError(
                "Le titre ne peut pas être vide."
            )
        return value.strip() if value else value


class EventListSerializer(serializers.ModelSerializer):
    """
    Serializer léger pour les listes d'événements.
    """
    
    is_past = serializers.ReadOnlyField()
    is_ongoing = serializers.ReadOnlyField()
    has_transaction = serializers.SerializerMethodField()
    has_reminder = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'start_date', 'end_date',
            'all_day', 'color',
            'is_past', 'is_ongoing',
            'has_transaction', 'has_reminder'
        ]
    
    def get_has_transaction(self, obj):
        """Retourne True si lié à une transaction."""
        return obj.transaction_id is not None
    
    def get_has_reminder(self, obj):
        """Retourne True si lié à un rappel."""
        return obj.reminder_id is not None


class CalendarEventSerializer(serializers.ModelSerializer):
    """
    Serializer optimisé pour l'affichage calendrier.
    """
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'start_date', 'end_date',
            'all_day', 'color'
        ]


class CalendarQuerySerializer(serializers.Serializer):
    """
    Serializer pour les paramètres de requête du calendrier.
    """
    
    year = serializers.IntegerField(
        required=True,
        min_value=2000,
        max_value=2100,
        help_text="Année"
    )
    month = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=12,
        help_text="Mois (1-12)"
    )


class DateQuerySerializer(serializers.Serializer):
    """
    Serializer pour les paramètres de requête par date.
    """
    
    date = serializers.DateField(
        required=True,
        help_text="Date au format YYYY-MM-DD"
    )


class UpcomingEventsSerializer(serializers.Serializer):
    """
    Serializer pour la liste des événements à venir.
    """
    
    days = serializers.IntegerField(
        required=False,
        default=7,
        min_value=1,
        max_value=365,
        help_text="Nombre de jours à regarder"
    )


class EventFilterSerializer(serializers.Serializer):
    """
    Serializer pour les filtres d'événements.
    """
    
    date_from = serializers.DateTimeField(
        required=False,
        help_text="Date de début"
    )
    date_to = serializers.DateTimeField(
        required=False,
        help_text="Date de fin"
    )
    all_day = serializers.BooleanField(
        required=False,
        help_text="Événements journée entière seulement"
    )
    has_transaction = serializers.BooleanField(
        required=False,
        help_text="Événements liés à une transaction"
    )
    has_reminder = serializers.BooleanField(
        required=False,
        help_text="Événements liés à un rappel"
    )
    color = serializers.CharField(
        required=False,
        help_text="Filtrer par couleur"
    )
    ordering = serializers.ChoiceField(
        choices=['start_date', '-start_date', 'created_at', '-created_at'],
        required=False,
        default='start_date',
        help_text="Tri des résultats"
    )
    search = serializers.CharField(
        required=False,
        help_text="Recherche dans le titre et la description"
    )


class CreateEventFromReminderSerializer(serializers.Serializer):
    """
    Serializer pour créer un événement à partir d'un rappel.
    """
    
    reminder_id = serializers.UUIDField(
        required=True,
        help_text="ID du rappel"
    )
    
    def validate_reminder_id(self, value):
        """Vérifie que le rappel existe et appartient à l'utilisateur."""
        from reminders.models import Reminder
        
        user = self.context['request'].user
        try:
            reminder = Reminder.objects.get(id=value, user=user)
            self.reminder = reminder
            return value
        except Reminder.DoesNotExist:
            raise serializers.ValidationError(
                "Rappel introuvable."
            )
    
    def create(self, validated_data):
        """Crée l'événement à partir du rappel."""
        return Event.create_from_reminder(self.reminder)


class CreateEventFromTransactionSerializer(serializers.Serializer):
    """
    Serializer pour créer un événement à partir d'une transaction.
    """
    
    transaction_id = serializers.UUIDField(
        required=True,
        help_text="ID de la transaction"
    )
    
    def validate_transaction_id(self, value):
        """Vérifie que la transaction existe et appartient à l'utilisateur."""
        from finances.models import Transaction
        
        user = self.context['request'].user
        try:
            transaction = Transaction.objects.get(id=value, user=user, is_deleted=False)
            self.transaction = transaction
            return value
        except Transaction.DoesNotExist:
            raise serializers.ValidationError(
                "Transaction introuvable."
            )
    
    def create(self, validated_data):
        """Crée l'événement à partir de la transaction."""
        return Event.create_from_transaction(self.transaction)