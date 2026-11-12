from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.templates_engine.audit import log_template_action
from apps.templates_engine.domain.institution import can_manage_template
from apps.templates_engine.models import AuditAction, DocumentTemplate


class TemplateMetadataForm(forms.ModelForm):
    class Meta:
        model = DocumentTemplate
        fields = ["name", "description"]
        labels = {"name": "Nome", "description": "Descrição"}


class TemplateMetadataView(LoginRequiredMixin, View):
    def get_object(self, user, pk):
        obj = get_object_or_404(DocumentTemplate, pk=pk)
        if not can_manage_template(obj, user):
            raise PermissionDenied
        return obj

    def get(self, request, pk):
        obj = self.get_object(request.user, pk)
        return render(
            request,
            "templates_engine/template_metadata.html",
            {"form": TemplateMetadataForm(instance=obj), "template_obj": obj},
        )

    def post(self, request, pk):
        obj = self.get_object(request.user, pk)
        form = TemplateMetadataForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            log_template_action(
                template=obj, actor=request.user, action=AuditAction.TEMPLATE_UPDATED
            )
            messages.success(request, "Modelo atualizado.")
            return redirect("template-detail", pk=pk)
        return render(
            request, "templates_engine/template_metadata.html", {"form": form, "template_obj": obj}
        )
