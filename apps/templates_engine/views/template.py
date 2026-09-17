import csv

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.templates_engine.audit import log_template_action
from apps.templates_engine.forms import (
    DynamicTemplateFillForm,
    TemplateInviteForm,
    TemplateShareForm,
    TemplateShareWithGroupForm,
    TemplateUploadForm,
)
from apps.templates_engine.models import (
    AccessRole,
    AuditAction,
    DocumentTemplate,
    InviteStatus,
    TemplateFileType,
    TemplateInvite,
    TemplatePermission,
    TemplateShareGroup,
    TemplateStatus,
    TemplateSubmission,
    Workspace,
    WorkspaceMemberRole,
)
from apps.templates_engine.services import detect_template_schema, generate_filled_document
from .shared import (
    get_user_items_per_page,
    template_access_service,
    template_filter_service,
    template_selector,
    template_sharing_service,
    workspace_service,
)

User = get_user_model()


class TemplateListView(LoginRequiredMixin, ListView):
    template_name = "templates_engine/template_list.html"
    model = DocumentTemplate
    context_object_name = "templates"
    paginate_by = 10

    def get_paginate_by(self, queryset):
        return get_user_items_per_page(self.request.user, self.paginate_by)

    def get_queryset(self):
        queryset = template_access_service.get_accessible_templates_queryset(
            self.request.user,
            DocumentTemplate.objects.all(),
        )

        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        file_type = (self.request.GET.get("file_type") or "").strip()

        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(description__icontains=q))
        if status in {TemplateStatus.ACTIVE, TemplateStatus.CLOSED}:
            queryset = queryset.filter(status=status)
        if file_type in {TemplateFileType.PDF, TemplateFileType.DOCX, TemplateFileType.XLSX}:
            queryset = queryset.filter(file_type=file_type)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        owned_ids = [tpl.id for tpl in context["templates"] if tpl.owner_id == self.request.user.id]
        context["permissions_by_template"] = {}
        context["pending_invites_by_template"] = {}
        if owned_ids:
            permissions = template_selector.template_permissions_for_owned_templates(owned_ids)
            invites = template_selector.pending_invites_for_owned_templates(owned_ids)
            for permission in permissions:
                context["permissions_by_template"].setdefault(permission.template_id, []).append(permission)
            for invite in invites:
                context["pending_invites_by_template"].setdefault(invite.template_id, []).append(invite)

        context["editable_roles"] = [
            (AccessRole.EDITOR, "Editor"),
            (AccessRole.FILLER, "Preenchedor"),
            (AccessRole.VIEWER, "Leitor"),
        ]
        context["current_q"] = (self.request.GET.get("q") or "").strip()
        context["current_status"] = (self.request.GET.get("status") or "").strip()
        context["current_file_type"] = (self.request.GET.get("file_type") or "").strip()
        context["status_options"] = TemplateStatus.choices
        context["file_type_options"] = TemplateFileType.choices
        context["share_groups"] = template_selector.owner_groups_with_members_ordered(self.request.user)
        return context


class TemplateCreateView(LoginRequiredMixin, CreateView):
    template_name = "templates_engine/template_create.html"
    form_class = TemplateUploadForm
    success_url = reverse_lazy("template-list")

    def form_valid(self, form):
        workspace = None
        workspace_id = self.request.POST.get("workspace_id") or self.request.GET.get("workspace")
        if workspace_id:
            workspace = get_object_or_404(Workspace, pk=workspace_id)
            if not template_access_service.is_workspace_member(workspace, self.request.user):
                messages.error(self.request, "Voce nao pertence a este ambiente.")
                return redirect("workspace-list")

        form.instance.owner = self.request.user
        form.instance.workspace = workspace
        response = super().form_valid(form)
        schema = detect_template_schema(self.object.file.path, self.object.file_type)
        self.object.fields_schema = schema
        self.object.save(update_fields=["fields_schema", "updated_at"])
        TemplatePermission.objects.get_or_create(
            template=self.object,
            user=self.request.user,
            defaults={"role": AccessRole.OWNER},
        )
        log_template_action(
            template=self.object,
            action=AuditAction.TEMPLATE_CREATED,
            actor=self.request.user,
            metadata={
                "file_type": self.object.file_type,
                "fields_detected": len(schema),
                "workspace_id": self.object.workspace_id,
            },
        )
        messages.success(self.request, "Template importado com sucesso.")
        return response


