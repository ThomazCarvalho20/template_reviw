from django.contrib import admin

from apps.templates_engine.models import (
    DocumentRequest,
    DocumentRequestEvent,
    DocumentTemplate,
    Institution,
    InstitutionMembership,
    SubmissionShare,
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


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_email", "is_active"]
    search_fields = ["name", "contact_email"]
    list_filter = ["is_active"]


@admin.register(InstitutionMembership)
class InstitutionMembershipAdmin(admin.ModelAdmin):
    list_display = ["institution", "user", "role", "is_active"]
    list_filter = ["institution", "role", "is_active"]

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission


@admin.register(DocumentRequest)
class DocumentRequestAdmin(admin.ModelAdmin):
    list_display = ["protocol", "institution", "requester", "status", "assigned_to"]
    list_filter = ["institution", "status"]
    readonly_fields = [field.name for field in DocumentRequest._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DocumentRequestEvent)
class DocumentRequestEventAdmin(DocumentRequestAdmin):
    list_display = ["request", "actor", "status", "created_at"]
    list_filter = ["status"]
    readonly_fields = [field.name for field in DocumentRequestEvent._meta.fields]


@admin.register(SubmissionShare)
class SubmissionShareAdmin(DocumentRequestAdmin):
    list_display = ["submission", "user", "created_at"]
    list_filter = []
    readonly_fields = [field.name for field in SubmissionShare._meta.fields]
