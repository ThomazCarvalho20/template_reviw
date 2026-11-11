import uuid

from django.conf import settings
from django.db import models


class Institution(models.Model):
    name = models.CharField("Nome", max_length=200, unique=True)
    description = models.TextField("Descrição", blank=True)
    contact_email = models.EmailField("E-mail de contato", blank=True)
    is_active = models.BooleanField("Ativa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Instituição"
        verbose_name_plural = "Instituições"

    def __str__(self):
        return self.name


class InstitutionMembership(models.Model):
    class Role(models.TextChoices):
        MANAGER = "manager", "Instituição — responsável"
        MEMBER = "member", "Usuário"

    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="institution_memberships"
    )
    role = models.CharField("Perfil", max_length=16, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField("Ativo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["institution", "user"], name="unique_institution_user")
        ]
        verbose_name = "Vínculo institucional"
        verbose_name_plural = "Vínculos institucionais"

    def __str__(self):
        return f"{self.user} — {self.institution}"


class DocumentRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        IN_REVIEW = "in_review", "Em análise"
        APPROVED = "approved", "Aprovada"
        REJECTED = "rejected", "Indeferida"
        CANCELED = "canceled", "Cancelada"

    protocol = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    submission = models.OneToOneField(
        "templates_engine.TemplateSubmission",
        on_delete=models.PROTECT,
        related_name="document_request",
    )
    institution = models.ForeignKey(
        Institution, on_delete=models.PROTECT, related_name="document_requests"
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="document_requests"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_document_requests",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    revision = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Solicitação de documento"
        verbose_name_plural = "Solicitações de documentos"

    def __str__(self):
        return f"ED-{self.protocol}"


class DocumentRequestEvent(models.Model):
    request = models.ForeignKey(DocumentRequest, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=16, choices=DocumentRequest.Status.choices)
    note = models.TextField(blank=True, max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"{self.request_id}: {self.status}"


class SubmissionShare(models.Model):
    submission = models.ForeignKey(
        "templates_engine.TemplateSubmission", on_delete=models.CASCADE, related_name="shares"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shared_submissions"
    )
    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "user"], name="unique_submission_recipient"
            )
        ]

    def __str__(self):
        return f"{self.submission_id} → {self.user_id}"
