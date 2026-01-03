"""
Events views - Event and Calendar views
"""

from datetime import timedelta, datetime
from calendar import monthrange

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from .models import Event
from .serializers import (
    EventSerializer, EventCreateSerializer, EventUpdateSerializer,
    EventListSerializer, CalendarEventSerializer
)


@extend_schema_view(
    list=extend_schema(
        summary="Lister les événements",
        description="Retourne tous les événements de l'utilisateur.",
        parameters=[
            OpenApiParameter('date_from', str, description="Date de début (ISO)"),
            OpenApiParameter('date_to', str, description="Date de fin (ISO)"),
            OpenApiParameter('all_day', bool, description="Événements journée entière"),
            OpenApiParameter('search', str, description="Recherche dans titre/description"),
        ],
        tags=['Événements']
    ),
    retrieve=extend_schema(
        summary="Détail d'un événement",
        tags=['Événements']
    ),
    create=extend_schema(
        summary="Créer un événement",
        description="Crée un nouvel événement. Peut être lié à une transaction ou un rappel.",
        tags=['Événements']
    ),
    update=extend_schema(
        summary="Modifier un événement",
        tags=['Événements']
    ),
    partial_update=extend_schema(
        summary="Modifier partiellement un événement",
        tags=['Événements']
    ),
    destroy=extend_schema(
        summary="Supprimer un événement",
        tags=['Événements']
    ),
)
class EventViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des événements.
    
    Permet de lister, créer, modifier et supprimer des événements.
    Support des liens vers transactions et rappels.
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = EventSerializer
    
    def get_queryset(self):
        """Retourne les événements de l'utilisateur avec filtres."""
        user = self.request.user
        
        queryset = Event.objects.filter(
            user=user
        ).select_related('user', 'transaction', 'reminder')
        
        # Appliquer les filtres
        queryset = self._apply_filters(queryset)
        
        return queryset
    
    def _apply_filters(self, queryset):
        """Applique les filtres des paramètres de requête."""
        params = self.request.query_params
        
        # Filtre par dates
        date_from = params.get('date_from')
        if date_from:
            queryset = queryset.filter(start_date__gte=date_from)
        
        date_to = params.get('date_to')
        if date_to:
            queryset = queryset.filter(start_date__lte=date_to)
        
        # Événements journée entière
        all_day = params.get('all_day')
        if all_day is not None:
            all_day = all_day.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(all_day=all_day)
        
        # Avec transaction
        has_transaction = params.get('has_transaction')
        if has_transaction is not None:
            has_transaction = has_transaction.lower() in ['true', '1', 'yes']
            if has_transaction:
                queryset = queryset.filter(transaction__isnull=False)
            else:
                queryset = queryset.filter(transaction__isnull=True)
        
        # Avec rappel
        has_reminder = params.get('has_reminder')
        if has_reminder is not None:
            has_reminder = has_reminder.lower() in ['true', '1', 'yes']
            if has_reminder:
                queryset = queryset.filter(reminder__isnull=False)
            else:
                queryset = queryset.filter(reminder__isnull=True)
        
        # Couleur
        color = params.get('color')
        if color:
            queryset = queryset.filter(color=color)
        
        # Recherche
        search = params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        
        # Tri
        ordering = params.get('ordering', 'start_date')
        valid_orderings = ['start_date', '-start_date', 'created_at', '-created_at']
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        
        return queryset
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action."""
        if self.action == 'create':
            return EventCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EventUpdateSerializer
        elif self.action == 'list':
            return EventListSerializer
        return EventSerializer
    
    def get_object(self):
        """Récupère un événement en vérifiant les permissions."""
        pk = self.kwargs.get('pk')
        return get_object_or_404(
            Event.objects.select_related('user', 'transaction', 'reminder'),
            id=pk,
            user=self.request.user
        )


@extend_schema(
    summary="Calendrier mensuel",
    description="Retourne les événements d'un mois donné pour affichage calendrier.",
    parameters=[
        OpenApiParameter('year', int, required=True, description="Année (2000-2100)"),
        OpenApiParameter('month', int, required=True, description="Mois (1-12)"),
    ],
    tags=['Calendrier']
)
class CalendarView(APIView):
    """
    Vue calendrier pour un mois donné.
    
    Retourne les événements optimisés pour l'affichage calendrier.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Paramètres
        try:
            year = int(request.query_params.get('year', timezone.now().year))
            month = int(request.query_params.get('month', timezone.now().month))
            
            if not (2000 <= year <= 2100):
                return Response(
                    {'error': 'L\'année doit être entre 2000 et 2100.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not (1 <= month <= 12):
                return Response(
                    {'error': 'Le mois doit être entre 1 et 12.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Paramètres year et month invalides.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Dates du mois
        first_day = timezone.make_aware(datetime(year, month, 1))
        last_day_num = monthrange(year, month)[1]
        last_day = timezone.make_aware(
            datetime(year, month, last_day_num, 23, 59, 59)
        )
        
        # Événements du mois
        events = Event.objects.filter(
            user=user,
            start_date__gte=first_day,
            start_date__lte=last_day
        ).order_by('start_date')
        
        # Organiser par jour
        events_by_day = {}
        for event in events:
            day = event.start_date.day
            if day not in events_by_day:
                events_by_day[day] = []
            events_by_day[day].append(CalendarEventSerializer(event).data)
        
        return Response({
            'year': year,
            'month': month,
            'first_day': first_day.isoformat(),
            'last_day': last_day.isoformat(),
            'total_events': events.count(),
            'events_by_day': events_by_day,
            'events': CalendarEventSerializer(events, many=True).data
        })


@extend_schema(
    summary="Calendrier d'un mois spécifique",
    description="Retourne les événements pour une année et mois spécifiques.",
    tags=['Calendrier']
)
class MonthCalendarView(APIView):
    """
    Vue calendrier pour un mois spécifique via URL.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, year, month):
        user = request.user
        
        # Validation
        if not (2000 <= year <= 2100):
            return Response(
                {'error': 'L\'année doit être entre 2000 et 2100.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not (1 <= month <= 12):
            return Response(
                {'error': 'Le mois doit être entre 1 et 12.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Dates du mois
        first_day = timezone.make_aware(datetime(year, month, 1))
        last_day_num = monthrange(year, month)[1]
        last_day = timezone.make_aware(
            datetime(year, month, last_day_num, 23, 59, 59)
        )
        
        # Événements du mois (inclut ceux qui chevauchent)
        events = Event.objects.filter(
            user=user
        ).filter(
            # Commence dans le mois
            Q(start_date__gte=first_day, start_date__lte=last_day) |
            # Ou se termine dans le mois
            Q(end_date__gte=first_day, end_date__lte=last_day) |
            # Ou englobe tout le mois
            Q(start_date__lt=first_day, end_date__gt=last_day)
        ).order_by('start_date')
        
        # Organiser par jour
        events_by_day = {}
        for event in events:
            day = event.start_date.day
            if day not in events_by_day:
                events_by_day[day] = []
            events_by_day[day].append(CalendarEventSerializer(event).data)
        
        return Response({
            'year': year,
            'month': month,
            'days_in_month': last_day_num,
            'total_events': events.count(),
            'events_by_day': events_by_day,
            'events': CalendarEventSerializer(events, many=True).data
        })


@extend_schema(
    summary="Événements à venir",
    description="Retourne les événements prévus dans les prochains jours.",
    parameters=[
        OpenApiParameter('days', int, description="Nombre de jours (défaut: 7, max: 30)")
    ],
    tags=['Événements']
)
class UpcomingEventsView(APIView):
    """
    Vue pour les événements à venir.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        days = int(request.query_params.get('days', 7))
        days = min(max(days, 1), 30)  # Entre 1 et 30 jours
        
        now = timezone.now()
        end_date = now + timedelta(days=days)
        
        events = Event.objects.filter(
            user=user,
            start_date__gte=now,
            start_date__lte=end_date
        ).select_related('transaction', 'reminder').order_by('start_date')
        
        # Événements en cours
        ongoing = Event.objects.filter(
            user=user,
            start_date__lte=now,
            end_date__gte=now
        ).select_related('transaction', 'reminder')
        
        return Response({
            'period': {
                'start': now.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'ongoing': EventListSerializer(ongoing, many=True).data,
            'ongoing_count': ongoing.count(),
            'upcoming': EventListSerializer(events, many=True).data,
            'upcoming_count': events.count()
        })


@extend_schema(
    summary="Événements d'une date",
    description="Retourne les événements pour une date spécifique.",
    parameters=[
        OpenApiParameter('date', str, required=True, description="Date (YYYY-MM-DD)")
    ],
    tags=['Événements']
)
class DateEventsView(APIView):
    """
    Vue pour les événements d'une date spécifique.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        date_str = request.query_params.get('date')
        
        if not date_str:
            return Response(
                {'error': 'Le paramètre date est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Format de date invalide. Utilisez YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Début et fin de la journée
        day_start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
        day_end = timezone.make_aware(datetime.combine(date, datetime.max.time()))
        
        # Événements de la journée
        events = Event.objects.filter(
            user=user
        ).filter(
            # Commence ce jour
            Q(start_date__date=date) |
            # Ou se termine ce jour
            Q(end_date__date=date) |
            # Ou englobe ce jour
            Q(start_date__lt=day_start, end_date__gt=day_end)
        ).select_related('transaction', 'reminder').order_by('start_date')
        
        return Response({
            'date': date_str,
            'count': events.count(),
            'events': EventSerializer(events, many=True).data
        })


@extend_schema(
    summary="Événements d'aujourd'hui",
    description="Retourne les événements du jour actuel.",
    tags=['Événements']
)
class TodayEventsView(APIView):
    """
    Vue pour les événements d'aujourd'hui.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        today = timezone.now().date()
        
        # Début et fin de la journée
        day_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        day_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        
        # Événements d'aujourd'hui
        events = Event.objects.filter(
            user=user
        ).filter(
            Q(start_date__date=today) |
            Q(end_date__date=today) |
            Q(start_date__lt=day_start, end_date__gt=day_end)
        ).select_related('transaction', 'reminder').order_by('start_date')
        
        # Séparer par statut
        now = timezone.now()
        past = []
        ongoing = []
        upcoming = []
        
        for event in events:
            if event.end_date and event.end_date < now:
                past.append(event)
            elif event.start_date > now:
                upcoming.append(event)
            else:
                ongoing.append(event)
        
        return Response({
            'date': today.isoformat(),
            'total_count': events.count(),
            'past': EventListSerializer(past, many=True).data,
            'past_count': len(past),
            'ongoing': EventListSerializer(ongoing, many=True).data,
            'ongoing_count': len(ongoing),
            'upcoming': EventListSerializer(upcoming, many=True).data,
            'upcoming_count': len(upcoming)
        })


@extend_schema(
    summary="Statistiques des événements",
    description="Retourne les statistiques sur les événements de l'utilisateur.",
    tags=['Événements']
)
class EventStatsView(APIView):
    """
    Vue pour les statistiques des événements.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        now = timezone.now()
        
        # Base queryset
        base_qs = Event.objects.filter(user=user)
        
        # Statistiques générales
        total = base_qs.count()
        past = base_qs.filter(
            Q(end_date__lt=now) | Q(end_date__isnull=True, start_date__lt=now)
        ).count()
        upcoming = base_qs.filter(start_date__gt=now).count()
        ongoing = total - past - upcoming
        
        # Par catégorie
        all_day_count = base_qs.filter(all_day=True).count()
        with_transaction = base_qs.filter(transaction__isnull=False).count()
        with_reminder = base_qs.filter(reminder__isnull=False).count()
        
        # Ce mois
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        this_month = base_qs.filter(
            start_date__gte=month_start,
            start_date__lte=month_end
        ).count()
        
        # Cette semaine
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        this_week = base_qs.filter(
            start_date__gte=week_start,
            start_date__lt=week_end
        ).count()
        
        return Response({
            'total': total,
            'past': past,
            'ongoing': ongoing,
            'upcoming': upcoming,
            'all_day': all_day_count,
            'with_transaction': with_transaction,
            'with_reminder': with_reminder,
            'this_month': this_month,
            'this_week': this_week
        })