from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from apps.templates_engine.forms import TemplateShareGroupCreateForm, TemplateShareGroupUpdateForm
from apps.templates_engine.models import TemplateShareGroup, TemplateShareGroupMember, Workspace
from .shared import template_selector, template_sharing_service


class GroupListView(LoginRequiredMixin, TemplateView):
    template_name = "templates_engine/group_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["groups"] = template_selector.owner_groups_with_members(self.request.user)
        return context


class GroupDetailView(LoginRequiredMixin, TemplateView):
    template_name = "templates_engine/group_detail.html"

    def _get_group(self):
        return get_object_or_404(
            TemplateShareGroup.objects.prefetch_related("members"),
            pk=self.kwargs["group_id"],
            owner=self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self._get_group()
        members_raw = ", ".join(group.members.values_list("email", flat=True))
        context["group"] = group
        context["group_update_form"] = kwargs.get("group_update_form") or TemplateShareGroupUpdateForm(
            initial={"name": group.name, "members_raw": members_raw}
        )
        context["workspaces"] = template_selector.owner_workspaces_ordered(self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        group = self._get_group()
        action = (request.POST.get("action") or "").strip()

        if action == "update_group":
            form = TemplateShareGroupUpdateForm(request.POST)
            if not form.is_valid():
                messages.error(request, "Nao foi possivel atualizar o grupo.")
                return self.render_to_response(self.get_context_data(group_update_form=form))

            group.name = form.cleaned_data["name"]
            group.save(update_fields=["name"])

            desired_emails = set(form.cleaned_data["members_raw"])
            current_members = {m.email: m for m in group.members.all()}
            current_emails = set(current_members.keys())

            to_add = desired_emails - current_emails
            to_remove = current_emails - desired_emails
            if to_add:
                TemplateShareGroupMember.objects.bulk_create(
                    [TemplateShareGroupMember(group=group, email=email) for email in sorted(to_add)]
                )
            if to_remove:
                TemplateShareGroupMember.objects.filter(group=group, email__in=to_remove).delete()

            messages.success(request, "Grupo atualizado com sucesso.")
            return redirect("group-detail", group_id=group.pk)

        if action in {"add_group_to_workspace", "remove_group_from_workspace"}:
            workspace_id = request.POST.get("workspace_id")
            workspace = get_object_or_404(Workspace, pk=workspace_id, owner=request.user)
            if action == "add_group_to_workspace":
                added, missing = template_sharing_service.add_group_members_to_workspace(group, workspace)
                if added:
                    messages.success(request, f"{added} membro(s) adicionados ao ambiente '{workspace.name}'.")
                if missing:
                    messages.warning(request, f"Sem cadastro no sistema: {', '.join(missing)}")
                return redirect("group-detail", group_id=group.pk)

            removed, skipped = template_sharing_service.remove_group_members_from_workspace(group, workspace)
            if removed:
                messages.success(request, f"{removed} membro(s) removidos do ambiente '{workspace.name}'.")
            if skipped:
                messages.info(request, "Criador do ambiente foi preservado automaticamente.")
            return redirect("group-detail", group_id=group.pk)

        messages.error(request, "Acao invalida.")
        return redirect("group-detail", group_id=group.pk)


class TemplateShareGroupCreateView(LoginRequiredMixin, View):
    def post(self, request):
        form = TemplateShareGroupCreateForm(request.POST)
        if not form.is_valid():
            for _, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect("group-list")
        group = form.save(owner=request.user)
        messages.success(request, f"Grupo '{group.name}' criado com {group.members.count()} membro(s).")
        return redirect("group-list")
