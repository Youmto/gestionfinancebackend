"""
Finances views - Category, Transaction, Dashboard and ExpenseSplit views
"""

from decimal import Decimal
from datetime import datetime, timedelta
from calendar import monthrange
from .services import BudgetAlertService
from django.db.models import Sum, Case, When, DecimalField, Count, Q
from django.utils import timezone
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from .exports import ExcelExporter, PDFExporter

from groups.models import GroupMember
from .models import Category, Transaction, ExpenseSplit, create_default_categories
from .serializers import (
    CategorySerializer, CategoryCreateSerializer, CategorySimpleSerializer,
    TransactionSerializer, TransactionCreateSerializer, TransactionListSerializer,
    ExpenseSplitSerializer, ExpenseSplitCreateSerializer, 
    CreateSplitsSerializer, ExpenseSplitUpdateSerializer,
    DashboardSerializer, MonthlySummarySerializer,
    CategoryStatsSerializer, ChartDataSerializer,
    TransactionFilterSerializer, BudgetStatusSerializer, BudgetOverviewSerializer
)


@extend_schema_view(
    list=extend_schema(
        summary="Lister les catégories",
        description="Retourne les catégories système et personnalisées de l'utilisateur.",
        tags=['Catégories']
    ),
    retrieve=extend_schema(
        summary="Détail d'une catégorie",
        tags=['Catégories']
    ),
    create=extend_schema(
        summary="Créer une catégorie",
        description="Crée une nouvelle catégorie personnalisée.",
        tags=['Catégories']
    ),
    update=extend_schema(
        summary="Modifier une catégorie",
        tags=['Catégories']
    ),
    partial_update=extend_schema(
        summary="Modifier partiellement une catégorie",
        tags=['Catégories']
    ),
    destroy=extend_schema(
        summary="Supprimer une catégorie",
        description="Seules les catégories personnalisées peuvent être supprimées.",
        tags=['Catégories']
    ),
)
class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des catégories.
    
    Permet de lister, créer, modifier et supprimer des catégories.
    Les catégories système ne peuvent pas être modifiées ou supprimées.
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer
    
    def get_queryset(self):
        """Retourne les catégories accessibles à l'utilisateur."""
        return Category.get_for_user(self.request.user)
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action."""
        if self.action == 'create':
            return CategoryCreateSerializer
        return CategorySerializer
    
    def perform_destroy(self, instance):
        """Empêche la suppression des catégories système."""
        if instance.is_system:
            return Response(
                {'error': 'Les catégories système ne peuvent pas être supprimées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier s'il y a des transactions liées
        if instance.transactions.filter(
            user=self.request.user,
            is_deleted=False
        ).exists():
            return Response(
                {'error': 'Cette catégorie contient des transactions.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.delete()
    
    @action(detail=False, methods=['get'])
    @extend_schema(
        summary="Catégories par type",
        parameters=[
            OpenApiParameter('type', str, description="Type: income, expense ou both")
        ],
        tags=['Catégories']
    )
    def by_type(self, request):
        """Retourne les catégories filtrées par type."""
        category_type = request.query_params.get('type', None)
        queryset = Category.get_for_user(request.user, category_type)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    # ============ NOUVEAUX ENDPOINTS BUDGET ============
    
    @action(detail=True, methods=['get'])
    @extend_schema(
        summary="Statut du budget d'une catégorie",
        description="Retourne le statut détaillé du budget pour une catégorie.",
        parameters=[
            OpenApiParameter('year', int, description="Année (défaut: année courante)"),
            OpenApiParameter('month', int, description="Mois 1-12 (défaut: mois courant)")
        ],
        responses={200: BudgetStatusSerializer},
        tags=['Catégories', 'Budget']
    )
    def budget_status(self, request, pk=None):
        """Retourne le statut du budget d'une catégorie."""
        category = self.get_object()
        
        # Récupérer année/mois
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        
        if year and month:
            year = int(year)
            month = int(month)
        else:
            now = timezone.now()
            year = now.year
            month = now.month
        
        # Obtenir le statut
        budget_status = category.get_budget_status(year, month)
        
        if budget_status is None:
            return Response({
                'category': CategorySerializer(category, context={'request': request}).data,
                'message': 'Aucun budget défini pour cette catégorie',
                'has_budget': False
            })
        
        # Récupérer les transactions récentes du mois
        recent_transactions = Transaction.objects.filter(
            user=request.user,
            category=category,
            type=Transaction.TransactionType.EXPENSE,
            date__year=year,
            date__month=month,
            is_deleted=False
        ).order_by('-date')[:5]
        
        return Response({
            'category': CategorySerializer(category, context={'request': request}).data,
            'period': {'year': year, 'month': month},
            'has_budget': True,
            **budget_status,
            'recent_transactions': TransactionListSerializer(recent_transactions, many=True).data
        })
    
    @action(detail=False, methods=['get'])
    @extend_schema(
        summary="Aperçu de tous les budgets",
        description="Retourne un résumé de tous les budgets définis avec leur statut.",
        parameters=[
            OpenApiParameter('year', int, description="Année (défaut: année courante)"),
            OpenApiParameter('month', int, description="Mois 1-12 (défaut: mois courant)")
        ],
        responses={200: BudgetOverviewSerializer},
        tags=['Catégories', 'Budget']
    )
    def budget_overview(self, request):
        """Retourne un aperçu de tous les budgets."""
        now = timezone.now()
        year = int(request.query_params.get('year', now.year))
        month = int(request.query_params.get('month', now.month))
        
        # Catégories avec budget
        categories = self.get_queryset().filter(
            budget__isnull=False,
            type__in=[Category.CategoryType.EXPENSE, Category.CategoryType.BOTH]
        )
        
        results = []
        total_budget = Decimal('0.00')
        total_spent = Decimal('0.00')
        alerts_count = 0
        over_budget_count = 0
        
        for category in categories:
            status_data = category.get_budget_status(year, month)
            if status_data:
                total_budget += Decimal(str(status_data['budget']))
                total_spent += Decimal(str(status_data['spent']))
                
                if status_data['is_over_budget']:
                    over_budget_count += 1
                elif status_data['is_alert']:
                    alerts_count += 1
                
                results.append({
                    'id': str(category.id),
                    'name': category.name,
                    'description': category.description,
                    'icon': category.icon,
                    'color': category.color,
                    **status_data
                })
        
        # Trier par pourcentage décroissant
        results.sort(key=lambda x: x['percentage'], reverse=True)
        
        return Response({
            'period': {'year': year, 'month': month},
            'summary': {
                'total_budget': float(total_budget),
                'total_spent': float(total_spent),
                'total_remaining': float(total_budget - total_spent),
                'overall_percentage': round(float(total_spent / total_budget * 100) if total_budget > 0 else 0, 2),
                'categories_count': len(results),
                'alerts_count': alerts_count,
                'over_budget_count': over_budget_count
            },
            'categories': results
        })
    
    @action(detail=False, methods=['get'])
    @extend_schema(
        summary="Alertes budget",
        description="Retourne les catégories en alerte ou avec budget dépassé.",
        parameters=[
            OpenApiParameter('year', int, description="Année"),
            OpenApiParameter('month', int, description="Mois 1-12")
        ],
        tags=['Catégories', 'Budget']
    )
    def budget_alerts(self, request):
        """Retourne les catégories en alerte ou dépassées."""
        now = timezone.now()
        year = int(request.query_params.get('year', now.year))
        month = int(request.query_params.get('month', now.month))
        
        categories = self.get_queryset().filter(
            budget__isnull=False,
            type__in=[Category.CategoryType.EXPENSE, Category.CategoryType.BOTH]
        )
        
        over_budget = []
        alerts = []
        healthy = []
        
        for category in categories:
            status_data = category.get_budget_status(year, month)
            if status_data:
                item = {
                    'id': str(category.id),
                    'name': category.name,
                    'description': category.description,
                    'icon': category.icon,
                    'color': category.color,
                    **status_data
                }
                
                if status_data['is_over_budget']:
                    over_budget.append(item)
                elif status_data['is_alert']:
                    alerts.append(item)
                else:
                    healthy.append(item)
        
        return Response({
            'period': {'year': year, 'month': month},
            'over_budget': over_budget,
            'alerts': alerts,
            'healthy': healthy,
            'summary': {
                'over_budget_count': len(over_budget),
                'alerts_count': len(alerts),
                'healthy_count': len(healthy)
            }
        })
    # ===================================================


