from apps.core.domain.selectors import CoreSelector
from apps.templates_engine.domain.institution import visible_submissions


class DashboardService:
    selector = CoreSelector()

    @staticmethod
    def get_user_settings(user):
        return CoreSelector.user_settings(user)

    def get_items_limit(self, user, fallback=10):
        settings_obj = self.get_user_settings(user)
        return settings_obj.items_per_page or fallback

    @staticmethod
    def get_recent_templates_and_submissions(user, limit):
        templates_qs = CoreSelector.accessible_templates(user)
        template_ids = templates_qs.values_list("id", flat=True)
        submissions_qs = visible_submissions(
            user, CoreSelector.template_submissions_for_template_ids(template_ids)
        )
        return templates_qs[:limit], submissions_qs[:limit]
