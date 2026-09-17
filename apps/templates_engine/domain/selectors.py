from django.db.models import Q

from apps.templates_engine.models import (
    AccessRole,
    InviteStatus,
    TemplateInvite,
    TemplatePermission,
    TemplateShareGroup,
    UserNotification,
    Workspace,
    WorkspaceJoinRequest,
    WorkspaceJoinRequestStatus,
    WorkspaceMembership,
)


class TemplateEngineSelector:
    @staticmethod
    def workspace_memberships_for_user(user):
        return WorkspaceMembership.objects.select_related("workspace").filter(user=user, is_active=True)

    @staticmethod
    def owned_workspaces(user):
        return Workspace.objects.filter(owner=user)

    @staticmethod
    def pending_workspace_requests_for_owner(user):
        return WorkspaceJoinRequest.objects.select_related("workspace", "requester").filter(
            workspace__owner=user,
            status=WorkspaceJoinRequestStatus.PENDING,
        )

    @staticmethod
    def my_pending_workspace_requests(user):
        return WorkspaceJoinRequest.objects.select_related("workspace").filter(
            requester=user,
            status=WorkspaceJoinRequestStatus.PENDING,
        )

    @staticmethod
    def owner_groups_with_members(user):
        return TemplateShareGroup.objects.filter(owner=user).prefetch_related("members")

    @staticmethod
    def owner_groups_with_members_ordered(user):
        return TemplateShareGroup.objects.filter(owner=user).prefetch_related("members").order_by("name")

    @staticmethod
    def owner_workspaces_ordered(user):
        return Workspace.objects.filter(owner=user).order_by("name")

    @staticmethod
    def notifications_for_user(user, limit=8):
        return UserNotification.objects.filter(user=user).order_by("-created_at")[:limit]

    @staticmethod
    def unread_notifications_count(user):
        return UserNotification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def mark_all_notifications_read(user):
        return UserNotification.objects.filter(user=user, is_read=False).update(is_read=True)

    @staticmethod
    def template_permissions_for_owned_templates(owned_template_ids):
        return (
            TemplatePermission.objects.select_related("user", "template")
            .filter(template_id__in=owned_template_ids)
            .exclude(role=AccessRole.OWNER)
        )

    @staticmethod
    def pending_invites_for_owned_templates(owned_template_ids):
        return TemplateInvite.objects.filter(template_id__in=owned_template_ids, status=InviteStatus.PENDING)

    @staticmethod
    def accessible_templates(user, base_queryset):
        return base_queryset.filter(
            Q(owner=user)
            | Q(permissions__user=user)
            | Q(workspace__memberships__user=user, workspace__memberships__is_active=True)
        ).distinct()
