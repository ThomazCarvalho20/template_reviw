from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.templates_engine.models import WorkspaceMemberRole, WorkspaceMembership

User = get_user_model()


class WorkspaceService:
    def __init__(self, access_service):
        self.access_service = access_service

    def touch_presence(self, workspace, user):
        membership = self.access_service.get_workspace_membership(workspace, user)
        if not membership:
            return
        membership.last_seen_at = timezone.now()
        membership.save(update_fields=["last_seen_at", "updated_at"])

    @staticmethod
    def add_members_by_email(workspace, emails):
        added = 0
        missing = []
        for email in emails:
            target_user = User.objects.filter(email__iexact=email).first()
            if not target_user:
                missing.append(email)
                continue
            WorkspaceMembership.objects.update_or_create(
                workspace=workspace,
                user=target_user,
                defaults={
                    "is_active": True,
                    "role": WorkspaceMemberRole.MEMBER,
                },
            )
            added += 1
        return added, missing
