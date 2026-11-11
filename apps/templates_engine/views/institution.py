from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from apps.templates_engine.audit import log_template_action
from apps.templates_engine.domain.institution import (
    can_manage_institution,
    can_manage_template,
    downloadable_submissions,
    transition_request,
    visible_requests,
    visible_submissions,
)
from apps.templates_engine.forms.institution import (
    InstitutionForm,
    InstitutionMemberForm,
    RequestUpdateForm,
    SubmissionShareForm,
    TemplateFieldFormSet,
)
from apps.templates_engine.models import (
    AuditAction,
    DocumentTemplate,
    Institution,
    InstitutionMembership,
    SubmissionShare,
)

User = get_user_model()


class InstitutionListView(LoginRequiredMixin, ListView):
    template_name = "institutions/list.html"
    context_object_name = "institutions"
    paginate_by = 20

    def get_queryset(self):
        qs = Institution.objects.all()
        if not self.request.user.is_superuser:
            qs = qs.filter(
                memberships__user=self.request.user, memberships__is_active=True, is_active=True
            )
        return qs.distinct()


class InstitutionEditView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, pk):
        return get_object_or_404(Institution, pk=pk) if pk else Institution()

    def get(self, request, pk=None):
        return render(
            request,
            "institutions/form.html",
            {"form": InstitutionForm(instance=self.get_object(pk))},
        )

    @transaction.atomic
    def post(self, request, pk=None):
        form = InstitutionForm(request.POST, instance=self.get_object(pk))
        if form.is_valid():
            institution = form.save()
            if email := form.cleaned_data["responsible_email"]:
                user = User.objects.get(email__iexact=email, is_active=True)
                InstitutionMembership.objects.update_or_create(
                    institution=institution,
                    user=user,
                    defaults={"role": "manager", "is_active": True},
                )
            messages.success(request, "Instituição salva.")
            return redirect("institution-detail", pk=institution.pk)
        return render(request, "institutions/form.html", {"form": form})


class InstitutionDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        qs = Institution.objects.all()
        if not request.user.is_superuser:
            qs = qs.filter(
                is_active=True, memberships__user=request.user, memberships__is_active=True
            )
        institution = get_object_or_404(qs.distinct(), pk=pk)
        manager = can_manage_institution(pk, request.user)
        return render(
            request,
            "institutions/detail.html",
            {
                "institution": institution,
                "can_manage": manager,
                "members": institution.memberships.select_related("user") if manager else [],
                "templates": institution.templates.all(),
                "member_form": InstitutionMemberForm(actor=request.user),
            },
        )


class InstitutionMemberAddView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not can_manage_institution(pk, request.user):
            raise PermissionDenied
        institution = get_object_or_404(Institution, pk=pk, is_active=True)
        form = InstitutionMemberForm(request.POST, actor=request.user)
        if form.is_valid():
            user = User.objects.get(email__iexact=form.cleaned_data["email"], is_active=True)
            membership = InstitutionMembership.objects.filter(
                institution=institution, user=user
            ).first()
            if membership and membership.role == "manager" and not request.user.is_superuser:
                raise PermissionDenied
            InstitutionMembership.objects.update_or_create(
                institution=institution,
                user=user,
                defaults={"role": form.cleaned_data["role"], "is_active": True},
            )
            messages.success(request, "Vínculo salvo.")
            return redirect("institution-detail", pk=pk)
        return render(request, "institutions/form.html", {"form": form}, status=400)


class InstitutionMemberRemoveView(LoginRequiredMixin, View):
    def post(self, request, pk, membership_id):
        if not can_manage_institution(pk, request.user):
            raise PermissionDenied
        member = get_object_or_404(InstitutionMembership, pk=membership_id, institution_id=pk)
        if member.role == "manager" and not request.user.is_superuser:
            raise PermissionDenied
        member.is_active = False
        member.save(update_fields=["is_active"])
        messages.success(request, "Vínculo desativado.")
        return redirect("institution-detail", pk=pk)


class TemplateFieldsView(LoginRequiredMixin, View):
    def get_template(self, user, pk):
        template = get_object_or_404(DocumentTemplate, pk=pk)
        if not can_manage_template(template, user):
            raise PermissionDenied
        return template

    def get(self, request, pk):
        template = self.get_template(request.user, pk)
        return render(
            request,
            "templates_engine/template_fields.html",
            {
                "template_obj": template,
                "formset": TemplateFieldFormSet(initial=template.fields_schema, prefix="fields"),
                "revision": template.updated_at.isoformat(),
            },
        )

    @transaction.atomic
    def post(self, request, pk):
        template = self.get_template(request.user, pk)
        formset = TemplateFieldFormSet(request.POST, prefix="fields")
        context = {
            "template_obj": template,
            "formset": formset,
            "revision": request.POST.get("revision", ""),
        }
        if template.status != "active":
            context["error"] = "Modelos encerrados não podem ser alterados."
            return render(request, "templates_engine/template_fields.html", context, status=409)
        if request.POST.get("revision") != template.updated_at.isoformat():
            context["error"] = "O modelo foi atualizado. Recarregue a página antes de editar."
            return render(request, "templates_engine/template_fields.html", context, status=409)
        if formset.is_valid():
            schema = [
                {key: form.cleaned_data[key] for key in ["key", "label", "type", "required"]}
                for form in formset
                if form.cleaned_data and not form.cleaned_data.get("DELETE")
            ]
            # Conditional update also protects SQLite, where select_for_update is not supported.
            from django.utils import timezone

            updated = DocumentTemplate.objects.filter(pk=pk, updated_at=template.updated_at).update(
                fields_schema=schema,
                updated_at=timezone.now(),
            )
            if not updated:
                context["error"] = "O modelo foi atualizado. Recarregue a página."
                return render(request, "templates_engine/template_fields.html", context, status=409)
            log_template_action(
                template=template,
                actor=request.user,
                action=AuditAction.TEMPLATE_FIELDS_UPDATED,
                metadata={"fields_count": len(schema)},
            )
            messages.success(
                request, "Campos atualizados. As emissões anteriores foram preservadas."
            )
            return redirect("template-detail", pk=pk)
        return render(request, "templates_engine/template_fields.html", context)


