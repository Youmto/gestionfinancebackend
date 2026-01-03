"""
Reminders serializers - Reminder serializers
"""

from django.utils import timezone
from rest_framework import serializers

from accounts.serializers import UserMinimalSerializer
from groups.serializers import GroupListSerializer
from .models import Reminder


class ReminderSerializer(serializers.ModelSerializer):
    """
    Serializer pour les rappels.
    
    Affiche les détails complets d'un rappel.
    """
    
    user_details = UserMinimalSerializer(source='user', read_only=True)
    group_details = GroupListSerializer(source='group', read_only=True)
    is_personal = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    next_occurrence = serializers.SerializerMethodField()
    
    class Meta:
        model = Reminder
        fields = [
            'id', 'user', 'user_details',
            'group', 'group_details',
            'title', 'description', 'reminder_type',
            'reminder_date', 'amount',
            'is_recurring', 'recurring_config',
            'is_completed', 'completed_at',
            'notification_sent', 'notification_sent_at',
            'is_personal', 'is_overdue', 'is_upcoming',
            'next_occurrence',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'is_completed', 'completed_at',
            'notification_sent', 'notification_sent_at',
            'created_at', 'updated_at'
        ]
    
    def get_next_occurrence(self, obj):
        """Retourne la prochaine occurrence si récurrent."""
        next_date = obj.get_next_occurrence()
        return next_date.isoformat() if next_date else None


class ReminderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création/modification de rappel.
    """
    
    class Meta:
        model = Reminder
        fields = [
            'group', 'title', 'description', 'reminder_type',
            'reminder_date', 'amount', 'is_recurring', 'recurring_config'
        ]
        extra_kwargs = {
            'description': {'required': False, 'default': ''},
            'reminder_type': {'required': False, 'default': 'general'},
            'amount': {'required': False},
            'is_recurring': {'required': False, 'default': False},
            'recurring_config': {'required': False},
            'group': {'required': False},
        }
    
    def validate_title(self, value):
        """Vérifie que le titre n'est pas vide."""
        if not value.strip():
            raise serializers.ValidationError(
                "Le titre ne peut pas être vide."
            )
        return value.strip()
    
    def validate_reminder_date(self, value):
        """Vérifie que la date n'est pas dans le passé pour une création."""
        if not self.instance:  # Création seulement
            if value < timezone.now():
                raise serializers.ValidationError(
                    "La date du rappel ne peut pas être dans le passé."
                )
        return value
    
    def validate_amount(self, value):
        """Vérifie que le montant est positif si fourni."""
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Le montant doit être supérieur à 0."
            )
        return value
    
    def validate_group(self, value):
        """Vérifie que l'utilisateur est membre du groupe."""
        if value:
            user = self.context['request'].user
            if not value.is_member(user):
                raise serializers.ValidationError(
                    "Vous n'êtes pas membre de ce groupe."
                )
        return value
    
    def validate(self, attrs):
        """Validations croisées."""
        # Valider la configuration de récurrence
        if attrs.get('is_recurring'):
            config = attrs.get('recurring_config')
            if not config:
                raise serializers.ValidationError({
                    'recurring_config': "La configuration de récurrence est requise."
                })
            
            # Valider la structure de la config
            required_fields = ['frequency']
            for field in required_fields:
                if field not in config:
                    raise serializers.ValidationError({
                        'recurring_config': f"Le champ '{field}' est requis."
                    })
            
            valid_frequencies = ['daily', 'weekly', 'monthly', 'yearly']
            if config.get('frequency') not in valid_frequencies:
                raise serializers.ValidationError({
                    'recurring_config': f"La fréquence doit être l'une de: {', '.join(valid_frequencies)}"
                })
        
        return attrs
    
    def create(self, validated_data):
        """Crée le rappel pour l'utilisateur connecté."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ReminderUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour de rappel.
    """
    
    class Meta:
        model = Reminder
        fields = [
            'title', 'description', 'reminder_type',
            'reminder_date', 'amount', 'is_recurring', 'recurring_config'
        ]
        extra_kwargs = {
            'title': {'required': False},
            'description': {'required': False},
            'reminder_type': {'required': False},
            'reminder_date': {'required': False},
            'amount': {'required': False},
            'is_recurring': {'required': False},
            'recurring_config': {'required': False},
        }
    
    def validate_title(self, value):
        """Vérifie que le titre n'est pas vide."""
        if value is not None and not value.strip():
            raise serializers.ValidationError(
                "Le titre ne peut pas être vide."
            )
        return value.strip() if value else value


class ReminderListSerializer(serializers.ModelSerializer):
    """
    Serializer léger pour les listes de rappels.
    """
    
    is_overdue = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Reminder
        fields = [
            'id', 'title', 'reminder_type', 'reminder_date',
            'amount', 'is_recurring', 'is_completed',
            'is_overdue', 'is_upcoming',
            'group', 'group_name', 'created_at'
        ]


class CompleteReminderSerializer(serializers.Serializer):
    """
    Serializer pour marquer un rappel comme terminé.
    """
    
    create_next = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Créer la prochaine occurrence pour les rappels récurrents"
    )
    
    def save(self, **kwargs):
        """Marque le rappel comme terminé."""
        reminder = self.context['reminder']
        create_next = self.validated_data.get('create_next', True)
        
        reminder.mark_as_completed()
        
        # Créer la prochaine occurrence si récurrent
        next_reminder = None
        if reminder.is_recurring and create_next:
            next_reminder = reminder.create_next_occurrence()
        
        return {
            'reminder': reminder,
            'next_reminder': next_reminder
        }


class UpcomingRemindersSerializer(serializers.Serializer):
    """
    Serializer pour la liste des rappels à venir.
    """
    
    days = serializers.IntegerField(
        required=False,
        default=7,
        min_value=1,
        max_value=365,
        help_text="Nombre de jours à regarder"
    )


class ReminderFilterSerializer(serializers.Serializer):
    """
    Serializer pour les filtres de rappels.
    """
    
    reminder_type = serializers.ChoiceField(
        choices=['payment', 'bill', 'general'],
        required=False,
        help_text="Type de rappel"
    )
    group = serializers.UUIDField(
        required=False,
        help_text="ID du groupe"
    )
    is_completed = serializers.BooleanField(
        required=False,
        help_text="Rappels terminés"
    )
    is_overdue = serializers.BooleanField(
        required=False,
        help_text="Rappels en retard"
    )
    date_from = serializers.DateTimeField(
        required=False,
        help_text="Date de début"
    )
    date_to = serializers.DateTimeField(
        required=False,
        help_text="Date de fin"
    )
    ordering = serializers.ChoiceField(
        choices=['reminder_date', '-reminder_date', 'created_at', '-created_at'],
        required=False,
        default='reminder_date',
        help_text="Tri des résultats"
    )