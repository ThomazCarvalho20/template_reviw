from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.templates_engine.forms import (
    WorkspaceAddGroupForm,
    WorkspaceAddMembersForm,
    WorkspaceAttachTemplateForm,
    WorkspaceCreateForm,
)
from apps.templates_engine.models import (
    DocumentTemplate,
    NotificationType,
    UserNotification,
    Workspace,
    WorkspaceJoinRequest,
    WorkspaceJoinRequestStatus,
    WorkspaceMemberRole,
    WorkspaceMembership,
)

from .shared import (
    template_access_service,
    template_selector,
    template_sharing_service,
    workspace_service,
)


class WorkspaceListView(LoginRequiredMixin, TemplateView):
    template_name = "templates_engine/workspace_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["memberships"] = template_selector.workspace_memberships_for_user(self.request.user)
        context["owned_workspaces"] = template_selector.owned_workspaces(self.request.user)
        context["workspace_form"] = kwargs.get("workspace_form") or WorkspaceCreateForm()
        context["pending_requests_for_owner"] = (
            template_selector.pending_workspace_requests_for_owner(self.request.user)
        )
        context["my_pending_requests"] = template_selector.my_pending_workspace_requests(
            self.request.user
        )
        return context


class WorkspaceCreateView(LoginRequiredMixin, View):
    def post(self, request):
        form = WorkspaceCreateForm(request.POST)
        if not form.is_valid():
            for _, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect("workspace-list")

        workspace = form.save(commit=False)
        workspace.owner = request.user
        workspace.save()
        WorkspaceMembership.objects.create(
            workspace=workspace,
            user=request.user,
            role=WorkspaceMemberRole.OWNER,
            is_active=True,
            last_seen_at=timezone.now(),
        )
        messages.success(request, f"Ambiente '{workspace.name}' criado com sucesso.")
        return redirect("workspace-detail", pk=workspace.pk)


class WorkspaceDetailView(LoginRequiredMixin, TemplateView):
    template_name = "templates_engine/workspace_detail.html"

    def get(self, request, *args, **kwargs):
        self.workspace = get_object_or_404(Workspace, pk=kwargs["pk"])
        membership = template_access_service.get_workspace_membership(self.workspace, request.user)
        if not membership:
            join_request, created = WorkspaceJoinRequest.objects.get_or_create(
                workspace=self.workspace,
                requester=request.user,
                status=WorkspaceJoinRequestStatus.PENDING,
                defaults={},
            )
            if created:
                UserNotification.objects.create(
                    user=self.workspace.owner,
                    notification_type=NotificationType.WORKSPACE_JOIN_REQUEST,
                    title="Nova solicitacao de entrada em ambiente",
                    message=f"{request.user.email} solicitou acesso ao ambiente '{self.workspace.name}'.",
                    metadata={"workspace_id": self.workspace.pk, "request_id": join_request.pk},
                )
            messages.warning(
                request, "Solicitacao enviada ao criador do ambiente. Aguarde aprovacao."
            )
            return redirect("workspace-list")

        workspace_service.touch_presence(self.workspace, request.user)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        membership = template_access_service.get_workspace_membership(
            self.workspace, self.request.user
        )
        context["workspace"] = self.workspace
        context["current_membership"] = membership
        context["can_manage"] = self.workspace.owner_id == self.request.user.id or (
            membership and membership.role in {WorkspaceMemberRole.OWNER, WorkspaceMemberRole.ADMIN}
        )

        active_memberships = self.workspace.memberships.select_related("user").filter(
            is_active=True
        )
        online_threshold = timezone.now() - timezone.timedelta(minutes=2)
        context["memberships"] = active_memberships
        context["online_memberships"] = active_memberships.filter(
            last_seen_at__gte=online_threshold
        )
        context["workspace_templates"] = self.workspace.templates.select_related("owner")

        accessible_templates = template_access_service.get_accessible_templates_queryset(
            self.request.user,
            DocumentTemplate.objects.all(),
        )
        context["available_templates"] = accessible_templates.exclude(workspace=self.workspace)
        context["add_members_form"] = WorkspaceAddMembersForm()
        context["add_group_form"] = WorkspaceAddGroupForm(owner=self.request.user)
        context["share_groups_for_owner"] = template_selector.owner_groups_with_members(
            self.request.user
        )
        context["attach_template_form"] = WorkspaceAttachTemplateForm(
            owner=self.request.user, workspace=self.workspace
        )
        return context


class WorkspaceTemplateListView(LoginRequiredMixin, TemplateView):
    template_name = "templates_engine/workspace_templates.html"

    def get(self, request, *args, **kwargs):
        self.workspace = get_object_or_404(Workspace, pk=kwargs["pk"])
        membership = template_access_service.get_workspace_membership(self.workspace, request.user)
        if not membership:
            messages.warning(request, "Voce precisa participar do ambiente para ver os templates.")
            return redirect("workspace-detail", pk=self.workspace.pk)
        workspace_service.touch_presence(self.workspace, request.user)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()
        templates_qs = self.workspace.templates.select_related("owner")
        if q:
            templates_qs = templates_qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        context["workspace"] = self.workspace
        context["templates"] = templates_qs
        context["current_q"] = q
        return context


class WorkspaceHeartbeatView(LoginRequiredMixin, View):
    def post(self, request, pk):
        workspace = get_object_or_404(Workspace, pk=pk)
        if not template_access_service.is_workspace_member(workspace, request.user):
            return JsonResponse({"ok": False}, status=403)
        workspace_service.touch_presence(workspace, request.user)
        return JsonResponse({"ok": True})