@extend_schema_view(
    list=extend_schema(
        summary="Lister les transactions",
        description="Retourne les transactions personnelles et de groupe de l'utilisateur.",
        parameters=[
            OpenApiParameter('type', str, description="income ou expense"),
            OpenApiParameter('category', str, description="UUID de la catégorie"),
            OpenApiParameter('group', str, description="UUID du groupe"),
            OpenApiParameter('date_from', str, description="Date de début (YYYY-MM-DD)"),
            OpenApiParameter('date_to', str, description="Date de fin (YYYY-MM-DD)"),
            OpenApiParameter('search', str, description="Recherche dans la description"),
        ],
        tags=['Transactions']
    ),
    retrieve=extend_schema(
        summary="Détail d'une transaction",
        tags=['Transactions']
    ),
    create=extend_schema(
        summary="Créer une transaction",
        tags=['Transactions']
    ),
    update=extend_schema(
        summary="Modifier une transaction",
        tags=['Transactions']
    ),
    partial_update=extend_schema(
        summary="Modifier partiellement une transaction",
        tags=['Transactions']
    ),
    destroy=extend_schema(
        summary="Supprimer une transaction",
        description="Suppression douce (soft delete).",
        tags=['Transactions']
    ),
)
class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des transactions.
    
    Permet de lister, créer, modifier et supprimer des transactions.
    Support des filtres et de la recherche.
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    
    def get_queryset(self):
        """Retourne les transactions de l'utilisateur avec filtres."""
        user = self.request.user
        
        # Transactions personnelles OU de groupe dont l'utilisateur est membre
        user_groups = GroupMember.objects.filter(
            user=user,
            status=GroupMember.MemberStatus.ACTIVE
        ).values_list('group_id', flat=True)
        
        queryset = Transaction.objects.filter(
            Q(user=user, group__isnull=True) | Q(group__in=user_groups),
            is_deleted=False
        ).select_related('user', 'category', 'group')
        
        # Appliquer les filtres
        queryset = self._apply_filters(queryset)
        
        return queryset
    
    def _apply_filters(self, queryset):
        """Applique les filtres des paramètres de requête."""
        params = self.request.query_params
        
        # Filtre par type
        transaction_type = params.get('type')
        if transaction_type in ['income', 'expense']:
            queryset = queryset.filter(type=transaction_type)
        
        # Filtre par catégorie
        category_id = params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filtre par groupe
        group_id = params.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        
        # Filtre par date
        date_from = params.get('date_from')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        date_to = params.get('date_to')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        # Filtre par montant
        min_amount = params.get('min_amount')
        if min_amount:
            queryset = queryset.filter(amount__gte=min_amount)
        
        max_amount = params.get('max_amount')
        if max_amount:
            queryset = queryset.filter(amount__lte=max_amount)
        
        # Recherche
        search = params.get('search')
        if search:
            queryset = queryset.filter(description__icontains=search)
        
        # Tri
        ordering = params.get('ordering', '-date')
        if ordering in ['date', '-date', 'amount', '-amount', 'created_at', '-created_at']:
            queryset = queryset.order_by(ordering)
        
        return queryset
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action."""
        if self.action in ['create', 'update', 'partial_update']:
            return TransactionCreateSerializer
        if self.action == 'list':
            return TransactionListSerializer
        return TransactionSerializer
    
    def perform_destroy(self, instance):
        """Suppression douce."""
        instance.soft_delete()
    
    @action(detail=True, methods=['post'])
    @extend_schema(
        summary="Partager une dépense",
        description="Divise une dépense de groupe entre les membres.",
        request=CreateSplitsSerializer,
        tags=['Transactions']
    )
    
    def perform_create(self, serializer):
        """Crée une transaction et vérifie les alertes budget."""
        transaction = serializer.save(user=self.request.user)
        
        # Vérifier les alertes budget pour les dépenses
        if transaction.type == 'expense' and transaction.category:
            BudgetAlertService.check_and_send_alerts(
                user=self.request.user,
                category=transaction.category
            )

    def perform_update(self, serializer):
        """Met à jour une transaction et vérifie les alertes budget."""
        transaction = serializer.save()
        
        # Vérifier les alertes budget pour les dépenses
        if transaction.type == 'expense' and transaction.category:
            BudgetAlertService.check_and_send_alerts(
                user=self.request.user,
                category=transaction.category
            )
    def split(self, request, pk=None):
        """Crée des partages pour une transaction de groupe."""
        transaction = self.get_object()
        
        # Vérifications
        if transaction.type != Transaction.TransactionType.EXPENSE:
            return Response(
                {'error': 'Seules les dépenses peuvent être partagées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not transaction.group:
            return Response(
                {'error': 'Seules les transactions de groupe peuvent être partagées.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CreateSplitsSerializer(
            data=request.data,
            context={'request': request, 'transaction': transaction}
        )
        serializer.is_valid(raise_exception=True)
        
        # Créer les partages
        splits_data = serializer.validated_data.get('splits', [])
        equal_split = serializer.validated_data.get('equal_split', False)
        
        # Supprimer les anciens partages
        transaction.splits.all().delete()
        
        if equal_split:
            # Diviser également entre tous les membres actifs
            members = transaction.group.members.filter(
                status=GroupMember.MemberStatus.ACTIVE
            )
            member_count = members.count()
            split_amount = transaction.amount / member_count
            
            for member in members:
                ExpenseSplit.objects.create(
                    transaction=transaction,
                    user=member.user,
                    amount=split_amount
                )
        else:
            # Utiliser les montants fournis
            for split_data in splits_data:
                ExpenseSplit.objects.create(
                    transaction=transaction,
                    user=split_data['user'],
                    amount=split_data['amount']
                )
        
        # Retourner les partages créés
        splits = transaction.splits.all()
        return Response(
            ExpenseSplitSerializer(splits, many=True).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    @extend_schema(
        summary="Voir les partages",
        description="Retourne les partages d'une transaction.",
        tags=['Transactions']
    )
    def splits(self, request, pk=None):
        """Retourne les partages d'une transaction."""
        transaction = self.get_object()
        splits = transaction.splits.select_related('user')
        return Response(ExpenseSplitSerializer(splits, many=True).data)


