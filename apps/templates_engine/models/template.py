import uuid

from django.conf import settings
from django.db import models

from .choices import AccessRole, AuditAction, InviteStatus, TemplateFileType, TemplateStatus
from .workspace import Workspace


class DocumentTemplate(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_templates")
    workspace = models.ForeignKey(Workspace, on_delete=models.SET_NULL, blank=True, null=True, related_name="templates")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="templates/")
    file_type = models.CharField(max_length=8, choices=TemplateFileType.choices)
    fields_schema = models.JSONField(default=list, help_text="Lista de campos detectados no template.")
    status = models.CharField(max_length=16, choices=TemplateStatus.choices, default=TemplateStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class TemplatePermission(models.Model):
    template = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE, related_name="permissions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="template_permissions")
    role = models.CharField(max_length=16, choices=AccessRole.choices, default=AccessRole.FILLER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("template", "user")

    def __str__(self) -> str:
        return f"{self.user} -> {self.template} ({self.role})"


class TemplateShareGroup(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="template_share_groups")
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("owner", "name")

    def __str__(self) -> str:
        return f"{self.name} ({self.owner_id})"


class TemplateShareGroupMember(models.Model):
    group = models.ForeignKey(TemplateShareGroup, on_delete=models.CASCADE, related_name="members")
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "email")
        ordering = ["email"]

    def __str__(self) -> str:
        return f"{self.email} -> {self.group.name}"


class TemplateSubmission(models.Model):
    template = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE, related_name="submissions")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="template_submissions",
    )
    payload = models.JSONField(default=dict)
    output_file = models.FileField(upload_to="generated/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Submission #{self.pk} - {self.template.name}"


class TemplateInvite(models.Model):
    template = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE, related_name="invites")
    invited_email = models.EmailField()
    role = models.CharField(max_length=16, choices=AccessRole.choices, default=AccessRole.FILLER)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=16, choices=InviteStatus.choices, default=InviteStatus.PENDING)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_template_invites",
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="accepted_template_invites",
    )
    accepted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Invite {self.invited_email} -> {self.template.name}"


class TemplateAuditLog(models.Model):
    template = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=64, choices=AuditAction.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="template_audit_logs",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.template.name} - {self.action}"
