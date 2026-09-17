from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.urls import reverse

from apps.templates_engine.audit import log_template_action
from apps.templates_engine.models import (
    AuditAction,
    InviteStatus,
    TemplateInvite,
    TemplatePermission,
    WorkspaceMemberRole,
    WorkspaceMembership,
)

User = get_user_model()


class TemplateSharingService:
    @staticmethod
    def share_template_with_group(request, template_obj, group, role):
        members = group.members.all()

        granted = 0
        invited = 0
        skipped_owner = 0
        for member in members:
            email = member.email.strip().lower()
            target_user = User.objects.filter(email__iexact=email).first()
            if target_user:
                if target_user.id == request.user.id:
                    skipped_owner += 1
                    continue
                TemplatePermission.objects.update_or_create(
                    template=template_obj,
                    user=target_user,
                    defaults={"role": role},
                )
                granted += 1
                continue

            invite, _ = TemplateInvite.objects.update_or_create(
                template=template_obj,
                invited_email=email,
                status=InviteStatus.PENDING,
                defaults={"role": role, "created_by": request.user},
            )
            accept_url = request.build_absolute_uri(reverse("template-invite-accept", kwargs={"token": invite.token}))
            send_mail(
                subject=f"Convite para template: {template_obj.name}",
                message=(
                    f"Voce recebeu um convite para colaborar no template '{template_obj.name}'.\n\n"
                    f"Acesse para aceitar: {accept_url}\n\n"
                    "Se voce ainda nao possui conta, cadastre-se e depois acesse o mesmo link."
                ),
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
            )
            invited += 1

        log_template_action(
            template=template_obj,
            action=AuditAction.TEMPLATE_SHARED,
            actor=request.user,
            metadata={
                "share_mode": "group",
                "group_id": group.pk,
                "group_name": group.name,
                "role": role,
                "granted_count": granted,
                "invited_count": invited,
                "skipped_owner_count": skipped_owner,
            },
        )
        return granted, invited

    @staticmethod
    def add_group_members_to_workspace(group, workspace):
        added = 0
        missing = []
        for member in group.members.all():
            target_user = User.objects.filter(email__iexact=member.email).first()
            if not target_user:
                missing.append(member.email)
                continue
            WorkspaceMembership.objects.update_or_create(
                workspace=workspace,
                user=target_user,
                defaults={"is_active": True, "role": WorkspaceMemberRole.MEMBER},
            )
            added += 1
        return added, missing

    @staticmethod
    def remove_group_members_from_workspace(group, workspace):
        removed = 0
        skipped = 0
        for member in group.members.all():
            target_user = User.objects.filter(email__iexact=member.email).first()
            if not target_user:
                continue
            if target_user.id == workspace.owner_id:
                skipped += 1
                continue
            membership = WorkspaceMembership.objects.filter(workspace=workspace, user=target_user, is_active=True).first()
            if not membership:
                continue
            membership.is_active = False
            membership.save(update_fields=["is_active", "updated_at"])
            removed += 1
        return removed, skipped