@extend_schema(
    summary="Marquer un partage comme payé",
    tags=['Transactions']
)
class ExpenseSplitUpdateView(generics.UpdateAPIView):
    """
    Vue pour marquer un partage de dépense comme payé.
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSplitUpdateSerializer
    queryset = ExpenseSplit.objects.all()
    
    def get_queryset(self):
        """Filtre les partages accessibles à l'utilisateur."""
        return ExpenseSplit.objects.filter(
            Q(user=self.request.user) |  # Sa propre part
            Q(transaction__group__members__user=self.request.user,
              transaction__group__members__role=GroupMember.MemberRole.ADMIN,
              transaction__group__members__status=GroupMember.MemberStatus.ACTIVE)  # Admin du groupe
        ).distinct()
    
    def perform_update(self, serializer):
        """Met à jour le partage."""
        if serializer.validated_data.get('is_paid'):
            serializer.instance.mark_as_paid()
        else:
            serializer.save()


@extend_schema(
    summary="Tableau de bord financier",
    description="Retourne les statistiques financières de l'utilisateur avec alertes budget.",
    tags=['Dashboard']
)
class DashboardView(APIView):
    """
    Vue du tableau de bord financier.
    
    Retourne:
    - Solde total
    - Revenus et dépenses totaux
    - Revenus et dépenses du mois
    - Transactions récentes
    - Répartition par catégorie
    - Alertes budget (NOUVEAU)
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Transactions personnelles (non supprimées)
        transactions = Transaction.objects.filter(
            user=user,
            group__isnull=True,
            is_deleted=False
        )
        
        # Calculs globaux
        totals = transactions.aggregate(
            total_income=Sum(
                Case(
                    When(type='income', then='amount'),
                    default=Decimal('0'),
                    output_field=DecimalField()
                )
            ),
            total_expense=Sum(
                Case(
                    When(type='expense', then='amount'),
                    default=Decimal('0'),
                    output_field=DecimalField()
                )
            )
        )
        
        total_income = totals['total_income'] or Decimal('0')
        total_expense = totals['total_expense'] or Decimal('0')
        total_balance = total_income - total_expense
        
        # Calculs mensuels
        now = timezone.now()
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly = transactions.filter(
            date__gte=first_day_of_month.date()
        ).aggregate(
            monthly_income=Sum(
                Case(
                    When(type='income', then='amount'),
                    default=Decimal('0'),
                    output_field=DecimalField()
                )
            ),
            monthly_expense=Sum(
                Case(
                    When(type='expense', then='amount'),
                    default=Decimal('0'),
                    output_field=DecimalField()
                )
            )
        )
        
        monthly_income = monthly['monthly_income'] or Decimal('0')
        monthly_expense = monthly['monthly_expense'] or Decimal('0')
        
        # Transactions récentes
        recent_transactions = transactions.order_by('-date', '-created_at')[:10]
        
        # Répartition par catégorie (dépenses)
        expense_by_category = transactions.filter(
            type='expense'
        ).values(
            'category__id', 'category__name', 
            'category__icon', 'category__color'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')[:10]
        
        # Répartition par catégorie (revenus)
        income_by_category = transactions.filter(
            type='income'
        ).values(
            'category__id', 'category__name',
            'category__icon', 'category__color'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')[:10]
        
        # Calculer les pourcentages
        expense_list = []
        for item in expense_by_category:
            percentage = (item['total'] / total_expense * 100) if total_expense > 0 else 0
            expense_list.append({
                'category_id': item['category__id'],
                'category_name': item['category__name'],
                'category_icon': item['category__icon'],
                'category_color': item['category__color'],
                'total': item['total'],
                'count': item['count'],
                'percentage': round(percentage, 2)
            })
        
        income_list = []
        for item in income_by_category:
            percentage = (item['total'] / total_income * 100) if total_income > 0 else 0
            income_list.append({
                'category_id': item['category__id'],
                'category_name': item['category__name'],
                'category_icon': item['category__icon'],
                'category_color': item['category__color'],
                'total': item['total'],
                'count': item['count'],
                'percentage': round(percentage, 2)
            })
        
        # ============ NOUVEAU: Alertes Budget ============
        budget_alerts = []
        categories_with_budget = Category.objects.filter(
            Q(is_system=True) | Q(user=user),
            budget__isnull=False,
            type__in=[Category.CategoryType.EXPENSE, Category.CategoryType.BOTH]
        )
        
        for category in categories_with_budget:
            status_data = category.get_budget_status(now.year, now.month)
            if status_data and (status_data['is_alert'] or status_data['is_over_budget']):
                budget_alerts.append({
                    'category_id': str(category.id),
                    'category_name': category.name,
                    'category_icon': category.icon,
                    'category_color': category.color,
                    **status_data
                })
        
        # Trier par pourcentage décroissant
        budget_alerts.sort(key=lambda x: x['percentage'], reverse=True)
        # ================================================
        
        data = {
            'total_balance': total_balance,
            'total_income': total_income,
            'total_expense': total_expense,
            'monthly_income': monthly_income,
            'monthly_expense': monthly_expense,
            'recent_transactions': TransactionListSerializer(recent_transactions, many=True).data,
            'expense_by_category': expense_list,
            'income_by_category': income_list,
            'budget_alerts': budget_alerts,  # NOUVEAU
        }
        
        return Response(data)


@extend_schema(
    summary="Résumé mensuel",
    description="Retourne le résumé financier mois par mois.",
    parameters=[
        OpenApiParameter('months', int, description="Nombre de mois (défaut: 12)")
    ],
    tags=['Dashboard']
)
class MonthlySummaryView(APIView):
    """
    Vue du résumé mensuel.
    
    Retourne les totaux par mois pour les X derniers mois.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        months = int(request.query_params.get('months', 12))
        
        # Limiter à 24 mois max
        months = min(months, 24)
        
        now = timezone.now()
        summaries = []
        
        for i in range(months):
            # Calculer le mois
            target_date = now - timedelta(days=30 * i)
            year = target_date.year
            month = target_date.month
            
            # Dates du mois
            first_day = datetime(year, month, 1).date()
            last_day_num = monthrange(year, month)[1]
            last_day = datetime(year, month, last_day_num).date()
            
            # Agréger
            result = Transaction.objects.filter(
                user=user,
                group__isnull=True,
                is_deleted=False,
                date__gte=first_day,
                date__lte=last_day
            ).aggregate(
                income=Sum(
                    Case(
                        When(type='income', then='amount'),
                        default=Decimal('0'),
                        output_field=DecimalField()
                    )
                ),
                expense=Sum(
                    Case(
                        When(type='expense', then='amount'),
                        default=Decimal('0'),
                        output_field=DecimalField()
                    )
                ),
                count=Count('id')
            )
            
            income = result['income'] or Decimal('0')
            expense = result['expense'] or Decimal('0')
            
            summaries.append({
                'year': year,
                'month': month,
                'income': income,
                'expense': expense,
                'balance': income - expense,
                'transaction_count': result['count'] or 0
            })
        
        return Response(summaries)