class TemplateFillView(LoginRequiredMixin, DetailView):
    template_name = "templates_engine/template_fill.html"
    model = DocumentTemplate
    context_object_name = "template_obj"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not template_access_service.user_can_access_template(obj, self.request.user):
            raise Http404("Template nao encontrado.")
        if obj.workspace_id:
            workspace_service.touch_presence(obj.workspace, self.request.user)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = DynamicTemplateFillForm(fields_schema=self.object.fields_schema)
        context["recent_submissions"] = self.object.submissions.select_related("submitted_by")[:10]
        role = template_access_service.resolve_user_role(self.object, self.request.user)
        context["can_submit"] = self.object.status == TemplateStatus.ACTIVE and role in {
            AccessRole.OWNER,
            AccessRole.EDITOR,
            AccessRole.FILLER,
            WorkspaceMemberRole.MEMBER,
        }
        context["current_role"] = role
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        role = template_access_service.resolve_user_role(self.object, request.user)
        if self.object.status != TemplateStatus.ACTIVE:
            messages.error(request, "Template encerrado. Nao e possivel enviar preenchimento.")
            return redirect("template-fill", pk=self.object.pk)
        if role not in {AccessRole.OWNER, AccessRole.EDITOR, AccessRole.FILLER, WorkspaceMemberRole.MEMBER}:
            messages.error(request, "Seu perfil possui acesso somente leitura para este template.")
            return redirect("template-fill", pk=self.object.pk)

        form = DynamicTemplateFillForm(request.POST, fields_schema=self.object.fields_schema)
        if not form.is_valid():
            context = self.get_context_data()
            context["form"] = form
            return self.render_to_response(context)

        submission = TemplateSubmission.objects.create(
            template=self.object,
            submitted_by=request.user,
            payload=form.cleaned_data,
        )
        rendered = generate_filled_document(self.object.file.path, self.object.file_type, form.cleaned_data)
        output_name = f"template_{self.object.pk}_submission_{submission.pk}.{self.object.file_type}"
        submission.output_file.save(output_name, ContentFile(rendered), save=True)

        log_template_action(
            template=self.object,
            action=AuditAction.TEMPLATE_FILLED,
            actor=request.user,
            metadata={"submission_id": submission.pk, "fields_count": len(form.cleaned_data)},
        )
        messages.success(request, "Preenchimento salvo com sucesso.")
        return redirect("template-fill", pk=self.object.pk)


class TemplateCloseView(LoginRequiredMixin, View):
    def post(self, request, pk):
        template_obj = get_object_or_404(DocumentTemplate, pk=pk)
        if template_obj.owner_id != request.user.id:
            messages.error(request, "Somente o dono pode encerrar o template.")
            return redirect("template-list")

        template_obj.status = TemplateStatus.CLOSED
        template_obj.closed_at = timezone.now()
        template_obj.save(update_fields=["status", "closed_at", "updated_at"])
        log_template_action(template=template_obj, action=AuditAction.TEMPLATE_CLOSED, actor=request.user)
        messages.success(request, "Template encerrado.")
        return redirect("template-list")


class TemplateShareView(LoginRequiredMixin, View):
    def post(self, request, pk):
        template_obj = get_object_or_404(DocumentTemplate, pk=pk)
        if template_obj.owner_id != request.user.id:
            messages.error(request, "Somente o dono pode compartilhar o template.")
            return redirect("template-list")

        form = TemplateShareForm(request.POST)
        if not form.is_valid():
            for _, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect("template-list")

        email = form.cleaned_data["email"]
        role = form.cleaned_data["role"]
        target_user = User.objects.filter(email__iexact=email).first()
        if not target_user:
            messages.error(request, "Usuario nao encontrado.")
            return redirect("template-list")
        if target_user.id == request.user.id:
            messages.error(request, "Nao e necessario compartilhar com o proprio dono.")
            return redirect("template-list")

        TemplatePermission.objects.update_or_create(
            template=template_obj,
            user=target_user,
            defaults={"role": role},
        )
        log_template_action(
            template=template_obj,
            action=AuditAction.TEMPLATE_SHARED,
            actor=request.user,
            metadata={"target_email": email, "role": role},
        )
        messages.success(request, f"Template compartilhado com {email}.")
        return redirect("template-list")


class TemplateInviteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        template_obj = get_object_or_404(DocumentTemplate, pk=pk)
        if template_obj.owner_id != request.user.id:
            messages.error(request, "Somente o dono pode convidar usuarios.")
            return redirect("template-list")

        form = TemplateInviteForm(request.POST)
        if not form.is_valid():
            for _, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect("template-list")

        invited_email = form.cleaned_data["email"].strip().lower()
        role = form.cleaned_data["role"]

        invite, _ = TemplateInvite.objects.update_or_create(
            template=template_obj,
            invited_email=invited_email,
            status=InviteStatus.PENDING,
            defaults={"role": role, "created_by": request.user},
        )

        accept_url = request.build_absolute_uri(reverse("template-invite-accept", kwargs={"token": invite.token}))
        send_mail(
            subject=f"Convite para template: {template_obj.name}",
            message=(
                f"Voce recebeu um convite para colaborar no template '{template_obj.name}'.\n\n"
                f"Acesse para aceitar: {accept_url}\n\n"
                "Se voce ainda nao possui conta, cadastre-se e depois acesse o mesmo link."
            ),
            from_email=None,
            recipient_list=[invited_email],
            fail_silently=False,
        )
        log_template_action(
            template=template_obj,
            action=AuditAction.TEMPLATE_INVITED,
            actor=request.user,
            metadata={"invited_email": invited_email, "role": role, "invite_id": invite.pk},
        )
        messages.success(request, f"Convite enviado para {invited_email}.")
        return redirect("template-list")


class TemplateShareWithGroupView(LoginRequiredMixin, View):
    def post(self, request, pk):
        template_obj = get_object_or_404(DocumentTemplate, pk=pk)
        if template_obj.owner_id != request.user.id:
            messages.error(request, "Somente o dono pode compartilhar o template.")
            return redirect("template-list")

        form = TemplateShareWithGroupForm(request.POST, owner=request.user)
        if not form.is_valid():
            for _, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect("template-list")

        group = get_object_or_404(TemplateShareGroup, pk=form.cleaned_data["group_id"], owner=request.user)
        role = form.cleaned_data["role"]
        granted, invited = template_sharing_service.share_template_with_group(request, template_obj, group, role)

        messages.success(
            request,
            f"Compartilhamento em grupo concluido. Permissoes: {granted} | Convites enviados: {invited}.",
        )
        return redirect("template-list")


class TemplateInviteAcceptView(LoginRequiredMixin, View):
    def get(self, request, token):
        invite = get_object_or_404(TemplateInvite, token=token)
        if invite.status != InviteStatus.PENDING:
            messages.info(request, "Este convite nao esta mais pendente.")
            return redirect("template-list")

        user_email = (request.user.email or "").strip().lower()
        if user_email != invite.invited_email.lower():
            messages.error(request, "Este convite pertence a outro e-mail.")
            return redirect("template-list")

        TemplatePermission.objects.update_or_create(
            template=invite.template,
            user=request.user,
            defaults={"role": invite.role},
        )
        invite.status = InviteStatus.ACCEPTED
        invite.accepted_by = request.user
        invite.accepted_at = timezone.now()
        invite.save(update_fields=["status", "accepted_by", "accepted_at"])
        log_template_action(
            template=invite.template,
            action=AuditAction.INVITE_ACCEPTED,
            actor=request.user,
            metadata={"invite_id": invite.pk, "email": user_email, "role": invite.role},
        )
        messages.success(request, f"Convite aceito para o template '{invite.template.name}'.")
        return redirect("template-fill", pk=invite.template_id)


