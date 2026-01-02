"""
Custom permissions for the application.
"""

from rest_framework import permissions

from groups.models import GroupMember


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission qui permet uniquement au propriétaire d'un objet de le modifier.
    Les autres utilisateurs peuvent seulement lire.
    """
    
    def has_object_permission(self, request, view, obj):
        # Les permissions de lecture sont autorisées pour toutes les requêtes
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Les permissions d'écriture sont uniquement pour le propriétaire
        return obj.user == request.user


class IsOwner(permissions.BasePermission):
    """
    Permission qui permet uniquement au propriétaire d'un objet d'y accéder.
    """
    
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsGroupMember(permissions.BasePermission):
    """
    Permission qui vérifie si l'utilisateur est membre actif du groupe.
    """
    
    message = "Vous n'êtes pas membre de ce groupe."
    
    def has_permission(self, request, view):
        # L'authentification est requise
        if not request.user.is_authenticated:
            return False
        return True
    
    def has_object_permission(self, request, view, obj):
        # Si l'objet est un groupe
        if hasattr(obj, 'is_member'):
            return obj.is_member(request.user)
        
        # Si l'objet a un attribut 'group'
        if hasattr(obj, 'group') and obj.group:
            return obj.group.is_member(request.user)
        
        return True


class IsGroupAdmin(permissions.BasePermission):
    """
    Permission qui vérifie si l'utilisateur est administrateur du groupe.
    """
    
    message = "Seuls les administrateurs du groupe peuvent effectuer cette action."
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return True
    
    def has_object_permission(self, request, view, obj):
        # Si l'objet est un groupe
        if hasattr(obj, 'is_admin'):
            return obj.is_admin(request.user)
        
        # Si l'objet a un attribut 'group'
        if hasattr(obj, 'group') and obj.group:
            return obj.group.is_admin(request.user)
        
        return True


class IsGroupAdminOrReadOnly(permissions.BasePermission):
    """
    Permission qui permet aux admins de modifier, aux membres de lire.
    """
    
    message = "Seuls les administrateurs du groupe peuvent effectuer cette action."
    
    def has_object_permission(self, request, view, obj):
        # Les permissions de lecture pour les membres
        if request.method in permissions.SAFE_METHODS:
            if hasattr(obj, 'is_member'):
                return obj.is_member(request.user)
            if hasattr(obj, 'group') and obj.group:
                return obj.group.is_member(request.user)
            return True
        
        # Les permissions d'écriture pour les admins
        if hasattr(obj, 'is_admin'):
            return obj.is_admin(request.user)
        if hasattr(obj, 'group') and obj.group:
            return obj.group.is_admin(request.user)
        
        return True


class IsGroupOwner(permissions.BasePermission):
    """
    Permission qui vérifie si l'utilisateur est le propriétaire du groupe.
    """
    
    message = "Seul le propriétaire du groupe peut effectuer cette action."
    
    def has_object_permission(self, request, view, obj):
        # Si l'objet est un groupe
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        # Si l'objet a un attribut 'group'
        if hasattr(obj, 'group') and obj.group:
            return obj.group.owner == request.user
        
        return False


class IsTransactionOwnerOrGroupMember(permissions.BasePermission):
    """
    Permission pour les transactions:
    - Transaction personnelle: seul le propriétaire
    - Transaction de groupe: membres du groupe
    """
    
    message = "Vous n'avez pas accès à cette transaction."
    
    def has_object_permission(self, request, view, obj):
        # Transaction personnelle
        if not obj.group:
            return obj.user == request.user
        
        # Transaction de groupe - les membres peuvent voir
        if request.method in permissions.SAFE_METHODS:
            return obj.group.is_member(request.user)
        
        # Seul le créateur ou un admin peut modifier
        if obj.user == request.user:
            return True
        
        return obj.group.is_admin(request.user)


class IsReminderOwnerOrGroupMember(permissions.BasePermission):
    """
    Permission pour les rappels:
    - Rappel personnel: seul le propriétaire
    - Rappel de groupe: membres du groupe
    """
    
    message = "Vous n'avez pas accès à ce rappel."
    
    def has_object_permission(self, request, view, obj):
        # Rappel personnel
        if not obj.group:
            return obj.user == request.user
        
        # Rappel de groupe - les membres peuvent voir
        if request.method in permissions.SAFE_METHODS:
            return obj.group.is_member(request.user)
        
        # Seul le créateur ou un admin peut modifier
        if obj.user == request.user:
            return True
        
        return obj.group.is_admin(request.user)


class IsVerifiedUser(permissions.BasePermission):
    """
    Permission qui vérifie si l'email de l'utilisateur est vérifié.
    """
    
    message = "Veuillez vérifier votre adresse email pour accéder à cette fonctionnalité."
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.is_verified
        )


class CanInviteToGroup(permissions.BasePermission):
    """
    Permission pour inviter des membres à un groupe.
    Seuls les admins peuvent inviter.
    """
    
    message = "Seuls les administrateurs peuvent inviter des membres."
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return True
    
    def has_object_permission(self, request, view, obj):
        # obj est le groupe
        return obj.is_admin(request.user)


class CanManageGroupMember(permissions.BasePermission):
    """
    Permission pour gérer les membres d'un groupe.
    - Seuls les admins peuvent changer les rôles
    - On ne peut pas se modifier soi-même (sauf quitter)
    """
    
    message = "Vous n'avez pas la permission de gérer ce membre."
    
    def has_object_permission(self, request, view, obj):
        # obj est un GroupMember
        user = request.user
        
        # Vérifier que c'est un admin du groupe
        if not obj.group.is_admin(user):
            return False
        
        # Ne peut pas modifier son propre rôle
        if obj.user == user and request.method in ['PUT', 'PATCH']:
            return False
        
        # Ne peut pas supprimer le propriétaire
        if obj.user == obj.group.owner and request.method == 'DELETE':
            return False
        
        return True