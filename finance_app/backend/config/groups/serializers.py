"""
Groups serializers - Group, GroupMember and GroupInvitation serializers
"""

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from accounts.serializers import UserMinimalSerializer
from accounts.models import User
from .models import Group, GroupMember, GroupInvitation


class GroupMemberSerializer(serializers.ModelSerializer):
    """
    Serializer pour les membres de groupe.
    """
    
    user_details = UserMinimalSerializer(source='user', read_only=True)
    invited_by_details = UserMinimalSerializer(source='invited_by', read_only=True)
    is_admin = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = GroupMember
        fields = [
            'id', 'group', 'user', 'user_details',
            'role', 'status', 'is_admin', 'is_active',
            'invited_by', 'invited_by_details',
            'joined_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'group', 'user', 'status', 
            'invited_by', 'joined_at', 'created_at'
        ]


class GroupMemberUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour modifier le rôle d'un membre.
    """
    
    class Meta:
        model = GroupMember
        fields = ['role']
    
    def validate_role(self, value):
        """Vérifie que l'utilisateur peut modifier ce rôle."""
        member = self.instance
        request_user = self.context['request'].user
        
        # Seuls les admins peuvent changer les rôles
        if not member.group.is_admin(request_user):
            raise serializers.ValidationError(
                "Seuls les administrateurs peuvent modifier les rôles."
            )
        
        # On ne peut pas se rétrograder soi-même si on est le dernier admin
        if (member.user == request_user and 
            value == GroupMember.MemberRole.MEMBER and
            member.group.admins.count() == 1):
            raise serializers.ValidationError(
                "Vous ne pouvez pas vous rétrograder, vous êtes le dernier administrateur."
            )
        
        return value


class GroupSerializer(serializers.ModelSerializer):
    """
    Serializer pour les groupes.
    """
    
    owner_details = UserMinimalSerializer(source='owner', read_only=True)
    members_count = serializers.ReadOnlyField()
    balance = serializers.SerializerMethodField()
    current_user_role = serializers.SerializerMethodField()
    is_current_user_admin = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 
            'owner', 'owner_details',
            'image', 'currency', 'is_active',
            'members_count', 'balance',
            'current_user_role', 'is_current_user_admin',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'owner', 'is_active', 
            'created_at', 'updated_at'
        ]
    
    def get_balance(self, obj):
        """Retourne le solde du groupe."""
        return obj.get_balance()
    
    def get_current_user_role(self, obj):
        """Retourne le rôle de l'utilisateur connecté."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                member = obj.members.get(
                    user=request.user,
                    status=GroupMember.MemberStatus.ACTIVE
                )
                return member.role
            except GroupMember.DoesNotExist:
                return None
        return None
    
    def get_is_current_user_admin(self, obj):
        """Retourne True si l'utilisateur connecté est admin."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_admin(request.user)
        return False


class GroupCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création de groupe.
    """
    
    class Meta:
        model = Group
        fields = ['name', 'description', 'image', 'currency']
        extra_kwargs = {
            'description': {'required': False, 'default': ''},
            'image': {'required': False},
            'currency': {'required': False, 'default': 'EUR'},
        }
    
    def validate_name(self, value):
        """Vérifie que le nom n'est pas vide."""
        if not value.strip():
            raise serializers.ValidationError(
                "Le nom du groupe ne peut pas être vide."
            )
        return value.strip()
    
    def create(self, validated_data):
        """Crée le groupe avec l'utilisateur comme propriétaire."""
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class GroupUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour de groupe.
    """
    
    class Meta:
        model = Group
        fields = ['name', 'description', 'image', 'currency']
        extra_kwargs = {
            'name': {'required': False},
            'description': {'required': False},
            'image': {'required': False},
            'currency': {'required': False},
        }
    
    def validate(self, attrs):
        """Vérifie que l'utilisateur est admin du groupe."""
        group = self.instance
        request_user = self.context['request'].user
        
        if not group.is_admin(request_user):
            raise serializers.ValidationError(
                "Seuls les administrateurs peuvent modifier le groupe."
            )
        
        return attrs


