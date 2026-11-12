from apps.templates_engine.domain.institution import can_manage_institution, is_institution_member
from apps.templates_engine.domain.selectors import TemplateEngineSelector
from apps.templates_engine.models import (
    AccessRole,
    TemplatePermission,
    WorkspaceMemberRole,
    WorkspaceMembership,
)


class TemplateAccessService:
    selector = TemplateEngineSelector()

    @staticmethod
    def is_workspace_member(workspace, user):
        return WorkspaceMembership.objects.filter(
            workspace=workspace, user=user, is_active=True
        ).exists()

    @staticmethod
    def get_workspace_membership(workspace, user):
        return WorkspaceMembership.objects.filter(
            workspace=workspace, user=user, is_active=True
        ).first()

    def resolve_user_role(self, template_obj, user):
        if user.is_superuser:
            return AccessRole.EDITOR
        if template_obj.institution_id:
            if not template_obj.institution.is_active:
                return None
            if can_manage_institution(template_obj.institution_id, user):
                return AccessRole.EDITOR
        elif template_obj.owner_id == user.id:
            return AccessRole.OWNER
        permission = (
            TemplatePermission.objects.filter(template=template_obj, user=user)
            .exclude(role=AccessRole.OWNER)
            .first()
        )
        if permission:
            return permission.role
        if template_obj.workspace_id and self.is_workspace_member(template_obj.workspace, user):
            return WorkspaceMemberRole.MEMBER
        if template_obj.institution_id and is_institution_member(template_obj.institution_id, user):
            return AccessRole.FILLER
        return None

    def user_can_access_template(self, template_obj, user):
        return self.resolve_user_role(template_obj, user) is not None

    @staticmethod
    def get_accessible_templates_queryset(user, base_qs):
        return TemplateEngineSelector.accessible_templates(user, base_qs)
