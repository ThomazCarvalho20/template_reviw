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
        return WorkspaceMembership.objects.filter(workspace=workspace, user=user, is_active=True).exists()

    @staticmethod
    def get_workspace_membership(workspace, user):
        return WorkspaceMembership.objects.filter(workspace=workspace, user=user, is_active=True).first()

    def resolve_user_role(self, template_obj, user):
        if template_obj.owner_id == user.id:
            return AccessRole.OWNER
        permission = TemplatePermission.objects.filter(template=template_obj, user=user).first()
        if permission:
            return permission.role
        if template_obj.workspace_id and self.is_workspace_member(template_obj.workspace, user):
            return WorkspaceMemberRole.MEMBER
        return None

    def user_can_access_template(self, template_obj, user):
        return (
            template_obj.owner_id == user.id
            or TemplatePermission.objects.filter(template=template_obj, user=user).exists()
            or (template_obj.workspace_id and self.is_workspace_member(template_obj.workspace, user))
        )

    @staticmethod
    def get_accessible_templates_queryset(user, base_qs):
        return TemplateEngineSelector.accessible_templates(user, base_qs)