class WorkspaceJoinRequestDecisionView(LoginRequiredMixin, View):
    def post(self, request, request_id):
        decision = (request.POST.get("decision") or "").strip()
        join_request = get_object_or_404(WorkspaceJoinRequest, pk=request_id)
        if join_request.workspace.owner_id != request.user.id:
            messages.error(request, "Somente o criador pode aprovar solicitacoes.")
            return redirect("workspace-list")
        if join_request.status != WorkspaceJoinRequestStatus.PENDING:
            messages.info(request, "Solicitacao ja foi processada.")
            return redirect("workspace-list")

        if decision == "approve":
            join_request.status = WorkspaceJoinRequestStatus.APPROVED
            WorkspaceMembership.objects.update_or_create(
                workspace=join_request.workspace,
                user=join_request.requester,
                defaults={
                    "is_active": True,
                    "role": WorkspaceMemberRole.MEMBER,
                    "last_seen_at": timezone.now(),
                },
            )
            messages.success(request, "Solicitacao aprovada.")
        elif decision == "reject":
            join_request.status = WorkspaceJoinRequestStatus.REJECTED
            messages.info(request, "Solicitacao rejeitada.")
        else:
            messages.error(request, "Acao invalida.")
            return redirect("workspace-list")

        join_request.reviewed_by = request.user
        join_request.reviewed_at = timezone.now()
        join_request.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        return redirect("workspace-list")


class WorkspaceLeaveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        workspace = get_object_or_404(Workspace, pk=pk)
        if workspace.owner_id == request.user.id:
            messages.error(request, "O criador nao pode sair do proprio ambiente.")
            return redirect("workspace-detail", pk=workspace.pk)

        membership = template_access_service.get_workspace_membership(workspace, request.user)
        if not membership:
            messages.info(request, "Voce nao esta neste ambiente.")
            return redirect("workspace-list")
        membership.is_active = False
        membership.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "Voce saiu do ambiente.")
        return redirect("workspace-list")


class WorkspaceRemoveMemberView(LoginRequiredMixin, View):
    def post(self, request, pk, membership_id):
        workspace = get_object_or_404(Workspace, pk=pk)
        if workspace.owner_id != request.user.id:
            messages.error(request, "Somente o criador pode remover membros.")
            return redirect("workspace-detail", pk=workspace.pk)

        membership = get_object_or_404(WorkspaceMembership, pk=membership_id, workspace=workspace)
        if membership.user_id == request.user.id:
            messages.error(request, "Use a opcao de gerenciamento do ambiente para esse caso.")
            return redirect("workspace-detail", pk=workspace.pk)

        membership.is_active = False
        membership.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "Membro removido do ambiente.")
        return redirect("workspace-detail", pk=workspace.pk)


class WorkspaceAddMembersView(LoginRequiredMixin, View):
    def post(self, request, pk):
        workspace = get_object_or_404(Workspace, pk=pk)
        if workspace.owner_id != request.user.id:
            messages.error(request, "Somente o criador pode adicionar membros.")
            return redirect("workspace-detail", pk=workspace.pk)

        form = WorkspaceAddMembersForm(request.POST)
        if not form.is_valid():
            for _, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect("workspace-detail", pk=workspace.pk)

        added, missing = workspace_service.add_members_by_email(
            workspace, form.cleaned_data["members_raw"]
        )

        if added:
            messages.success(request, f"{added} pessoa(s) adicionada(s) ao ambiente.")
        if missing:
            messages.warning(request, f"Nao cadastrados no sistema: {', '.join(missing)}")
        return redirect("workspace-detail", pk=workspace.pk)


class WorkspaceAddGroupView(LoginRequiredMixin, View):
    def post(self, request, pk):
        workspace = get_object_or_404(Workspace, pk=pk)
        if workspace.owner_id != request.user.id:
            messages.error(request, "Somente o criador pode adicionar grupo ao ambiente.")
            return redirect("workspace-detail", pk=workspace.pk)

        form = WorkspaceAddGroupForm(request.POST, owner=request.user)
        if not form.is_valid():
            for _, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect("workspace-detail", pk=workspace.pk)

        group = get_object_or_404(
            template_selector.owner_groups_with_members(request.user),
            pk=form.cleaned_data["group_id"],
        )
        added, missing = template_sharing_service.add_group_members_to_workspace(group, workspace)

        if added:
            messages.success(
                request, f"{added} membro(s) do grupo '{group.name}' adicionados ao ambiente."
            )
        if missing:
            messages.warning(request, f"Sem cadastro no sistema: {', '.join(missing)}")
        return redirect("workspace-detail", pk=workspace.pk)


class WorkspaceAttachTemplateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        workspace = get_object_or_404(Workspace, pk=pk)
        if not template_access_service.is_workspace_member(workspace, request.user):
            messages.error(request, "Apenas membros podem adicionar templates ao ambiente.")
            return redirect("workspace-detail", pk=workspace.pk)

        form = WorkspaceAttachTemplateForm(request.POST, owner=request.user, workspace=workspace)
        if not form.is_valid():
            for _, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect("workspace-detail", pk=workspace.pk)

        template_obj = get_object_or_404(DocumentTemplate, pk=form.cleaned_data["template_id"])
        if not template_access_service.user_can_access_template(template_obj, request.user):
            messages.error(request, "Voce nao pode vincular este template.")
            return redirect("workspace-detail", pk=workspace.pk)

        template_obj.workspace = workspace
        template_obj.save(update_fields=["workspace", "updated_at"])
        messages.success(request, "Template vinculado ao ambiente.")
        return redirect("workspace-detail", pk=workspace.pk)