class GroupListSerializer(serializers.ModelSerializer):
    """
    Serializer léger pour les listes de groupes.
    """
    
    members_count = serializers.ReadOnlyField()
    current_user_role = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = [
            'id', 'name', 'image', 'currency',
            'members_count', 'current_user_role',
            'is_active', 'created_at'
        ]
    
    def get_current_user_role(self, obj):
        """Retourne le rôle de l'utilisateur connecté."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                member = obj.members.get(
                    user=request.user,
                    status=GroupMember.MemberStatus.ACTIVE
                )
                return member.role
            except GroupMember.DoesNotExist:
                return None
        return None


class GroupDetailSerializer(GroupSerializer):
    """
    Serializer détaillé pour un groupe.
    Inclut la liste des membres.
    """
    
    members = serializers.SerializerMethodField()
    pending_invitations_count = serializers.SerializerMethodField()
    
    class Meta(GroupSerializer.Meta):
        fields = GroupSerializer.Meta.fields + [
            'members', 'pending_invitations_count'
        ]
    
    def get_members(self, obj):
        """Retourne la liste des membres actifs."""
        members = obj.members.filter(
            status=GroupMember.MemberStatus.ACTIVE
        ).select_related('user', 'invited_by')
        return GroupMemberSerializer(members, many=True).data
    
    def get_pending_invitations_count(self, obj):
        """Retourne le nombre d'invitations en attente."""
        return obj.invitations.filter(
            status=GroupInvitation.InvitationStatus.PENDING,
            expires_at__gt=timezone.now()
        ).count()


class GroupInvitationSerializer(serializers.ModelSerializer):
    """
    Serializer pour les invitations de groupe.
    """
    
    group_details = GroupListSerializer(source='group', read_only=True)
    invited_by_details = UserMinimalSerializer(source='invited_by', read_only=True)
    is_valid = serializers.ReadOnlyField()
    
    class Meta:
        model = GroupInvitation
        fields = [
            'id', 'group', 'group_details',
            'email', 'invited_by', 'invited_by_details',
            'token', 'status', 'is_valid',
            'expires_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'group', 'token', 'status',
            'expires_at', 'created_at'
        ]


class InviteToGroupSerializer(serializers.Serializer):
    """
    Serializer pour inviter quelqu'un à un groupe.
    """
    
    email = serializers.EmailField(
        required=True,
        help_text="Adresse email de la personne à inviter"
    )
    
    def validate_email(self, value):
        """Valide l'email et vérifie diverses conditions."""
        value = value.lower()
        group = self.context.get('group')
        request_user = self.context.get('request').user
        
        # Vérifier que l'utilisateur peut inviter
        if not group.is_admin(request_user):
            raise serializers.ValidationError(
                "Seuls les administrateurs peuvent inviter des membres."
            )
        
        # Vérifier la limite de membres
        max_members = getattr(settings, 'APP_SETTINGS', {}).get('MAX_GROUP_MEMBERS', 50)
        if group.members_count >= max_members:
            raise serializers.ValidationError(
                f"Le groupe a atteint la limite de {max_members} membres."
            )
        
        # Vérifier si l'utilisateur est déjà membre
        try:
            user = User.objects.get(email__iexact=value)
            if group.is_member(user):
                raise serializers.ValidationError(
                    "Cet utilisateur est déjà membre du groupe."
                )
            
            # Vérifier s'il a une invitation en attente
            if GroupInvitation.objects.filter(
                group=group,
                email__iexact=value,
                status=GroupInvitation.InvitationStatus.PENDING,
                expires_at__gt=timezone.now()
            ).exists():
                raise serializers.ValidationError(
                    "Une invitation est déjà en attente pour cet email."
                )
        except User.DoesNotExist:
            # L'utilisateur n'existe pas, vérifier juste l'invitation en attente
            if GroupInvitation.objects.filter(
                group=group,
                email__iexact=value,
                status=GroupInvitation.InvitationStatus.PENDING,
                expires_at__gt=timezone.now()
            ).exists():
                raise serializers.ValidationError(
                    "Une invitation est déjà en attente pour cet email."
                )
        
        return value
    
    def create(self, validated_data):
        """Crée l'invitation."""
        group = self.context['group']
        request_user = self.context['request'].user
        
        invitation = GroupInvitation.objects.create(
            group=group,
            email=validated_data['email'],
            invited_by=request_user
        )
        
        return invitation


