"""
Admin configuration for groups app.
"""

from django.contrib import admin

from .models import Group, GroupMember, GroupInvitation


class GroupMemberInline(admin.TabularInline):
    """
    Inline pour afficher les membres dans la page du groupe.
    """
    
    model = GroupMember
    extra = 0
    readonly_fields = ['joined_at', 'created_at']
    raw_id_fields = ['user', 'invited_by']


class GroupInvitationInline(admin.TabularInline):
    """
    Inline pour afficher les invitations dans la page du groupe.
    """
    
    model = GroupInvitation
    extra = 0
    readonly_fields = ['token', 'created_at']
    raw_id_fields = ['invited_by']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """
    Configuration admin pour les groupes.
    """
    
    list_display = [
        'name', 'owner', 'currency', 'members_count',
        'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'currency', 'created_at']
    search_fields = ['name', 'description', 'owner__email']
    ordering = ['-created_at']
    
    raw_id_fields = ['owner']
    inlines = [GroupMemberInline, GroupInvitationInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'owner')
        }),
        ('Configuration', {
            'fields': ('currency', 'image')
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    """
    Configuration admin pour les membres de groupe.
    """
    
    list_display = [
        'user', 'group', 'role', 'status',
        'joined_at', 'created_at'
    ]
    list_filter = ['role', 'status', 'created_at']
    search_fields = ['user__email', 'group__name']
    ordering = ['-created_at']
    
    raw_id_fields = ['user', 'group', 'invited_by']


@admin.register(GroupInvitation)
class GroupInvitationAdmin(admin.ModelAdmin):
    """
    Configuration admin pour les invitations de groupe.
    """
    
    list_display = [
        'email', 'group', 'status', 'invited_by',
        'expires_at', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['email', 'group__name', 'invited_by__email']
    ordering = ['-created_at']
    
    readonly_fields = ['token', 'created_at']
    raw_id_fields = ['group', 'invited_by']