class TemplatePermissionRevokeView(LoginRequiredMixin, View):
    def post(self, request, pk, permission_id):
        template_obj = get_object_or_404(DocumentTemplate, pk=pk)
        if template_obj.owner_id != request.user.id:
            messages.error(request, "Somente o dono pode revogar permissao.")
            return redirect("template-list")

        permission = get_object_or_404(TemplatePermission, pk=permission_id, template=template_obj)
        if permission.role == AccessRole.OWNER:
            messages.error(request, "Permissao de dono nao pode ser revogada por esta rota.")
            return redirect("template-list")

        target_email = permission.user.email
        target_role = permission.role
        permission.delete()
        log_template_action(
            template=template_obj,
            action=AuditAction.TEMPLATE_PERMISSION_REVOKED,
            actor=request.user,
            metadata={"target_email": target_email, "role": target_role},
        )
        messages.success(request, f"Permissao revogada para {target_email}.")
        return redirect("template-list")


class TemplatePermissionUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk, permission_id):
        template_obj = get_object_or_404(DocumentTemplate, pk=pk)
        if template_obj.owner_id != request.user.id:
            messages.error(request, "Somente o dono pode editar permissao.")
            return redirect("template-list")

        permission = get_object_or_404(TemplatePermission, pk=permission_id, template=template_obj)
        if permission.role == AccessRole.OWNER:
            messages.error(request, "Permissao de dono nao pode ser editada por esta rota.")
            return redirect("template-list")

        new_role = (request.POST.get("role") or "").strip()
        valid_roles = {AccessRole.EDITOR, AccessRole.FILLER, AccessRole.VIEWER}
        if new_role not in valid_roles:
            messages.error(request, "Role invalido.")
            return redirect("template-list")

        old_role = permission.role
        if old_role == new_role:
            messages.info(request, "Permissao ja esta nesse mesmo nivel.")
            return redirect("template-list")

        permission.role = new_role
        permission.save(update_fields=["role"])
        log_template_action(
            template=template_obj,
            action=AuditAction.TEMPLATE_PERMISSION_UPDATED,
            actor=request.user,
            metadata={"target_email": permission.user.email, "old_role": old_role, "new_role": new_role},
        )
        messages.success(request, f"Permissao atualizada para {permission.user.email}.")
        return redirect("template-list")


class TemplateInviteCancelView(LoginRequiredMixin, View):
    def post(self, request, pk, invite_id):
        template_obj = get_object_or_404(DocumentTemplate, pk=pk)
        if template_obj.owner_id != request.user.id:
            messages.error(request, "Somente o dono pode cancelar convites.")
            return redirect("template-list")

        invite = get_object_or_404(TemplateInvite, pk=invite_id, template=template_obj)
        if invite.status != InviteStatus.PENDING:
            messages.info(request, "Somente convites pendentes podem ser cancelados.")
            return redirect("template-list")

        invite.status = InviteStatus.CANCELED
        invite.save(update_fields=["status"])
        log_template_action(
            template=template_obj,
            action=AuditAction.INVITE_CANCELED,
            actor=request.user,
            metadata={"invited_email": invite.invited_email, "invite_id": invite.pk},
        )
        messages.success(request, f"Convite cancelado para {invite.invited_email}.")
        return redirect("template-list")


