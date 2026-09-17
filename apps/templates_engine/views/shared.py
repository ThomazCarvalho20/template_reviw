from apps.core.models import UserSettings
from apps.templates_engine.domain import (
    TemplateAccessService,
    TemplateEngineSelector,
    TemplateFilterService,
    TemplateSharingService,
    WorkspaceService,
)


template_access_service = TemplateAccessService()
template_selector = TemplateEngineSelector()
workspace_service = WorkspaceService(template_access_service)
template_filter_service = TemplateFilterService()
template_sharing_service = TemplateSharingService()


def get_user_items_per_page(user, fallback=10):
    settings_obj, _ = UserSettings.objects.get_or_create(user=user)
    return settings_obj.items_per_page or fallback
