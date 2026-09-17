from django.conf import settings

from apps.core.domain.selectors import CoreSelector


class NavigationService:
    @staticmethod
    def build_navigation_context(request):
        if not request.user.is_authenticated:
            return {
                "nav_user_settings": None,
                "nav_notifications": [],
                "nav_notifications_unread_count": 0,
                "app_version": getattr(settings, "APP_VERSION", "1.0.0"),
            }

        settings_obj = CoreSelector.user_settings(request.user)
        notifications = CoreSelector.notifications_for_user(request.user, limit=8)
        unread_count = CoreSelector.unread_notifications_count(request.user)
        return {
            "nav_user_settings": settings_obj,
            "nav_notifications": notifications,
            "nav_notifications_unread_count": unread_count,
            "app_version": getattr(settings, "APP_VERSION", "1.0.0"),
        }
