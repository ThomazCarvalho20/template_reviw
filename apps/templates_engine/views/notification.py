from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.views import View

from apps.templates_engine.models import UserNotification
from .shared import template_selector


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, notification_id):
        notification = get_object_or_404(UserNotification, pk=notification_id, user=request.user)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return redirect(request.POST.get("next") or "dashboard")


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        template_selector.mark_all_notifications_read(request.user)
        return redirect(request.POST.get("next") or "dashboard")


class NotificationFeedView(LoginRequiredMixin, View):
    def get(self, request):
        notifications = template_selector.notifications_for_user(request.user, limit=8)
        unread_count = template_selector.unread_notifications_count(request.user)
        html = render_to_string(
            "templates_engine/partials/notifications_panel_content.html",
            {
                "nav_notifications": notifications,
                "nav_notifications_unread_count": unread_count,
            },
            request=request,
        )
        return JsonResponse({"ok": True, "unread_count": unread_count, "html": html})
