from django.db import connection
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.core.domain import DashboardService, SettingsService
from apps.core.forms import ProfileForm, ProfilePhotoForm, UserSettingsForm


dashboard_service = DashboardService()
settings_service = SettingsService()


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        limit = dashboard_service.get_items_limit(self.request.user)
        recent_templates, recent_submissions = dashboard_service.get_recent_templates_and_submissions(
            self.request.user,
            limit,
        )

        context["items_limit"] = limit
        context["recent_templates"] = recent_templates
        context["recent_submissions"] = recent_submissions
        return context


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = "core/settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings_obj = settings_service.get_user_settings(self.request.user)
        context["profile_form"] = kwargs.get("profile_form") or ProfileForm(instance=self.request.user)
        context["profile_photo_form"] = kwargs.get("profile_photo_form") or ProfilePhotoForm(instance=settings_obj)
        context["settings_form"] = kwargs.get("settings_form") or UserSettingsForm(instance=settings_obj)
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        settings_obj = settings_service.get_user_settings(request.user)

        if action == "profile":
            profile_form = ProfileForm(request.POST, instance=request.user)
            profile_photo_form = ProfilePhotoForm(request.POST, request.FILES, instance=settings_obj)
            settings_form = UserSettingsForm(instance=settings_obj)
            if profile_form.is_valid() and profile_photo_form.is_valid():
                cropped_data = (request.POST.get("profile_photo_cropped_data") or "").strip()

                profile_form.save()
                profile_photo_form.save()

                if cropped_data:
                    saved = settings_service.save_cropped_profile_photo(request.user, settings_obj, cropped_data)
                    if not saved:
                        messages.warning(
                            request,
                            "Nao foi possivel aplicar o recorte da foto. O upload original foi mantido.",
                        )

                settings_service.force_header_profile_scope(settings_obj)
                messages.success(request, "Perfil atualizado com sucesso.")
                return redirect("settings")
            messages.error(request, "Nao foi possivel salvar o perfil. Verifique os campos.")
            return self.render_to_response(
                self.get_context_data(
                    profile_form=profile_form,
                    profile_photo_form=profile_photo_form,
                    settings_form=settings_form,
                )
            )

        if action == "preferences":
            profile_form = ProfileForm(instance=request.user)
            profile_photo_form = ProfilePhotoForm(instance=settings_obj)
            settings_form = UserSettingsForm(request.POST, instance=settings_obj)
            if settings_form.is_valid():
                settings_form.save()
                messages.success(request, "Preferencias atualizadas com sucesso.")
                return redirect("settings")
            messages.error(request, "Nao foi possivel salvar as preferencias.")
            return self.render_to_response(
                self.get_context_data(
                    profile_form=profile_form,
                    profile_photo_form=profile_photo_form,
                    settings_form=settings_form,
                )
            )

        messages.error(request, "Acao invalida.")
        return redirect("settings")


def healthcheck_view(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_status = "ok"
    except Exception:
        db_status = "error"
    status_code = 200 if db_status == "ok" else 503
    return JsonResponse({"status": "ok" if status_code == 200 else "degraded", "database": db_status}, status=status_code)