@extend_schema(
    summary="Données pour graphiques",
    description="Retourne les données formatées pour les graphiques.",
    parameters=[
        OpenApiParameter('period', str, description="monthly ou weekly"),
        OpenApiParameter('count', int, description="Nombre de périodes")
    ],
    tags=['Dashboard']
)
class ChartDataView(APIView):
    """
    Vue des données pour graphiques.
    
    Retourne les données de revenus/dépenses formatées pour affichage graphique.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        period = request.query_params.get('period', 'monthly')
        count = int(request.query_params.get('count', 6))
        count = min(count, 12)  # Limiter
        
        labels = []
        income_data = []
        expense_data = []
        
        now = timezone.now()
        
        if period == 'weekly':
            for i in range(count - 1, -1, -1):
                # Calculer la semaine
                week_start = now - timedelta(weeks=i, days=now.weekday())
                week_end = week_start + timedelta(days=6)
                
                label = f"S{week_start.isocalendar()[1]}"
                labels.append(label)
                
                result = Transaction.objects.filter(
                    user=user,
                    group__isnull=True,
                    is_deleted=False,
                    date__gte=week_start.date(),
                    date__lte=week_end.date()
                ).aggregate(
                    income=Sum(
                        Case(
                            When(type='income', then='amount'),
                            default=Decimal('0'),
                            output_field=DecimalField()
                        )
                    ),
                    expense=Sum(
                        Case(
                            When(type='expense', then='amount'),
                            default=Decimal('0'),
                            output_field=DecimalField()
                        )
                    )
                )
                
                income_data.append(result['income'] or Decimal('0'))
                expense_data.append(result['expense'] or Decimal('0'))
        else:
            # Mensuel par défaut
            month_names = [
                'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'
            ]
            
            for i in range(count - 1, -1, -1):
                target_date = now - timedelta(days=30 * i)
                year = target_date.year
                month = target_date.month
                
                label = f"{month_names[month - 1]} {year}"
                labels.append(label)
                
                first_day = datetime(year, month, 1).date()
                last_day_num = monthrange(year, month)[1]
                last_day = datetime(year, month, last_day_num).date()
                
                result = Transaction.objects.filter(
                    user=user,
                    group__isnull=True,
                    is_deleted=False,
                    date__gte=first_day,
                    date__lte=last_day
                ).aggregate(
                    income=Sum(
                        Case(
                            When(type='income', then='amount'),
                            default=Decimal('0'),
                            output_field=DecimalField()
                        )
                    ),
                    expense=Sum(
                        Case(
                            When(type='expense', then='amount'),
                            default=Decimal('0'),
                            output_field=DecimalField()
                        )
                    )
                )
                
                income_data.append(result['income'] or Decimal('0'))
                expense_data.append(result['expense'] or Decimal('0'))
        
        return Response({
            'labels': labels,
            'income_data': income_data,
            'expense_data': expense_data
        })


@extend_schema(
    summary="Initialiser les catégories système",
    description="Crée les catégories par défaut si elles n'existent pas.",
    tags=['Admin']
)
class InitCategoriesView(APIView):
    """
    Vue pour initialiser les catégories système.
    
    À appeler lors du premier démarrage de l'application.
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if not request.user.is_staff:
            return Response(
                {'error': 'Réservé aux administrateurs.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        count = create_default_categories()
        return Response({
            'message': f'{count} catégories créées.',
            'created_count': count
        })


class ExportTransactionsView(APIView):
    """
    Exporter les transactions en Excel ou PDF.
    
    GET /api/v1/finances/export/transactions/?format=excel&date_from=2026-01-01&date_to=2026-01-31
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        export_format = request.query_params.get('format', 'excel')
        
        # Filtres
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        transaction_type = request.query_params.get('type')
        category_id = request.query_params.get('category')
        
        # Requête de base
        transactions = Transaction.objects.filter(
            user=user,
            group__isnull=True,
            is_deleted=False
        ).select_related('category').order_by('-date')
        
        # Appliquer les filtres
        if date_from:
            transactions = transactions.filter(date__gte=date_from)
        if date_to:
            transactions = transactions.filter(date__lte=date_to)
        if transaction_type:
            transactions = transactions.filter(type=transaction_type)
        if category_id:
            transactions = transactions.filter(category_id=category_id)
        
        # Titre du rapport
        title = "Transactions"
        if date_from and date_to:
            title = f"Transactions du {date_from} au {date_to}"
        
        # Exporter
        if export_format == 'pdf':
            return PDFExporter.export_transactions(transactions, user, title)
        else:
            return ExcelExporter.export_transactions(transactions, user, title)


class ExportBudgetReportView(APIView):
    """
    Exporter le rapport de budget en Excel.
    
    GET /api/v1/finances/export/budget/?year=2026&month=1
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        now = timezone.now()
        year = int(request.query_params.get('year', now.year))
        month = int(request.query_params.get('month', now.month))
        
        categories = Category.objects.filter(
            Q(is_system=True) | Q(user=user),
            budget__isnull=False,
            type__in=[Category.CategoryType.EXPENSE, Category.CategoryType.BOTH]
        )
        
        return ExcelExporter.export_budget_report(categories, user, year, month)


class ExportMonthlyReportView(APIView):
    """
    Exporter le rapport mensuel complet en PDF.
    
    GET /api/v1/finances/export/monthly/?year=2026&month=1
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        now = timezone.now()
        year = int(request.query_params.get('year', now.year))
        month = int(request.query_params.get('month', now.month))
        
        # Transactions du mois
        transactions = Transaction.objects.filter(
            user=user,
            group__isnull=True,
            is_deleted=False,
            date__year=year,
            date__month=month
        ).select_related('category').order_by('-date')
        
        # Catégories avec budget
        categories = Category.objects.filter(
            Q(is_system=True) | Q(user=user),
            budget__isnull=False
        )
        
        return PDFExporter.export_monthly_report(user, year, month, transactions, categories)