class AcceptInvitationSerializer(serializers.Serializer):
    """
    Serializer pour accepter une invitation.
    """
    
    token = serializers.CharField(
        required=True,
        help_text="Token d'invitation"
    )
    
    def validate_token(self, value):
        """Vérifie que le token est valide."""
        try:
            invitation = GroupInvitation.objects.get(token=value)
            
            if not invitation.is_valid:
                if invitation.status == GroupInvitation.InvitationStatus.EXPIRED:
                    raise serializers.ValidationError(
                        "Cette invitation a expiré."
                    )
                elif invitation.status == GroupInvitation.InvitationStatus.ACCEPTED:
                    raise serializers.ValidationError(
                        "Cette invitation a déjà été acceptée."
                    )
                elif invitation.status == GroupInvitation.InvitationStatus.DECLINED:
                    raise serializers.ValidationError(
                        "Cette invitation a été refusée."
                    )
                else:
                    raise serializers.ValidationError(
                        "Cette invitation n'est plus valide."
                    )
            
            self.invitation = invitation
            return value
            
        except GroupInvitation.DoesNotExist:
            raise serializers.ValidationError(
                "Invitation introuvable."
            )
    
    def save(self, **kwargs):
        """Accepte l'invitation pour l'utilisateur connecté."""
        user = self.context['request'].user
        return self.invitation.accept(user)


class DeclineInvitationSerializer(serializers.Serializer):
    """
    Serializer pour refuser une invitation.
    """
    
    token = serializers.CharField(
        required=True,
        help_text="Token d'invitation"
    )
    
    def validate_token(self, value):
        """Vérifie que le token est valide."""
        try:
            invitation = GroupInvitation.objects.get(token=value)
            
            if invitation.status != GroupInvitation.InvitationStatus.PENDING:
                raise serializers.ValidationError(
                    "Cette invitation ne peut plus être refusée."
                )
            
            self.invitation = invitation
            return value
            
        except GroupInvitation.DoesNotExist:
            raise serializers.ValidationError(
                "Invitation introuvable."
            )
    
    def save(self, **kwargs):
        """Refuse l'invitation."""
        self.invitation.decline()
        return self.invitation


class LeaveGroupSerializer(serializers.Serializer):
    """
    Serializer pour quitter un groupe.
    """
    
    def validate(self, attrs):
        """Vérifie que l'utilisateur peut quitter le groupe."""
        group = self.context.get('group')
        user = self.context['request'].user
        
        if not group.is_member(user):
            raise serializers.ValidationError(
                "Vous n'êtes pas membre de ce groupe."
            )
        
        # Vérifier si c'est le dernier admin
        if group.is_admin(user) and group.admins.count() == 1:
            # Si c'est le seul membre, on peut supprimer
            if group.members_count == 1:
                return attrs
            
            raise serializers.ValidationError(
                "Vous êtes le dernier administrateur. "
                "Promouvez un autre membre avant de partir."
            )
        
        return attrs
    
    def save(self, **kwargs):
        """Fait quitter le groupe à l'utilisateur."""
        group = self.context['group']
        user = self.context['request'].user
        
        member = group.members.get(
            user=user,
            status=GroupMember.MemberStatus.ACTIVE
        )
        member.leave()
        
        return member


class GroupBalanceSerializer(serializers.Serializer):
    """
    Serializer pour le solde d'un groupe.
    """
    
    income = serializers.DecimalField(max_digits=15, decimal_places=2)
    expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField()


class MemberBalanceSerializer(serializers.Serializer):
    """
    Serializer pour le solde d'un membre dans un groupe.
    """
    
    user = UserMinimalSerializer()
    total_paid = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_owed = serializers.DecimalField(max_digits=15, decimal_places=2)
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)