"""
Finances models - Category, Transaction and ExpenseSplit models
"""

from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import BaseModel, SoftDeleteBaseModel


class Category(BaseModel):
    """
    Catégorie de transaction.
    
    Peut être une catégorie système (partagée par tous) ou personnalisée (créée par un utilisateur).
    
    Attributs:
        - name: Nom de la catégorie
        - description: Description détaillée
        - icon: Icône (emoji ou classe CSS)
        - color: Couleur en hexadécimal
        - type: Type de transaction (income/expense/both)
        - budget: Budget mensuel alloué
        - budget_alert_threshold: Seuil d'alerte en pourcentage
        - is_system: True si c'est une catégorie système
        - user: NULL pour système, utilisateur pour personnalisée
    """
    
    class CategoryType(models.TextChoices):
        INCOME = 'income', 'Revenu'
        EXPENSE = 'expense', 'Dépense'
        BOTH = 'both', 'Les deux'
    
    name = models.CharField(
        max_length=100,
        verbose_name="Nom"
    )
    
    # ============ NOUVEAUX CHAMPS ============
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description",
        help_text="Description détaillée de la catégorie"
    )
    
    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Budget mensuel",
        help_text="Budget mensuel alloué à cette catégorie"
    )
    
    budget_alert_threshold = models.IntegerField(
        default=80,
        validators=[MinValueValidator(0)],
        verbose_name="Seuil d'alerte (%)",
        help_text="Pourcentage du budget à partir duquel une alerte est envoyée"
    )
    # =========================================
    
    icon = models.CharField(
        max_length=50,
        blank=True,
        default='📁',
        verbose_name="Icône"
    )
    color = models.CharField(
        max_length=7,
        default='#6B7280',
        verbose_name="Couleur"
    )
    type = models.CharField(
        max_length=10,
        choices=CategoryType.choices,
        default=CategoryType.EXPENSE,
        verbose_name="Type"
    )
    is_system = models.BooleanField(
        default=False,
        verbose_name="Catégorie système"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='custom_categories',
        verbose_name="Utilisateur"
    )
    
    class Meta:
        db_table = 'categories'
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'type']),
            models.Index(fields=['is_system']),
            models.Index(fields=['budget']),  # NOUVEAU
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'user'],
                name='unique_category_per_user'
            ),
        ]
    
    def __str__(self):
        return f"{self.icon} {self.name}"
    
    def clean(self):
        """Validation : une catégorie système ne peut pas avoir d'utilisateur."""
        if self.is_system and self.user:
            raise ValidationError("Une catégorie système ne peut pas appartenir à un utilisateur.")
        if not self.is_system and not self.user:
            raise ValidationError("Une catégorie personnalisée doit appartenir à un utilisateur.")
        if self.budget_alert_threshold < 0 or self.budget_alert_threshold > 100:
            raise ValidationError("Le seuil d'alerte doit être entre 0 et 100.")
    
    @classmethod
    def get_for_user(cls, user, category_type=None):
        """
        Retourne toutes les catégories disponibles pour un utilisateur.
        Inclut les catégories système et personnalisées de l'utilisateur.
        """
        queryset = cls.objects.filter(
            models.Q(is_system=True) | models.Q(user=user)
        )
        if category_type:
            queryset = queryset.filter(
                models.Q(type=category_type) | models.Q(type=cls.CategoryType.BOTH)
            )
        return queryset.order_by('name')
    
    # ============ NOUVELLES MÉTHODES ============
    def get_monthly_spent(self, year=None, month=None):
        """
        Calcule le montant dépensé ce mois pour cette catégorie.
        
        Args:
            year: Année (défaut: année courante)
            month: Mois (défaut: mois courant)
            
        Returns:
            Decimal: Montant total des dépenses
        """
        if year is None or month is None:
            now = timezone.now()
            year = now.year
            month = now.month
        
        total = self.transactions.filter(
            type=Transaction.TransactionType.EXPENSE,
            date__year=year,
            date__month=month,
            is_deleted=False
        ).aggregate(total=models.Sum('amount'))['total']
        
        return total or Decimal('0.00')
    
    def get_monthly_income(self, year=None, month=None):
        """
        Calcule les revenus du mois pour cette catégorie.
        
        Args:
            year: Année (défaut: année courante)
            month: Mois (défaut: mois courant)
            
        Returns:
            Decimal: Montant total des revenus
        """
        if year is None or month is None:
            now = timezone.now()
            year = now.year
            month = now.month
        
        total = self.transactions.filter(
            type=Transaction.TransactionType.INCOME,
            date__year=year,
            date__month=month,
            is_deleted=False
        ).aggregate(total=models.Sum('amount'))['total']
        
        return total or Decimal('0.00')
    
    def get_budget_status(self, year=None, month=None):
        """
        Retourne le statut du budget (dépensé, restant, pourcentage).
        
        Args:
            year: Année (défaut: année courante)
            month: Mois (défaut: mois courant)
            
        Returns:
            dict: Statut du budget ou None si pas de budget défini
            {
                'budget': float,
                'spent': float,
                'remaining': float,
                'percentage': float,
                'is_over_budget': bool,
                'is_alert': bool,
                'alert_threshold': int
            }
        """
        if not self.budget:
            return None
        
        spent = self.get_monthly_spent(year, month)
        remaining = self.budget - spent
        percentage = (spent / self.budget * 100) if self.budget > 0 else 0
        
        return {
            'budget': float(self.budget),
            'spent': float(spent),
            'remaining': float(remaining),
            'percentage': round(float(percentage), 2),
            'is_over_budget': spent > self.budget,
            'is_alert': percentage >= self.budget_alert_threshold,
            'alert_threshold': self.budget_alert_threshold,
        }
    # ============================================


