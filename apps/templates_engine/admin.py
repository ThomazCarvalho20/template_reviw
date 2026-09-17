from django.contrib import admin

from apps.templates_engine.models import (
    DocumentTemplate,
    TemplateAuditLog,
    TemplateInvite,
    TemplatePermission,
    TemplateShareGroup,
    TemplateShareGroupMember,
    TemplateSubmission,
    UserNotification,
    Workspace,
    WorkspaceJoinRequest,
    WorkspaceMembership,
)


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "file_type", "status", "created_at")
    list_filter = ("file_type", "status")
    search_fields = ("name", "owner__username", "owner__email")


@admin.register(TemplatePermission)
class TemplatePermissionAdmin(admin.ModelAdmin):
    list_display = ("id", "template", "user", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("template__name", "user__username", "user__email")


@admin.register(TemplateSubmission)
class TemplateSubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "template", "submitted_by", "created_at")
    search_fields = ("template__name", "submitted_by__username", "submitted_by__email")


@admin.register(TemplateInvite)
class TemplateInviteAdmin(admin.ModelAdmin):
    list_display = ("id", "template", "invited_email", "role", "status", "created_at")
    list_filter = ("status", "role")
    search_fields = ("template__name", "invited_email")


@admin.register(TemplateAuditLog)
class TemplateAuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "template", "action", "actor", "created_at")
    list_filter = ("action",)
    search_fields = ("template__name", "actor__email")


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "created_at")
    search_fields = ("name", "owner__email")


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "workspace", "user", "role", "is_active", "last_seen_at")
    list_filter = ("role", "is_active")
    search_fields = ("workspace__name", "user__email")


@admin.register(WorkspaceJoinRequest)
class WorkspaceJoinRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "workspace", "requester", "status", "reviewed_by", "created_at")
    list_filter = ("status",)
    search_fields = ("workspace__name", "requester__email")


@admin.register(TemplateShareGroup)
class TemplateShareGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "created_at")
    search_fields = ("name", "owner__email")


@admin.register(TemplateShareGroupMember)
class TemplateShareGroupMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "group", "email", "created_at")
    search_fields = ("group__name", "email")


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "notification_type", "title", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("user__email", "title")
