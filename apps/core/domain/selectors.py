from apps.core.models import UserSettings
from apps.templates_engine.domain.selectors import TemplateEngineSelector
from apps.templates_engine.models import DocumentTemplate, TemplateSubmission, UserNotification


class CoreSelector:
    @staticmethod
    def user_settings(user):
        settings_obj, _ = UserSettings.objects.get_or_create(user=user)
        return settings_obj

    @staticmethod
    def accessible_templates(user):
        return (
            TemplateEngineSelector.accessible_templates(user, DocumentTemplate.objects.all())
            .distinct()
            .select_related("owner")
            .order_by("-updated_at")
        )

    @staticmethod
    def template_submissions_for_template_ids(template_ids):
        return TemplateSubmission.objects.filter(template_id__in=template_ids).select_related(
            "template", "submitted_by"
        )

    @staticmethod
    def notifications_for_user(user, limit=8):
        return UserNotification.objects.filter(user=user).order_by("-created_at")[:limit]

    @staticmethod
    def unread_notifications_count(user):
        return UserNotification.objects.filter(user=user, is_read=False).count()
