"""
Groups models - Group, GroupMember and GroupInvitation models
"""

import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from core.models import BaseModel


class Group(BaseModel):
    """
    Groupe de gestion financière collaborative.
    
    Permet à plusieurs utilisateurs de partager et suivre des finances communes.
    
    Attributs:
        - name: Nom du groupe
        - description: Description du groupe
        - owner: Créateur/propriétaire du groupe
        - image: URL de l'image du groupe
        - currency: Devise utilisée par le groupe
        - is_active: Groupe actif
    """
    
    CURRENCY_CHOICES = [
        ('EUR', 'Euro (€)'),
        ('USD', 'Dollar US ($)'),
        ('GBP', 'Livre Sterling (£)'),
        ('CHF', 'Franc Suisse (CHF)'),
        ('CAD', 'Dollar Canadien (CA$)'),
        ('XAF', 'Franc CFA CEMAC (FCFA)'),
        ('XOF', 'Franc CFA UEMOA (CFA)'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name="Nom"
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name="Description"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_groups',
        verbose_name="Propriétaire"
    )
    image = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Image"
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='EUR',
        verbose_name="Devise"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )
    
    class Meta:
        db_table = 'groups'
        verbose_name = "Groupe"
        verbose_name_plural = "Groupes"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """
        Lors de la création, ajoute automatiquement le propriétaire comme admin.
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            GroupMember.objects.create(
                group=self,
                user=self.owner,
                role=GroupMember.MemberRole.ADMIN,
                status=GroupMember.MemberStatus.ACTIVE,
                joined_at=timezone.now()
            )
    
    @property
    def members_count(self):
        """Retourne le nombre de membres actifs."""
        return self.members.filter(status=GroupMember.MemberStatus.ACTIVE).count()
    
    @property
    def admins(self):
        """Retourne les administrateurs du groupe."""
        return self.members.filter(
            role=GroupMember.MemberRole.ADMIN,
            status=GroupMember.MemberStatus.ACTIVE
        )
    
    def is_admin(self, user):
        """Vérifie si l'utilisateur est admin du groupe."""
        return self.members.filter(
            user=user,
            role=GroupMember.MemberRole.ADMIN,
            status=GroupMember.MemberStatus.ACTIVE
        ).exists()
    
    def is_member(self, user):
        """Vérifie si l'utilisateur est membre actif du groupe."""
        return self.members.filter(
            user=user,
            status=GroupMember.MemberStatus.ACTIVE
        ).exists()
    
    def get_balance(self):
        """
        Calcule le solde du groupe (revenus - dépenses).
        """
        from django.db.models import Sum, Case, When, DecimalField
        from finances.models import Transaction
        
        result = self.transactions.filter(is_deleted=False).aggregate(
            total_income=Sum(
                Case(
                    When(type=Transaction.TransactionType.INCOME, then='amount'),
                    default=0,
                    output_field=DecimalField()
                )
            ),
            total_expense=Sum(
                Case(
                    When(type=Transaction.TransactionType.EXPENSE, then='amount'),
                    default=0,
                    output_field=DecimalField()
                )
            )
        )
        
        income = result['total_income'] or 0
        expense = result['total_expense'] or 0
        
        return {
            'income': income,
            'expense': expense,
            'balance': income - expense
        }