class Transaction(SoftDeleteBaseModel):
    """
    Transaction financière (revenu ou dépense).
    
    Peut être personnelle (user_id only) ou de groupe (user_id + group_id).
    
    Attributs:
        - user: Créateur de la transaction
        - group: Groupe associé (NULL = transaction personnelle)
        - category: Catégorie de la transaction
        - amount: Montant (toujours positif)
        - type: income ou expense
        - description: Description détaillée
        - date: Date de la transaction
        - is_recurring: Transaction récurrente
        - recurring_config: Configuration de récurrence (JSON)
        - attachment: URL de pièce jointe
    """
    
    class TransactionType(models.TextChoices):
        INCOME = 'income', 'Revenu'
        EXPENSE = 'expense', 'Dépense'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="Utilisateur"
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name="Groupe"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name="Catégorie"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant"
    )
    type = models.CharField(
        max_length=10,
        choices=TransactionType.choices,
        verbose_name="Type"
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name="Description"
    )
    date = models.DateField(
        verbose_name="Date"
    )
    
    # Récurrence
    is_recurring = models.BooleanField(
        default=False,
        verbose_name="Récurrente"
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
    
    # Pièce jointe
    attachment = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Pièce jointe"
    )
    
    class Meta:
        db_table = 'transactions'
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['group', 'date']),
            models.Index(fields=['category']),
            models.Index(fields=['type', 'date']),
            models.Index(fields=['user', 'type', 'date']),
        ]
    
    def __str__(self):
        sign = '+' if self.type == self.TransactionType.INCOME else '-'
        return f"{sign}{self.amount} - {self.category.name} ({self.date})"
    
    def clean(self):
        """Validations métier."""
        # Vérifier que la catégorie correspond au type de transaction
        if self.category.type != Category.CategoryType.BOTH:
            if self.type == self.TransactionType.INCOME and self.category.type != Category.CategoryType.INCOME:
                raise ValidationError({
                    'category': "Cette catégorie n'est pas compatible avec les revenus."
                })
            if self.type == self.TransactionType.EXPENSE and self.category.type != Category.CategoryType.EXPENSE:
                raise ValidationError({
                    'category': "Cette catégorie n'est pas compatible avec les dépenses."
                })
        
        # Vérifier que l'utilisateur est membre du groupe (si groupe)
        if self.group:
            from groups.models import GroupMember
            if not GroupMember.objects.filter(
                group=self.group,
                user=self.user,
                status=GroupMember.MemberStatus.ACTIVE
            ).exists():
                raise ValidationError({
                    'group': "Vous n'êtes pas membre de ce groupe."
                })
    
    @property
    def signed_amount(self):
        """Retourne le montant avec le signe approprié."""
        if self.type == self.TransactionType.EXPENSE:
            return -self.amount
        return self.amount
    
    @property
    def is_personal(self):
        """True si c'est une transaction personnelle (pas de groupe)."""
        return self.group is None


class ExpenseSplit(BaseModel):
    """
    Partage de dépense entre membres d'un groupe.
    
    Chaque ligne représente la part d'un membre pour une transaction de groupe.
    La somme de toutes les parts doit égaler le montant total de la transaction.
    
    Attributs:
        - transaction: Transaction partagée
        - user: Membre qui doit payer
        - amount: Montant à payer
        - is_paid: A payé sa part
        - paid_at: Date de paiement
    """
    
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='splits',
        verbose_name="Transaction"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expense_splits',
        verbose_name="Membre"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant"
    )
    is_paid = models.BooleanField(
        default=False,
        verbose_name="Payé"
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de paiement"
    )
    
    class Meta:
        db_table = 'expense_splits'
        verbose_name = "Partage de dépense"
        verbose_name_plural = "Partages de dépenses"
        ordering = ['transaction', 'user']
        indexes = [
            models.Index(fields=['transaction']),
            models.Index(fields=['user', 'is_paid']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['transaction', 'user'],
                name='unique_split_per_user'
            ),
        ]
    
    def __str__(self):
        status = "✓" if self.is_paid else "✗"
        return f"{self.user.full_name}: {self.amount} [{status}]"
    
    def clean(self):
        """Validations métier."""
        # Vérifier que la transaction est une dépense de groupe
        if self.transaction.type != Transaction.TransactionType.EXPENSE:
            raise ValidationError({
                'transaction': "Seules les dépenses peuvent être partagées."
            })
        if not self.transaction.group:
            raise ValidationError({
                'transaction': "Seules les transactions de groupe peuvent être partagées."
            })
        
        # Vérifier que l'utilisateur est membre du groupe
        from groups.models import GroupMember
        if not GroupMember.objects.filter(
            group=self.transaction.group,
            user=self.user,
            status=GroupMember.MemberStatus.ACTIVE
        ).exists():
            raise ValidationError({
                'user': "Cet utilisateur n'est pas membre du groupe."
            })
    
    def mark_as_paid(self):
        """Marque la part comme payée."""
        self.is_paid = True
        self.paid_at = timezone.now()
        self.save(update_fields=['is_paid', 'paid_at', 'updated_at'])


