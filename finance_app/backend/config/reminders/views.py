"""
Reminders views - Reminder views
"""

from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from groups.models import GroupMember
from .models import Reminder
from .serializers import (
    ReminderSerializer, ReminderCreateSerializer, ReminderUpdateSerializer,
    ReminderListSerializer, CompleteReminderSerializer, UpcomingRemindersSerializer
)


@extend_schema_view(
    list=extend_schema(
        summary="Lister les rappels",
        description="Retourne tous les rappels personnels et de groupe de l'utilisateur.",
        parameters=[
            OpenApiParameter('type', str, description="payment, bill ou general"),
            OpenApiParameter('group', str, description="UUID du groupe"),
            OpenApiParameter('is_completed', bool, description="Filtrer par statut terminé"),
            OpenApiParameter('date_from', str, description="Date de début (ISO)"),
            OpenApiParameter('date_to', str, description="Date de fin (ISO)"),
        ],
        tags=['Rappels']
    ),
    retrieve=extend_schema(
        summary="Détail d'un rappel",
        tags=['Rappels']
    ),
    create=extend_schema(
        summary="Créer un rappel",
        description="Crée un nouveau rappel personnel ou de groupe.",
        tags=['Rappels']
    ),
    update=extend_schema(
        summary="Modifier un rappel",
        tags=['Rappels']
    ),
    partial_update=extend_schema(
        summary="Modifier partiellement un rappel",
        tags=['Rappels']
    ),
    destroy=extend_schema(
        summary="Supprimer un rappel",
        tags=['Rappels']
    ),
)
class ReminderViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des rappels.
    
    Permet de lister, créer, modifier et supprimer des rappels.
    Support des rappels personnels et de groupe.
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = ReminderSerializer
    
    def get_queryset(self):
        """
        Retourne les rappels de l'utilisateur.
        
        Inclut:
        - Rappels personnels
        - Rappels de groupe dont l'utilisateur est membre actif
        """
        user = self.request.user
        
        # Groupes dont l'utilisateur est membre actif
        user_groups = GroupMember.objects.filter(
            user=user,
            status=GroupMember.MemberStatus.ACTIVE
        ).values_list('group_id', flat=True)
        
        # Rappels personnels OU de groupe
        queryset = Reminder.objects.filter(
            Q(user=user, group__isnull=True) | Q(group__in=user_groups)
        ).select_related('user', 'group')
        
        # Appliquer les filtres
        queryset = self._apply_filters(queryset)
        
        return queryset
    
    def _apply_filters(self, queryset):
        """Applique les filtres des paramètres de requête."""
        params = self.request.query_params
        
        # Filtre par type
        reminder_type = params.get('type')
        if reminder_type in ['payment', 'bill', 'general']:
            queryset = queryset.filter(reminder_type=reminder_type)
        
        # Filtre par groupe
        group_id = params.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        
        # Filtre par statut
        is_completed = params.get('is_completed')
        if is_completed is not None:
            is_completed = is_completed.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_completed=is_completed)
        
        # Filtre par dates
        date_from = params.get('date_from')
        if date_from:
            queryset = queryset.filter(reminder_date__gte=date_from)
        
        date_to = params.get('date_to')
        if date_to:
            queryset = queryset.filter(reminder_date__lte=date_to)
        
        # Filtre rappels en retard
        is_overdue = params.get('is_overdue')
        if is_overdue is not None:
            is_overdue = is_overdue.lower() in ['true', '1', 'yes']
            if is_overdue:
                queryset = queryset.filter(
                    is_completed=False,
                    reminder_date__lt=timezone.now()
                )
        
        # Tri
        ordering = params.get('ordering', 'reminder_date')
        valid_orderings = ['reminder_date', '-reminder_date', 'created_at', '-created_at']
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        
        return queryset
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action."""
        if self.action == 'create':
            return ReminderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ReminderUpdateSerializer
        elif self.action == 'list':
            return ReminderListSerializer
        return ReminderSerializer
    
    def get_object(self):
        """
        Récupère un rappel en vérifiant les permissions.
        """
        pk = self.kwargs.get('pk')
        user = self.request.user
        
        # Groupes de l'utilisateur
        user_groups = GroupMember.objects.filter(
            user=user,
            status=GroupMember.MemberStatus.ACTIVE
        ).values_list('group_id', flat=True)
        
        reminder = get_object_or_404(
            Reminder.objects.select_related('user', 'group'),
            Q(id=pk),
            Q(user=user, group__isnull=True) | Q(group__in=user_groups)
        )
        
        return reminder
    
    def perform_destroy(self, instance):
        """
        Supprime un rappel.
        
        Seul le créateur ou un admin du groupe peut supprimer.
        """
        user = self.request.user
        
        # Vérifier les permissions pour les rappels de groupe
        if instance.group:
            if instance.user != user and not instance.group.is_admin(user):
                return Response(
                    {'error': 'Vous n\'avez pas la permission de supprimer ce rappel.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            # Rappel personnel - seul le propriétaire peut supprimer
            if instance.user != user:
                return Response(
                    {'error': 'Vous n\'avez pas la permission de supprimer ce rappel.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        instance.delete()
    
    @action(detail=True, methods=['post'])
    @extend_schema(
        summary="Marquer comme terminé",
        description="Marque un rappel comme terminé. Crée la prochaine occurrence si récurrent.",
        request=CompleteReminderSerializer,
        tags=['Rappels']
    )
    def complete(self, request, pk=None):
        """Marque un rappel comme terminé."""
        reminder = self.get_object()
        
        if reminder.is_completed:
            return Response(
                {'error': 'Ce rappel est déjà terminé.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CompleteReminderSerializer(
            data=request.data,
            context={'reminder': reminder, 'request': request}
        )
        
        if serializer.is_valid():
            result = serializer.save()
            
            response_data = {
                'message': 'Rappel marqué comme terminé.',
                'reminder': ReminderSerializer(result['reminder']).data
            }
            
            if result['next_reminder']:
                response_data['next_reminder'] = ReminderSerializer(result['next_reminder']).data
            
            return Response(response_data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Rappels à venir",
    description="Retourne les rappels prévus dans les prochains jours.",
    parameters=[
        OpenApiParameter('days', int, description="Nombre de jours (défaut: 7, max: 30)")
    ],
    tags=['Rappels']
)
class UpcomingRemindersView(APIView):
    """
    Vue pour afficher les rappels à venir.
    
    Retourne les rappels non terminés dont la date est dans les X prochains jours.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        days = int(request.query_params.get('days', 7))
        days = min(max(days, 1), 30)  # Entre 1 et 30 jours
        
        now = timezone.now()
        end_date = now + timedelta(days=days)
        
        # Groupes de l'utilisateur
        user_groups = GroupMember.objects.filter(
            user=user,
            status=GroupMember.MemberStatus.ACTIVE
        ).values_list('group_id', flat=True)
        
        # Rappels à venir
        reminders = Reminder.objects.filter(
            Q(user=user, group__isnull=True) | Q(group__in=user_groups),
            is_completed=False,
            reminder_date__gte=now,
            reminder_date__lte=end_date
        ).select_related('user', 'group').order_by('reminder_date')
        
        # Rappels en retard
        overdue = Reminder.objects.filter(
            Q(user=user, group__isnull=True) | Q(group__in=user_groups),
            is_completed=False,
            reminder_date__lt=now
        ).select_related('user', 'group').order_by('reminder_date')
        
        return Response({
            'period': {
                'start': now.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'overdue': ReminderListSerializer(overdue, many=True).data,
            'overdue_count': overdue.count(),
            'upcoming': ReminderListSerializer(reminders, many=True).data,
            'upcoming_count': reminders.count()
        })


@extend_schema(
    summary="Statistiques des rappels",
    description="Retourne les statistiques sur les rappels de l'utilisateur.",
    tags=['Rappels']
)
class ReminderStatsView(APIView):
    """
    Vue pour les statistiques des rappels.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        now = timezone.now()
        
        # Groupes de l'utilisateur
        user_groups = GroupMember.objects.filter(
            user=user,
            status=GroupMember.MemberStatus.ACTIVE
        ).values_list('group_id', flat=True)
        
        # Base queryset
        base_qs = Reminder.objects.filter(
            Q(user=user, group__isnull=True) | Q(group__in=user_groups)
        )
        
        # Statistiques
        total = base_qs.count()
        completed = base_qs.filter(is_completed=True).count()
        pending = base_qs.filter(is_completed=False).count()
        overdue = base_qs.filter(is_completed=False, reminder_date__lt=now).count()
        
        # Par type
        by_type = {}
        for reminder_type in ['payment', 'bill', 'general']:
            by_type[reminder_type] = base_qs.filter(
                reminder_type=reminder_type,
                is_completed=False
            ).count()
        
        # Cette semaine
        week_end = now + timedelta(days=7)
        this_week = base_qs.filter(
            is_completed=False,
            reminder_date__gte=now,
            reminder_date__lte=week_end
        ).count()
        
        return Response({
            'total': total,
            'completed': completed,
            'pending': pending,
            'overdue': overdue,
            'this_week': this_week,
            'by_type': by_type,
            'completion_rate': round(completed / total * 100, 1) if total > 0 else 0
        })