class GroupMember(BaseModel):
    """
    Appartenance d'un utilisateur à un groupe.
    
    Définit le rôle (admin/membre) et le statut (pending/active/left).
    
    Attributs:
        - group: Groupe
        - user: Utilisateur
        - role: admin ou member
        - status: pending, active ou left
        - invited_by: Qui a invité ce membre
        - joined_at: Date d'adhésion effective
    """
    
    class MemberRole(models.TextChoices):
        ADMIN = 'admin', 'Administrateur'
        MEMBER = 'member', 'Membre'
    
    class MemberStatus(models.TextChoices):
        PENDING = 'pending', 'En attente'
        ACTIVE = 'active', 'Actif'
        LEFT = 'left', 'Parti'
    
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name="Groupe"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_memberships',
        verbose_name="Utilisateur"
    )
    role = models.CharField(
        max_length=10,
        choices=MemberRole.choices,
        default=MemberRole.MEMBER,
        verbose_name="Rôle"
    )
    status = models.CharField(
        max_length=10,
        choices=MemberStatus.choices,
        default=MemberStatus.PENDING,
        verbose_name="Statut"
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_invitations',
        verbose_name="Invité par"
    )
    joined_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'adhésion"
    )
    
    class Meta:
        db_table = 'group_members'
        verbose_name = "Membre du groupe"
        verbose_name_plural = "Membres du groupe"
        ordering = ['group', '-role', 'joined_at']
        indexes = [
            models.Index(fields=['group', 'status']),
            models.Index(fields=['user', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'user'],
                name='unique_member_per_group'
            ),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} - {self.group.name} ({self.role})"
    
    @property
    def is_admin(self):
        """True si le membre est administrateur."""
        return self.role == self.MemberRole.ADMIN
    
    @property
    def is_active(self):
        """True si le membre est actif."""
        return self.status == self.MemberStatus.ACTIVE
    
    def activate(self):
        """Active le membre (accepte l'invitation)."""
        self.status = self.MemberStatus.ACTIVE
        self.joined_at = timezone.now()
        self.save(update_fields=['status', 'joined_at', 'updated_at'])
    
    def leave(self):
        """Le membre quitte le groupe."""
        self.status = self.MemberStatus.LEFT
        self.save(update_fields=['status', 'updated_at'])
    
    def promote_to_admin(self):
        """Promeut le membre au rang d'administrateur."""
        self.role = self.MemberRole.ADMIN
        self.save(update_fields=['role', 'updated_at'])
    
    def demote_to_member(self):
        """Rétrograde l'administrateur au rang de membre."""
        self.role = self.MemberRole.MEMBER
        self.save(update_fields=['role', 'updated_at'])


class GroupInvitation(BaseModel):
    """
    Invitation à rejoindre un groupe.
    
    Envoyée par email aux utilisateurs non encore inscrits.
    Contient un token unique pour accepter l'invitation.
    
    Attributs:
        - group: Groupe concerné
        - email: Email de l'invité
        - invited_by: Utilisateur qui invite
        - token: Token unique d'invitation
        - status: pending, accepted, declined, expired
        - expires_at: Date d'expiration
    """
    
    class InvitationStatus(models.TextChoices):
        PENDING = 'pending', 'En attente'
        ACCEPTED = 'accepted', 'Acceptée'
        DECLINED = 'declined', 'Refusée'
        EXPIRED = 'expired', 'Expirée'
    
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='invitations',
        verbose_name="Groupe"
    )
    email = models.EmailField(
        max_length=255,
        verbose_name="Email de l'invité"
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_invitations_sent',
        verbose_name="Invité par"
    )
    token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Token"
    )
    status = models.CharField(
        max_length=10,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING,
        verbose_name="Statut"
    )
    expires_at = models.DateTimeField(
        verbose_name="Date d'expiration"
    )
    
    class Meta:
        db_table = 'group_invitations'
        verbose_name = "Invitation de groupe"
        verbose_name_plural = "Invitations de groupe"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['email', 'status']),
            models.Index(fields=['group', 'status']),
        ]
    
    def __str__(self):
        return f"Invitation to {self.group.name} for {self.email}"
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            days = getattr(settings, 'APP_SETTINGS', {}).get('INVITATION_EXPIRY_DAYS', 7)
            self.expires_at = timezone.now() + timedelta(days=days)
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        """Vérifie si l'invitation est encore valide."""
        return (
            self.status == self.InvitationStatus.PENDING and
            self.expires_at > timezone.now()
        )
    
    def accept(self, user):
        """
        Accepte l'invitation et ajoute l'utilisateur au groupe.
        
        Args:
            user: L'utilisateur qui accepte l'invitation
        
        Returns:
            GroupMember: Le nouveau membre créé
        """
        if not self.is_valid:
            from core.exceptions import InvitationExpiredException
            raise InvitationExpiredException()
        
        # Créer ou mettre à jour le membre
        member, created = GroupMember.objects.get_or_create(
            group=self.group,
            user=user,
            defaults={
                'role': GroupMember.MemberRole.MEMBER,
                'status': GroupMember.MemberStatus.ACTIVE,
                'invited_by': self.invited_by,
                'joined_at': timezone.now()
            }
        )
        
        if not created:
            member.activate()
        
        # Marquer l'invitation comme acceptée
        self.status = self.InvitationStatus.ACCEPTED
        self.save(update_fields=['status', 'updated_at'])
        
        return member
    
    def decline(self):
        """Refuse l'invitation."""
        self.status = self.InvitationStatus.DECLINED
        self.save(update_fields=['status', 'updated_at'])
    
    def check_expiration(self):
        """Vérifie et met à jour le statut si expiré."""
        if self.status == self.InvitationStatus.PENDING and self.expires_at <= timezone.now():
            self.status = self.InvitationStatus.EXPIRED
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False