class RequestListView(LoginRequiredMixin, ListView):
    template_name = "requests/list.html"
    context_object_name = "document_requests"
    paginate_by = 20

    def get_queryset(self):
        qs = visible_requests(self.request.user)
        if status := self.request.GET.get("status"):
            qs = qs.filter(status=status)
        if query := self.request.GET.get("q", "").strip():
            qs = qs.filter(
                Q(submission__template__name__icontains=query)
                | Q(protocol__icontains=query.replace("-", ""))
            )
        return qs


class RequestDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        obj = get_object_or_404(visible_requests(request.user), pk=pk)
        return render(
            request,
            "requests/detail.html",
            {
                "document_request": obj,
                "events": obj.events.select_related("actor"),
                "form": RequestUpdateForm(
                    document_request=obj,
                    actor=request.user,
                    initial={
                        "revision": obj.revision,
                        "assigned_to": obj.assigned_to,
                        "status": "in_review",
                    },
                ),
            },
        )


class RequestUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        obj = get_object_or_404(visible_requests(request.user), pk=pk)
        form = RequestUpdateForm(request.POST, document_request=obj, actor=request.user)
        if form.is_valid():
            try:
                transition_request(pk, request.user, **form.cleaned_data)
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, "Solicitação atualizada.")
                return redirect("request-detail", pk=pk)
        return render(
            request,
            "requests/detail.html",
            {"document_request": obj, "events": obj.events.select_related("actor"), "form": form},
            status=400,
        )


class SubmissionListView(LoginRequiredMixin, ListView):
    template_name = "documents/list.html"
    context_object_name = "submissions"
    paginate_by = 20

    def get_queryset(self):
        return (
            downloadable_submissions(self.request.user)
            .select_related("template", "submitted_by")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["manageable_submission_ids"] = set(
            visible_submissions(self.request.user)
            .filter(pk__in=[item.pk for item in context["submissions"]])
            .values_list("pk", flat=True)
        )
        return context


class SubmissionDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        submission = get_object_or_404(downloadable_submissions(request.user), pk=pk)
        if not submission.output_file:
            raise Http404
        try:
            handle = submission.output_file.open("rb")
        except (FileNotFoundError, OSError) as error:
            raise Http404 from error
        return FileResponse(
            handle, as_attachment=True, filename=f"documento_{pk}.{submission.template.file_type}"
        )


class TemplateDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        from apps.templates_engine.domain.access import TemplateAccessService

        template = get_object_or_404(
            TemplateAccessService.get_accessible_templates_queryset(
                request.user, DocumentTemplate.objects.all()
            ),
            pk=pk,
        )
        try:
            handle = template.file.open("rb")
        except (FileNotFoundError, OSError) as error:
            raise Http404 from error
        return FileResponse(
            handle, as_attachment=True, filename=f"modelo_{pk}.{template.file_type}"
        )


class SubmissionShareView(LoginRequiredMixin, View):
    def get(self, request, pk):
        submission = get_object_or_404(visible_submissions(request.user), pk=pk)
        return render(
            request,
            "documents/share.html",
            {
                "submission": submission,
                "form": SubmissionShareForm(),
                "shares": submission.shares.select_related("user"),
            },
        )

    @transaction.atomic
    def post(self, request, pk):
        submission = get_object_or_404(visible_submissions(request.user), pk=pk)
        form = SubmissionShareForm(request.POST)
        if form.is_valid():
            recipient = User.objects.get(email__iexact=form.cleaned_data["email"], is_active=True)
            _, created = SubmissionShare.objects.get_or_create(
                submission=submission, user=recipient, defaults={"shared_by": request.user}
            )
            if created:
                log_template_action(
                    template=submission.template,
                    actor=request.user,
                    action=AuditAction.SUBMISSION_SHARED,
                    metadata={"submission_id": pk, "recipient_id": recipient.pk},
                )
            messages.success(
                request,
                "Documento compartilhado. O destinatário pode acessá-lo em Documentos emitidos.",
            )
            return redirect("submission-share", pk=pk)
        return render(
            request,
            "documents/share.html",
            {
                "submission": submission,
                "form": form,
                "shares": submission.shares.select_related("user"),
            },
            status=400,
        )


class SubmissionShareRevokeView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, pk, share_id):
        submission = get_object_or_404(visible_submissions(request.user), pk=pk)
        share = get_object_or_404(SubmissionShare, pk=share_id, submission=submission)
        recipient_id = share.user_id
        share.delete()
        log_template_action(
            template=submission.template,
            actor=request.user,
            action=AuditAction.SUBMISSION_SHARE_REVOKED,
            metadata={"submission_id": pk, "recipient_id": recipient_id},
        )
        return redirect("submission-share", pk=pk)