# Fonction pour créer les catégories système par défaut
def create_default_categories():
    """
    Crée les catégories système par défaut si elles n'existent pas.
    À appeler lors de l'initialisation de la base de données.
    """
    default_categories = [
        # Dépenses
        {
            'name': 'Alimentation',
            'icon': '🍔',
            'color': '#F59E0B',
            'type': 'expense',
            'description': 'Courses alimentaires, restaurants et livraisons',
            'budget': None
        },
        {
            'name': 'Transport',
            'icon': '🚗',
            'color': '#3B82F6',
            'type': 'expense',
            'description': 'Carburant, transports en commun, taxi, entretien véhicule',
            'budget': None
        },
        {
            'name': 'Logement',
            'icon': '🏠',
            'color': '#8B5CF6',
            'type': 'expense',
            'description': 'Loyer, charges, entretien, assurance habitation',
            'budget': None
        },
        {
            'name': 'Factures & Services',
            'icon': '💡',
            'color': '#EF4444',
            'type': 'expense',
            'description': 'Électricité, eau, internet, téléphone, abonnements',
            'budget': None
        },
        {
            'name': 'Divertissement',
            'icon': '🎬',
            'color': '#EC4899',
            'type': 'expense',
            'description': 'Cinéma, sorties, jeux, streaming, loisirs',
            'budget': None
        },
        {
            'name': 'Shopping',
            'icon': '🛒',
            'color': '#14B8A6',
            'type': 'expense',
            'description': 'Vêtements, électronique, achats divers',
            'budget': None
        },
        {
            'name': 'Santé',
            'icon': '💊',
            'color': '#10B981',
            'type': 'expense',
            'description': 'Médecin, pharmacie, mutuelle, optique',
            'budget': None
        },
        {
            'name': 'Éducation',
            'icon': '📚',
            'color': '#6366F1',
            'type': 'expense',
            'description': 'Formations, livres, cours en ligne, scolarité',
            'budget': None
        },
        {
            'name': 'Voyages',
            'icon': '✈️',
            'color': '#F97316',
            'type': 'expense',
            'description': 'Billets, hôtels, vacances, activités touristiques',
            'budget': None
        },
        {
            'name': 'Autres dépenses',
            'icon': '📦',
            'color': '#6B7280',
            'type': 'expense',
            'description': 'Dépenses diverses non catégorisées',
            'budget': None
        },
        
        # Revenus
        {
            'name': 'Salaire',
            'icon': '💰',
            'color': '#22C55E',
            'type': 'income',
            'description': 'Revenus salariaux mensuels et primes',
            'budget': None
        },
        {
            'name': 'Freelance',
            'icon': '💼',
            'color': '#0EA5E9',
            'type': 'income',
            'description': 'Revenus de missions freelance et consulting',
            'budget': None
        },
        {
            'name': 'Investissements',
            'icon': '📈',
            'color': '#A855F7',
            'type': 'income',
            'description': 'Dividendes, intérêts et gains d\'investissement',
            'budget': None
        },
        {
            'name': 'Cadeaux reçus',
            'icon': '🎁',
            'color': '#F43F5E',
            'type': 'income',
            'description': 'Cadeaux et dons reçus',
            'budget': None
        },
        {
            'name': 'Autres revenus',
            'icon': '💵',
            'color': '#84CC16',
            'type': 'income',
            'description': 'Autres sources de revenus divers',
            'budget': None
        },
    ]
    
    created_count = 0
    for cat_data in default_categories:
        category, created = Category.objects.get_or_create(
            name=cat_data['name'],
            is_system=True,
            defaults={
                'icon': cat_data['icon'],
                'color': cat_data['color'],
                'type': cat_data['type'],
                'description': cat_data['description'],
                'budget': cat_data['budget'],
                'user': None,
            }
        )
        if created:
            created_count += 1
    
    return created_count