from django.urls import path

from apps.core.views import DashboardView, SettingsView, healthcheck_view


urlpatterns = [
    path("healthz/", healthcheck_view, name="healthcheck"),
    path("configuracoes/", SettingsView.as_view(), name="settings"),
    path("", DashboardView.as_view(), name="dashboard"),
]