class TemplateAuditListView(LoginRequiredMixin, DetailView):
    template_name = "templates_engine/template_audit.html"
    model = DocumentTemplate
    context_object_name = "template_obj"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not template_access_service.user_can_access_template(obj, self.request.user):
            raise Http404("Template nao encontrado.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtered_logs = template_filter_service.get_filtered_audit_logs(self.request, self.object)
        paginator = Paginator(filtered_logs, get_user_items_per_page(self.request.user, 10))
        page_obj = paginator.get_page(self.request.GET.get("page"))
        context["audit_logs"] = page_obj.object_list
        context["page_obj"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()
        context["current_action"] = (self.request.GET.get("action") or "").strip()
        context["current_actor_email"] = (self.request.GET.get("actor_email") or "").strip()
        context["current_date_from"] = (self.request.GET.get("date_from") or "").strip()
        context["current_date_to"] = (self.request.GET.get("date_to") or "").strip()
        context["action_options"] = AuditAction.choices
        context["querystring"] = self.request.GET.urlencode()
        return context


class TemplateAuditExportCsvView(LoginRequiredMixin, View):
    def get(self, request, pk):
        template_obj = get_object_or_404(DocumentTemplate, pk=pk)
        if not template_access_service.user_can_access_template(template_obj, request.user):
            raise Http404("Template nao encontrado.")

        logs = template_filter_service.get_filtered_audit_logs(request, template_obj)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="template_{template_obj.pk}_audit.csv"'
        writer = csv.writer(response)
        writer.writerow(["timestamp", "action", "actor_email", "metadata"])
        for log in logs:
            writer.writerow([
                log.created_at.isoformat(),
                log.action,
                log.actor.email if log.actor else "",
                log.metadata,
            ])
        return response


class TemplateSubmissionExportCsvView(LoginRequiredMixin, View):
    def get(self, request, pk):
        template_obj = get_object_or_404(DocumentTemplate, pk=pk)
        if not template_access_service.user_can_access_template(template_obj, request.user):
            raise Http404("Template nao encontrado.")

        submissions = template_filter_service.get_filtered_submissions(request, template_obj)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="template_{template_obj.pk}_submissions.csv"'
        writer = csv.writer(response)
        writer.writerow(["id", "timestamp", "submitted_by_email", "output_file", "fields_count"])
        for submission in submissions:
            writer.writerow([
                submission.pk,
                submission.created_at.isoformat(),
                submission.submitted_by.email if submission.submitted_by else "",
                submission.output_file.url if submission.output_file else "",
                len(submission.payload or {}),
            ])
        return response


class TemplateDetailView(LoginRequiredMixin, DetailView):
    template_name = "templates_engine/template_detail.html"
    model = DocumentTemplate
    context_object_name = "template_obj"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not template_access_service.user_can_access_template(obj, self.request.user):
            raise Http404("Template nao encontrado.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = template_access_service.resolve_user_role(self.object, self.request.user)
        context["current_role"] = role
        context["can_submit"] = self.object.status == TemplateStatus.ACTIVE and role in {
            AccessRole.OWNER,
            AccessRole.EDITOR,
            AccessRole.FILLER,
            WorkspaceMemberRole.MEMBER,
        }
        filtered_submissions = template_filter_service.get_filtered_submissions(self.request, self.object)
        submissions_paginator = Paginator(filtered_submissions, get_user_items_per_page(self.request.user, 10))
        submissions_page_obj = submissions_paginator.get_page(self.request.GET.get("page_submissions"))
        context["recent_submissions"] = submissions_page_obj.object_list
        context["submissions_page_obj"] = submissions_page_obj
        context["submissions_is_paginated"] = submissions_page_obj.has_other_pages()
        context["recent_audit_logs"] = self.object.audit_logs.select_related("actor")[:20]
        context["is_owner"] = self.object.owner_id == self.request.user.id
        context["current_submitted_by_email"] = (self.request.GET.get("submitted_by_email") or "").strip()
        context["current_submitted_from"] = (self.request.GET.get("submitted_from") or "").strip()
        context["current_submitted_to"] = (self.request.GET.get("submitted_to") or "").strip()
        context["current_has_output"] = (self.request.GET.get("has_output") or "").strip()
        context["submission_querystring"] = (
            f"submitted_by_email={context['current_submitted_by_email']}"
            f"&submitted_from={context['current_submitted_from']}"
            f"&submitted_to={context['current_submitted_to']}"
            f"&has_output={context['current_has_output']}"
        )
        if context["is_owner"]:
            context["permissions"] = (
                TemplatePermission.objects.select_related("user").filter(template=self.object).exclude(role=AccessRole.OWNER)
            )
            context["pending_invites"] = self.object.invites.filter(status=InviteStatus.PENDING)
            context["editable_roles"] = [
                (AccessRole.EDITOR, "Editor"),
                (AccessRole.FILLER, "Preenchedor"),
                (AccessRole.VIEWER, "Leitor"),
            ]
        return context
