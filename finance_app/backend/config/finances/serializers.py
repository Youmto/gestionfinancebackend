"""
Finances serializers - Category, Transaction and ExpenseSplit serializers
"""

from decimal import Decimal
from django.db import models
from django.db.models import Sum, Case, When, DecimalField, Count
from django.utils import timezone
from rest_framework import serializers

from accounts.serializers import UserMinimalSerializer
from .models import Category, Transaction, ExpenseSplit


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer pour les catégories.
    
    Affiche les catégories système et personnalisées de l'utilisateur.
    Inclut le statut du budget si défini.
    """
    
    transaction_count = serializers.SerializerMethodField(
        help_text="Nombre de transactions dans cette catégorie"
    )
    budget_status = serializers.SerializerMethodField(
        help_text="Statut du budget mensuel"
    )
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'icon', 'color', 'type',
            'budget', 'budget_alert_threshold', 'budget_status',
            'is_system', 'transaction_count', 'created_at'
        ]
        read_only_fields = ['id', 'is_system', 'created_at', 'budget_status']
    
    def get_transaction_count(self, obj):
        """Retourne le nombre de transactions pour cette catégorie."""
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            return obj.transactions.filter(
                user=user,
                is_deleted=False
            ).count()
        return 0
    
    def get_budget_status(self, obj):
        """Retourne le statut du budget si défini."""
        return obj.get_budget_status()
    
    def validate_name(self, value):
        """Vérifie que le nom n'est pas déjà utilisé par l'utilisateur."""
        user = self.context['request'].user
        
        # Vérifier les catégories système
        if Category.objects.filter(
            name__iexact=value,
            is_system=True
        ).exists():
            raise serializers.ValidationError(
                "Une catégorie système porte déjà ce nom."
            )
        
        # Vérifier les catégories de l'utilisateur (exclure l'instance actuelle en cas d'update)
        queryset = Category.objects.filter(
            name__iexact=value,
            user=user
        )
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError(
                "Vous avez déjà une catégorie avec ce nom."
            )
        
        return value
    
    def validate_budget(self, value):
        """Vérifie que le budget est positif."""
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Le budget doit être positif."
            )
        return value
    
    def validate_budget_alert_threshold(self, value):
        """Vérifie que le seuil est entre 0 et 100."""
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Le seuil d'alerte doit être entre 0 et 100."
            )
        return value
    
    def create(self, validated_data):
        """Crée une catégorie personnalisée pour l'utilisateur."""
        validated_data['user'] = self.context['request'].user
        validated_data['is_system'] = False
        return super().create(validated_data)


class CategoryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création de catégorie.
    """
    
    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'description',
            'icon',
            'color',
            'type',
            'budget',
            'budget_alert_threshold'
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'icon': {'required': False, 'default': '📁'},
            'color': {'required': False, 'default': '#6B7280'},
            'type': {'required': False, 'default': 'expense'},
            'description': {'required': False},
            'budget': {'required': False},
            'budget_alert_threshold': {'required': False, 'default': 80},
        }
    
    def validate_budget(self, value):
        """Vérifie que le budget est positif."""
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Le budget doit être positif."
            )
        return value
    
    def validate_budget_alert_threshold(self, value):
        """Vérifie que le seuil est entre 0 et 100."""
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError(
                "Le seuil d'alerte doit être entre 0 et 100."
            )
        return value
    
    def create(self, validated_data):
        """Crée une catégorie personnalisée pour l'utilisateur."""
        validated_data['user'] = self.context['request'].user
        validated_data['is_system'] = False
        return super().create(validated_data)


class CategorySimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simplifié pour les listes déroulantes.
    """
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'color', 'type']


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer pour les transactions.
    
    Affiche les détails complets d'une transaction avec les relations.
    """
    
    category_details = CategorySimpleSerializer(source='category', read_only=True)
    user_details = UserMinimalSerializer(source='user', read_only=True)
    signed_amount = serializers.ReadOnlyField()
    is_personal = serializers.ReadOnlyField()
    splits_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'user_details', 'group',
            'category', 'category_details',
            'amount', 'signed_amount', 'type',
            'description', 'date',
            'is_recurring', 'recurring_config',
            'attachment', 'is_personal',
            'splits_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at'
        ]
    
    def get_splits_count(self, obj):
        """Retourne le nombre de partages pour cette transaction."""
        return obj.splits.count() if obj.group else 0


class TransactionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création/modification de transaction.
    """
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'category', 'group', 'amount', 'type',
            'description', 'date', 'is_recurring',
            'recurring_config', 'attachment'
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'description': {'required': False, 'default': ''},
            'date': {'required': True},
            'is_recurring': {'required': False, 'default': False},
            'recurring_config': {'required': False},
            'attachment': {'required': False},
            'group': {'required': False},
        }
    
    def validate_amount(self, value):
        """Vérifie que le montant est positif."""
        if value <= 0:
            raise serializers.ValidationError(
                "Le montant doit être supérieur à 0."
            )
        return value
    
    def validate_category(self, value):
        """Vérifie que la catégorie est accessible à l'utilisateur."""
        user = self.context['request'].user
        
        # La catégorie doit être système ou appartenir à l'utilisateur
        if not value.is_system and value.user != user:
            raise serializers.ValidationError(
                "Cette catégorie n'est pas disponible."
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
        category = attrs.get('category')
        transaction_type = attrs.get('type')
        
        # Vérifier la compatibilité catégorie/type
        if category and transaction_type:
            if category.type != 'both':
                if transaction_type == 'income' and category.type != 'income':
                    raise serializers.ValidationError({
                        'category': "Cette catégorie n'est pas compatible avec les revenus."
                    })
                if transaction_type == 'expense' and category.type != 'expense':
                    raise serializers.ValidationError({
                        'category': "Cette catégorie n'est pas compatible avec les dépenses."
                    })
        
        # Valider la configuration de récurrence
        if attrs.get('is_recurring') and not attrs.get('recurring_config'):
            raise serializers.ValidationError({
                'recurring_config': "La configuration de récurrence est requise pour une transaction récurrente."
            })
        
        return attrs
    
    def create(self, validated_data):
        """Crée la transaction pour l'utilisateur connecté."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TransactionListSerializer(serializers.ModelSerializer):
    """
    Serializer léger pour les listes de transactions.
    """
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    signed_amount = serializers.ReadOnlyField()
    group_name = serializers.CharField(source='group.name', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'amount', 'signed_amount', 'type',
            'category', 'category_name', 'category_icon', 'category_color',
            'description', 'date', 'group', 'group_name',
            'is_recurring', 'created_at'
        ]


class ExpenseSplitSerializer(serializers.ModelSerializer):
    """
    Serializer pour les partages de dépenses.
    """
    
    user_details = UserMinimalSerializer(source='user', read_only=True)
    transaction_details = serializers.SerializerMethodField()
    
    class Meta:
        model = ExpenseSplit
        fields = [
            'id', 'transaction', 'transaction_details',
            'user', 'user_details', 'amount',
            'is_paid', 'paid_at', 'created_at'
        ]
        read_only_fields = ['id', 'paid_at', 'created_at']
    
    def get_transaction_details(self, obj):
        """Retourne les détails minimaux de la transaction."""
        return {
            'id': obj.transaction.id,
            'description': obj.transaction.description,
            'total_amount': obj.transaction.amount,
            'date': obj.transaction.date,
        }


class ExpenseSplitCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création de partage de dépense.
    """
    
    class Meta:
        model = ExpenseSplit
        fields = ['user', 'amount']
    
    def validate_amount(self, value):
        """Vérifie que le montant est positif."""
        if value <= 0:
            raise serializers.ValidationError(
                "Le montant doit être supérieur à 0."
            )
        return value


class CreateSplitsSerializer(serializers.Serializer):
    """
    Serializer pour créer plusieurs partages à la fois.
    """
    
    splits = ExpenseSplitCreateSerializer(many=True)
    equal_split = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Si true, divise également entre tous les membres"
    )
    
    def validate_splits(self, value):
        """Vérifie qu'il y a au moins un partage."""
        if not value:
            raise serializers.ValidationError(
                "Au moins un partage est requis."
            )
        return value
    
    def validate(self, attrs):
        """Valide que la somme des montants égale le total."""
        transaction = self.context.get('transaction')
        if not transaction:
            return attrs
        
        splits = attrs.get('splits', [])
        equal_split = attrs.get('equal_split', False)
        
        if not equal_split and splits:
            total_split = sum(s['amount'] for s in splits)
            if total_split != transaction.amount:
                raise serializers.ValidationError({
                    'splits': f"La somme des parts ({total_split}) doit égaler le montant total ({transaction.amount})."
                })
        
        return attrs


class ExpenseSplitUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour marquer un partage comme payé.
    """
    
    class Meta:
        model = ExpenseSplit
        fields = ['is_paid']


# ============ Dashboard & Statistics Serializers ============

class DashboardSerializer(serializers.Serializer):
    """
    Serializer pour le tableau de bord financier.
    """
    
    total_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    recent_transactions = TransactionListSerializer(many=True)
    expense_by_category = serializers.ListField()
    income_by_category = serializers.ListField()
    budget_alerts = serializers.ListField()


class MonthlySummarySerializer(serializers.Serializer):
    """
    Serializer pour le résumé mensuel.
    """
    
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    income = serializers.DecimalField(max_digits=15, decimal_places=2)
    expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    transaction_count = serializers.IntegerField()


class CategoryStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques par catégorie.
    """
    
    category_id = serializers.UUIDField()
    category_name = serializers.CharField()
    category_icon = serializers.CharField()
    category_color = serializers.CharField()
    total = serializers.DecimalField(max_digits=15, decimal_places=2)
    count = serializers.IntegerField()
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class BudgetStatusSerializer(serializers.Serializer):
    """
    Serializer pour le statut du budget d'une catégorie.
    """
    
    budget = serializers.DecimalField(max_digits=15, decimal_places=2)
    spent = serializers.DecimalField(max_digits=15, decimal_places=2)
    remaining = serializers.DecimalField(max_digits=15, decimal_places=2)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    is_over_budget = serializers.BooleanField()
    is_alert = serializers.BooleanField()
    alert_threshold = serializers.IntegerField()


class BudgetOverviewSerializer(serializers.Serializer):
    """
    Serializer pour l'aperçu des budgets.
    """
    
    period = serializers.DictField()
    summary = serializers.DictField()
    categories = serializers.ListField()


class ChartDataSerializer(serializers.Serializer):
    """
    Serializer pour les données de graphiques.
    """
    
    labels = serializers.ListField(child=serializers.CharField())
    income_data = serializers.ListField(child=serializers.DecimalField(max_digits=15, decimal_places=2))
    expense_data = serializers.ListField(child=serializers.DecimalField(max_digits=15, decimal_places=2))


class TransactionFilterSerializer(serializers.Serializer):
    """
    Serializer pour les filtres de transactions.
    """
    
    type = serializers.ChoiceField(
        choices=['income', 'expense'],
        required=False,
        help_text="Type de transaction"
    )
    category = serializers.UUIDField(
        required=False,
        help_text="ID de la catégorie"
    )
    group = serializers.UUIDField(
        required=False,
        help_text="ID du groupe"
    )
    date_from = serializers.DateField(
        required=False,
        help_text="Date de début"
    )
    date_to = serializers.DateField(
        required=False,
        help_text="Date de fin"
    )
    min_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        help_text="Montant minimum"
    )
    max_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        help_text="Montant maximum"
    )
    search = serializers.CharField(
        required=False,
        help_text="Recherche dans la description"
    )
    ordering = serializers.ChoiceField(
        choices=['date', '-date', 'amount', '-amount', 'created_at', '-created_at'],
        required=False,
        default='-date',
        help_text="Tri des résultats"
    )
