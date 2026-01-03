"""
Groups views - Group, GroupMember and GroupInvitation views
"""

from decimal import Decimal

from django.db.models import Sum, Case, When, DecimalField, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from finances.models import Transaction, ExpenseSplit
from finances.serializers import TransactionListSerializer
from .models import Group, GroupMember, GroupInvitation
from .serializers import (
    GroupSerializer, GroupCreateSerializer, GroupUpdateSerializer,
    GroupListSerializer, GroupDetailSerializer,
    GroupMemberSerializer, GroupMemberUpdateSerializer,
    GroupInvitationSerializer, InviteToGroupSerializer,
    AcceptInvitationSerializer, DeclineInvitationSerializer,
    LeaveGroupSerializer, GroupBalanceSerializer, MemberBalanceSerializer
)


@extend_schema_view(
    list=extend_schema(
        summary="Lister mes groupes",
        description="Retourne tous les groupes dont l'utilisateur est membre actif.",
        tags=['Groupes']
    ),
    retrieve=extend_schema(
        summary="Détail d'un groupe",
        description="Retourne les détails complets d'un groupe avec ses membres.",
        tags=['Groupes']
    ),
    create=extend_schema(
        summary="Créer un groupe",
        description="Crée un nouveau groupe. L'utilisateur devient propriétaire et administrateur.",
        tags=['Groupes']
    ),
    update=extend_schema(
        summary="Modifier un groupe",
        description="Modifie les informations d'un groupe (administrateurs uniquement).",
        tags=['Groupes']
    ),
    partial_update=extend_schema(
        summary="Modifier partiellement un groupe",
        tags=['Groupes']
    ),
    destroy=extend_schema(
        summary="Supprimer un groupe",
        description="Supprime un groupe (propriétaire uniquement). Le groupe doit être vide ou avoir un seul membre.",
        tags=['Groupes']
    ),
)
class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des groupes.
    
    Permet de lister, créer, modifier et supprimer des groupes.
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer
    
    def get_queryset(self):
        """Retourne les groupes dont l'utilisateur est membre actif."""
        user = self.request.user
        
        # Groupes où l'utilisateur est membre actif
        return Group.objects.filter(
            members__user=user,
            members__status=GroupMember.MemberStatus.ACTIVE,
            is_active=True
        ).distinct().select_related('owner').prefetch_related('members')
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action."""
        if self.action == 'create':
            return GroupCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return GroupUpdateSerializer
        elif self.action == 'retrieve':
            return GroupDetailSerializer
        elif self.action == 'list':
            return GroupListSerializer
        return GroupSerializer
    
    def perform_destroy(self, instance):
        """
        Supprime un groupe.
        
        Seul le propriétaire peut supprimer le groupe.
        Le groupe doit avoir au maximum 1 membre (le propriétaire).
        """
        user = self.request.user
        
        # Vérifier que l'utilisateur est le propriétaire
        if instance.owner != user:
            return Response(
                {'error': 'Seul le propriétaire peut supprimer le groupe.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Vérifier le nombre de membres actifs
        active_members_count = instance.members.filter(
            status=GroupMember.MemberStatus.ACTIVE
        ).count()
        
        if active_members_count > 1:
            return Response(
                {'error': 'Le groupe contient encore des membres. Retirez-les d\'abord.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Soft delete - désactiver le groupe
        instance.is_active = False
        instance.save()


@extend_schema(
    summary="Inviter au groupe",
    description="Envoie une invitation par email pour rejoindre le groupe.",
    request=InviteToGroupSerializer,
    responses={201: GroupInvitationSerializer},
    tags=['Invitations']
)
class InviteToGroupView(APIView):
    """
    Vue pour inviter quelqu'un à rejoindre un groupe.
    
    L'invitation est envoyée par email avec un lien contenant un token unique.
    Seuls les administrateurs peuvent inviter de nouveaux membres.
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, group_id):
        # Récupérer le groupe
        group = get_object_or_404(
            Group,
            id=group_id,
            is_active=True
        )
        
        # Vérifier que l'utilisateur est admin
        if not group.is_admin(request.user):
            return Response(
                {'error': 'Seuls les administrateurs peuvent inviter des membres.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = InviteToGroupSerializer(
            data=request.data,
            context={'request': request, 'group': group}
        )
        
        if serializer.is_valid():
            invitation = serializer.save()
            
            # TODO: Envoyer l'email d'invitation
            # send_invitation_email(invitation)
            
            return Response(
                GroupInvitationSerializer(invitation).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Accepter une invitation",
    description="Accepte une invitation et rejoint le groupe.",
    tags=['Invitations']
)
class AcceptInvitationView(APIView):
    """
    Vue pour accepter une invitation à rejoindre un groupe.
    
    Le token d'invitation doit être valide et non expiré.
    L'utilisateur connecté doit correspondre à l'email de l'invitation.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, token):
        """
        GET pour afficher les informations de l'invitation.
        """
        try:
            invitation = GroupInvitation.objects.select_related(
                'group', 'invited_by'
            ).get(token=token)
            
            return Response({
                'invitation': GroupInvitationSerializer(invitation).data,
                'is_valid': invitation.is_valid,
                'can_accept': (
                    invitation.is_valid and 
                    request.user.email.lower() == invitation.email.lower()
                )
            })
            
        except GroupInvitation.DoesNotExist:
            return Response(
                {'error': 'Invitation introuvable.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def post(self, request, token):
        """
        POST pour accepter l'invitation.
        """
        try:
            invitation = GroupInvitation.objects.select_related(
                'group', 'invited_by'
            ).get(token=token)
            
            # Vérifier que l'invitation est valide
            if not invitation.is_valid:
                return Response(
                    {'error': 'Cette invitation n\'est plus valide.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Vérifier que l'email correspond
            if request.user.email.lower() != invitation.email.lower():
                return Response(
                    {'error': 'Cette invitation ne vous est pas destinée.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Accepter l'invitation
            member = invitation.accept(request.user)
            
            return Response({
                'message': f'Vous avez rejoint le groupe "{invitation.group.name}".',
                'group': GroupSerializer(invitation.group, context={'request': request}).data,
                'member': GroupMemberSerializer(member).data
            })
            
        except GroupInvitation.DoesNotExist:
            return Response(
                {'error': 'Invitation introuvable.'},
                status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    summary="Lister les membres",
    description="Retourne la liste des membres d'un groupe.",
    tags=['Membres']
)
class GroupMembersView(generics.ListAPIView):
    """
    Vue pour lister les membres d'un groupe.
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = GroupMemberSerializer
    
    def get_queryset(self):
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(Group, id=group_id, is_active=True)
        
        # Vérifier que l'utilisateur est membre
        if not group.is_member(self.request.user):
            return GroupMember.objects.none()
        
        return group.members.filter(
            status=GroupMember.MemberStatus.ACTIVE
        ).select_related('user', 'invited_by')


@extend_schema(
    summary="Détail/Modification d'un membre",
    description="Afficher, modifier le rôle ou retirer un membre du groupe.",
    tags=['Membres']
)
class GroupMemberDetailView(APIView):
    """
    Vue pour gérer un membre spécifique d'un groupe.
    
    - GET: Afficher les détails du membre
    - PATCH: Modifier le rôle (promouvoir/rétrograder)
    - DELETE: Retirer le membre du groupe
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_group_and_member(self, group_id, user_id):
        """Récupère le groupe et le membre."""
        group = get_object_or_404(Group, id=group_id, is_active=True)
        
        member = get_object_or_404(
            GroupMember,
            group=group,
            user_id=user_id,
            status=GroupMember.MemberStatus.ACTIVE
        )
        
        return group, member
    
    def get(self, request, group_id, user_id):
        """Afficher les détails d'un membre."""
        group, member = self.get_group_and_member(group_id, user_id)
        
        # Vérifier que l'utilisateur est membre du groupe
        if not group.is_member(request.user):
            return Response(
                {'error': 'Vous n\'êtes pas membre de ce groupe.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return Response(GroupMemberSerializer(member).data)
    
    def patch(self, request, group_id, user_id):
        """Modifier le rôle d'un membre."""
        group, member = self.get_group_and_member(group_id, user_id)
        
        # Vérifier que l'utilisateur est admin
        if not group.is_admin(request.user):
            return Response(
                {'error': 'Seuls les administrateurs peuvent modifier les rôles.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = GroupMemberUpdateSerializer(
            member,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(GroupMemberSerializer(member).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, group_id, user_id):
        """Retirer un membre du groupe."""
        group, member = self.get_group_and_member(group_id, user_id)
        
        # Vérifier que l'utilisateur est admin ou est le membre lui-même
        if not group.is_admin(request.user) and request.user.id != user_id:
            return Response(
                {'error': 'Vous n\'avez pas la permission de retirer ce membre.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Empêcher le retrait du propriétaire
        if member.user == group.owner:
            return Response(
                {'error': 'Le propriétaire du groupe ne peut pas être retiré.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier si c'est le dernier admin
        if member.role == GroupMember.MemberRole.ADMIN and group.admins.count() == 1:
            return Response(
                {'error': 'Impossible de retirer le dernier administrateur.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        member.leave()
        
        return Response(
            {'message': 'Membre retiré avec succès.'},
            status=status.HTTP_200_OK
        )


@extend_schema(
    summary="Quitter un groupe",
    description="L'utilisateur quitte le groupe.",
    tags=['Groupes']
)
class LeaveGroupView(APIView):
    """
    Vue pour quitter un groupe.
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id, is_active=True)
        
        serializer = LeaveGroupSerializer(
            data={},
            context={'request': request, 'group': group}
        )
        
        if serializer.is_valid():
            member = serializer.save()
            
            return Response({
                'message': f'Vous avez quitté le groupe "{group.name}".'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Solde du groupe",
    description="Retourne le solde financier du groupe et la répartition par membre.",
    tags=['Groupes']
)
class GroupBalanceView(APIView):
    """
    Vue pour afficher le solde d'un groupe.
    
    Inclut le total des revenus/dépenses et la balance de chaque membre.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id, is_active=True)
        
        # Vérifier que l'utilisateur est membre
        if not group.is_member(request.user):
            return Response(
                {'error': 'Vous n\'êtes pas membre de ce groupe.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Solde global du groupe
        group_balance = group.get_balance()
        
        # Balance par membre
        members = group.members.filter(
            status=GroupMember.MemberStatus.ACTIVE
        ).select_related('user')
        
        member_balances = []
        
        for member in members:
            # Transactions créées par ce membre
            created_transactions = Transaction.objects.filter(
                group=group,
                user=member.user,
                is_deleted=False,
                type='expense'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            # Parts dues (ExpenseSplit)
            owed_splits = ExpenseSplit.objects.filter(
                transaction__group=group,
                user=member.user
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            # Parts payées
            paid_splits = ExpenseSplit.objects.filter(
                transaction__group=group,
                user=member.user,
                is_paid=True
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            member_balances.append({
                'user': {
                    'id': str(member.user.id),
                    'email': member.user.email,
                    'first_name': member.user.first_name,
                    'last_name': member.user.last_name,
                    'full_name': member.user.full_name
                },
                'total_paid': created_transactions,
                'total_owed': owed_splits,
                'balance': created_transactions - owed_splits  # Positif = créditeur
            })
        
        return Response({
            'group': {
                'id': str(group.id),
                'name': group.name,
                'currency': group.currency
            },
            'summary': group_balance,
            'members': member_balances
        })


@extend_schema(
    summary="Transactions du groupe",
    description="Retourne les transactions d'un groupe avec filtres.",
    parameters=[
        OpenApiParameter('type', str, description="income ou expense"),
        OpenApiParameter('date_from', str, description="Date de début (YYYY-MM-DD)"),
        OpenApiParameter('date_to', str, description="Date de fin (YYYY-MM-DD)"),
    ],
    tags=['Groupes']
)
class GroupTransactionsView(generics.ListAPIView):
    """
    Vue pour lister les transactions d'un groupe.
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionListSerializer
    
    def get_queryset(self):
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(Group, id=group_id, is_active=True)
        
        # Vérifier que l'utilisateur est membre
        if not group.is_member(self.request.user):
            return Transaction.objects.none()
        
        queryset = Transaction.objects.filter(
            group=group,
            is_deleted=False
        ).select_related('user', 'category')
        
        # Appliquer les filtres
        params = self.request.query_params
        
        # Type
        transaction_type = params.get('type')
        if transaction_type in ['income', 'expense']:
            queryset = queryset.filter(type=transaction_type)
        
        # Dates
        date_from = params.get('date_from')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        date_to = params.get('date_to')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset.order_by('-date', '-created_at')