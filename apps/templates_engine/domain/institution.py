from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.templates_engine.models import (
    DocumentRequest,
    DocumentRequestEvent,
    Institution,
    InstitutionMembership,
    TemplateSubmission,
    UserNotification,
)


def managed_institutions(user):
    queryset = Institution.objects.filter(is_active=True)
    if user.is_superuser:
        return queryset
    return queryset.filter(
        memberships__user=user, memberships__role="manager", memberships__is_active=True
    )


def is_institution_member(institution_id, user):
    return (
        user.is_superuser
        or InstitutionMembership.objects.filter(
            institution_id=institution_id,
            institution__is_active=True,
            user=user,
            is_active=True,
        ).exists()
    )


def can_manage_institution(institution_id, user):
    return user.is_superuser or managed_institutions(user).filter(pk=institution_id).exists()


def can_manage_template(template, user):
    return (
        user.is_superuser
        or (template.institution_id is None and template.owner_id == user.pk)
        or (template.institution_id and can_manage_institution(template.institution_id, user))
    )


def visible_submissions(user, queryset=None):
    queryset = TemplateSubmission.objects.all() if queryset is None else queryset
    if user.is_superuser:
        return queryset
    return queryset.filter(
        Q(submitted_by=user)
        | Q(template__owner=user, template__institution__isnull=True)
        | Q(template__institution__in=managed_institutions(user))
    ).distinct()


def downloadable_submissions(user):
    if user.is_superuser:
        return TemplateSubmission.objects.all()
    return TemplateSubmission.objects.filter(
        Q(pk__in=visible_submissions(user).values("pk")) | Q(shares__user=user)
    ).distinct()


def visible_requests(user):
    queryset = DocumentRequest.objects.select_related(
        "institution", "requester", "assigned_to", "submission__template"
    )
    if user.is_superuser:
        return queryset
    return queryset.filter(
        Q(requester=user) | Q(institution__in=managed_institutions(user))
    ).distinct()


def user_profile(user):
    if user.is_superuser:
        return "Administrador"
    if managed_institutions(user).exists():
        return "Instituição"
    return "Usuário"


@transaction.atomic
def transition_request(request_id, actor, status, note, revision, assigned_to=None):
    request = DocumentRequest.objects.select_for_update().get(
        pk=request_id,
        pk__in=visible_requests(actor).values("pk"),
    )
    if request.revision != revision:
        raise ValidationError("A solicitação foi atualizada. Recarregue a página.")
    transitions = {
        "pending": {"in_review", "approved", "rejected", "canceled"},
        "in_review": {"in_review", "approved", "rejected", "canceled"},
        "approved": set(),
        "rejected": set(),
        "canceled": set(),
    }
    if status not in transitions[request.status]:
        raise ValidationError("Transição de situação inválida.")
    manager = can_manage_institution(request.institution_id, actor)
    if not manager and (actor.pk != request.requester_id or status != "canceled"):
        raise PermissionDenied
    if assigned_to and not manager:
        raise PermissionDenied
    if assigned_to and not can_manage_institution(request.institution_id, assigned_to):
        raise ValidationError("O responsável deve gerenciar esta instituição.")
    if status == "rejected" and not note.strip():
        raise ValidationError("Informe o motivo do indeferimento.")
    request.status = status
    if manager:
        request.assigned_to = assigned_to or actor
    request.revision += 1
    updated = DocumentRequest.objects.filter(pk=request.pk, revision=revision).update(
        status=status,
        assigned_to=request.assigned_to,
        revision=request.revision,
        updated_at=timezone.now(),
    )
    if not updated:
        raise ValidationError("A solicitação foi atualizada. Recarregue a página.")
    DocumentRequestEvent.objects.create(request=request, actor=actor, status=status, note=note)
    if actor.pk != request.requester_id:
        UserNotification.objects.create(
            user=request.requester,
            notification_type="document_request",
            title="Solicitação atualizada",
            message=f"{request}: {request.get_status_display()}",
            metadata={"request_id": request.pk},
        )
    return request
