import io
import zipfile
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.test.utils import override_settings

from apps.core.models import UserSettings
from apps.templates_engine.models import (
    AuditAction,
    DocumentTemplate,
    InviteStatus,
    TemplateAuditLog,
    TemplateInvite,
    TemplatePermission,
    TemplateShareGroup,
    TemplateShareGroupMember,
    TemplateStatus,
    TemplateSubmission,
    Workspace,
    WorkspaceJoinRequest,
    WorkspaceJoinRequestStatus,
    WorkspaceMembership,
)
from apps.templates_engine.services import detect_template_schema, generate_filled_document


User = get_user_model()


def make_fake_docx_with_placeholders(*placeholders):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        xml_content = " ".join(f"{{{{{field}}}}}" for field in placeholders)
        archive.writestr("word/document.xml", f"<w:document><w:body>{xml_content}</w:body></w:document>")
    return buffer.getvalue()


class TemplateServiceTests(TestCase):
    def test_detect_schema_from_docx(self):
        content = make_fake_docx_with_placeholders("nome_cliente", "cpf")
        file = SimpleUploadedFile(
            "modelo.docx",
            content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        obj = DocumentTemplate.objects.create(
            owner=User.objects.create_user(
                username="owner_service",
                email="owner_service@example.com",
                password="StrongPass123!",
            ),
            name="Modelo de Contrato",
            file=file,
            file_type="docx",
        )
        schema = detect_template_schema(obj.file.path, obj.file_type)
        keys = {field["key"] for field in schema}
        self.assertEqual(keys, {"nome_cliente", "cpf"})

    def test_generate_filled_document_docx(self):
        content = make_fake_docx_with_placeholders("nome_cliente", "cpf")
        file = SimpleUploadedFile(
            "modelo.docx",
            content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        obj = DocumentTemplate.objects.create(
            owner=User.objects.create_user(
                username="owner_service_2",
                email="owner_service_2@example.com",
                password="StrongPass123!",
            ),
            name="Modelo",
            file=file,
            file_type="docx",
        )
        rendered = generate_filled_document(
            obj.file.path,
            obj.file_type,
            {"nome_cliente": "Alice", "cpf": "123"},
        )
        with zipfile.ZipFile(io.BytesIO(rendered), mode="r") as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        self.assertIn("Alice", xml)
        self.assertIn("123", xml)

    @patch("apps.templates_engine.services._import_pypdf")
    def test_generate_filled_document_pdf_updates_form_fields(self, import_pypdf_mock):
        reader = MagicMock()
        reader.pages = [MagicMock(), MagicMock()]
        reader_cls = MagicMock(return_value=reader)

        writer = MagicMock()
        writer.pages = []
        writer._root_object = {}
        writer_cls = MagicMock(return_value=writer)

        name_object = lambda value: value
        boolean_object = lambda value: value
        import_pypdf_mock.return_value = (reader_cls, writer_cls, name_object, boolean_object)

        def add_page(page):
            writer.pages.append(page)

        writer.add_page.side_effect = add_page
        writer.write.side_effect = lambda out: out.write(b"%PDF-mocked")

        rendered = generate_filled_document("/tmp/fake.pdf", "pdf", {"nome_cliente": "Alice"})

        self.assertEqual(rendered, b"%PDF-mocked")
        self.assertEqual(writer.update_page_form_field_values.call_count, 2)
        writer.update_page_form_field_values.assert_any_call(reader.pages[0], {"nome_cliente": "Alice"})


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TemplateFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="StrongPass123!",
        )
        self.other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="StrongPass123!",
        )

    def _create_template(self):
        content = make_fake_docx_with_placeholders("nome_cliente", "cpf")
        file = SimpleUploadedFile(
            "modelo.docx",
            content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        return DocumentTemplate.objects.create(
            owner=self.owner,
            name="Contrato",
            file=file,
            file_type="docx",
            fields_schema=[
                {"key": "nome_cliente", "label": "Nome Cliente", "type": "text", "required": True},
                {"key": "cpf", "label": "CPF", "type": "text", "required": True},
            ],
        )

    def test_template_create_view_sets_owner_permission_and_schema(self):
        self.client.force_login(self.owner)
        upload_file = SimpleUploadedFile(
            "modelo.docx",
            make_fake_docx_with_placeholders("nome_cliente", "cpf"),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response = self.client.post(
            reverse("template-create"),
            data={
                "name": "Contrato Novo",
                "description": "Desc",
                "file_type": "docx",
                "file": upload_file,
            },
        )
        self.assertEqual(response.status_code, 302)
        created = DocumentTemplate.objects.get(name="Contrato Novo")
        self.assertTrue(created.fields_schema)
        self.assertTrue(
            TemplatePermission.objects.filter(template=created, user=self.owner, role="owner").exists()
        )
        self.assertTrue(
            TemplateAuditLog.objects.filter(template=created, action=AuditAction.TEMPLATE_CREATED).exists()
        )

    def test_share_template_only_owner_can_share(self):
        template = self._create_template()
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("template-share", args=[template.pk]),
            data={"email": "other@example.com", "role": "viewer"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            TemplatePermission.objects.filter(template=template, user=self.other, role="viewer").exists()
        )

    def test_share_template_by_owner(self):
        template = self._create_template()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("template-share", args=[template.pk]),
            data={"email": "other@example.com", "role": "viewer"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            TemplatePermission.objects.filter(template=template, user=self.other, role="viewer").exists()
        )
        self.assertTrue(
            TemplateAuditLog.objects.filter(template=template, action=AuditAction.TEMPLATE_SHARED).exists()
        )

    def test_create_share_group(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("template-group-create"),
            data={
                "name": "Equipe Financeiro",
                "members_raw": "other@example.com, new.person@example.com",
            },
        )
        self.assertEqual(response.status_code, 302)
        group = TemplateShareGroup.objects.get(owner=self.owner, name="Equipe Financeiro")
        members = list(group.members.values_list("email", flat=True))
        self.assertEqual(sorted(members), ["new.person@example.com", "other@example.com"])

    def test_share_template_with_group_grants_permissions_and_sends_invites(self):
        template = self._create_template()
        group = TemplateShareGroup.objects.create(owner=self.owner, name="Time A")
        TemplateShareGroupMember.objects.create(group=group, email="other@example.com")
        TemplateShareGroupMember.objects.create(group=group, email="external@example.com")

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("template-share-group", args=[template.pk]),
            data={"group_id": group.pk, "role": "viewer"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            TemplatePermission.objects.filter(template=template, user=self.other, role="viewer").exists()
        )
        self.assertTrue(
            TemplateInvite.objects.filter(
                template=template, invited_email="external@example.com", status=InviteStatus.PENDING
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(
            TemplateAuditLog.objects.filter(
                template=template, action=AuditAction.TEMPLATE_SHARED, metadata__share_mode="group"
            ).exists()
        )

    def test_workspace_create_and_membership(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("workspace-create"),
            data={"name": "Operacoes", "description": "Time de operacoes"},
        )
        self.assertEqual(response.status_code, 302)
        workspace = Workspace.objects.get(name="Operacoes")
        self.assertEqual(workspace.owner_id, self.owner.id)
        self.assertTrue(
            WorkspaceMembership.objects.filter(
                workspace=workspace, user=self.owner, is_active=True, role="owner"
            ).exists()
        )

    def test_workspace_detail_non_member_creates_join_request(self):
        workspace = Workspace.objects.create(owner=self.owner, name="Financeiro")
        WorkspaceMembership.objects.create(workspace=workspace, user=self.owner, role="owner", is_active=True)
        self.client.force_login(self.other)
        response = self.client.get(reverse("workspace-detail", args=[workspace.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            WorkspaceJoinRequest.objects.filter(
                workspace=workspace, requester=self.other, status=WorkspaceJoinRequestStatus.PENDING
            ).exists()
        )

    def test_workspace_owner_can_approve_join_request(self):
        workspace = Workspace.objects.create(owner=self.owner, name="Comercial")
        WorkspaceMembership.objects.create(workspace=workspace, user=self.owner, role="owner", is_active=True)
        join_request = WorkspaceJoinRequest.objects.create(
            workspace=workspace,
            requester=self.other,
            status=WorkspaceJoinRequestStatus.PENDING,
        )
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("workspace-request-decision", args=[join_request.pk]),
            data={"decision": "approve"},
        )
        self.assertEqual(response.status_code, 302)
        join_request.refresh_from_db()
        self.assertEqual(join_request.status, WorkspaceJoinRequestStatus.APPROVED)
        self.assertTrue(
            WorkspaceMembership.objects.filter(workspace=workspace, user=self.other, is_active=True).exists()
        )

    def test_workspace_templates_page_for_member(self):
        workspace = Workspace.objects.create(owner=self.owner, name="Dados")
        WorkspaceMembership.objects.create(workspace=workspace, user=self.owner, role="owner", is_active=True)
        WorkspaceMembership.objects.create(workspace=workspace, user=self.other, role="member", is_active=True)
        template = self._create_template()
        template.workspace = workspace
        template.save(update_fields=["workspace"])
        self.client.force_login(self.other)
        response = self.client.get(reverse("workspace-templates", args=[workspace.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, template.name)

    def test_workspace_templates_page_non_member_redirects(self):
        workspace = Workspace.objects.create(owner=self.owner, name="Privado")
        WorkspaceMembership.objects.create(workspace=workspace, user=self.owner, role="owner", is_active=True)
        stranger = User.objects.create_user(
            username="ws_stranger",
            email="ws_stranger@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(stranger)
        response = self.client.get(reverse("workspace-templates", args=[workspace.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            WorkspaceJoinRequest.objects.filter(
                workspace=workspace, requester=stranger, status=WorkspaceJoinRequestStatus.PENDING
            ).exists()
        )

    def test_workspace_add_group_adds_group_members(self):
        workspace = Workspace.objects.create(owner=self.owner, name="Produto")
        WorkspaceMembership.objects.create(workspace=workspace, user=self.owner, role="owner", is_active=True)
        group = TemplateShareGroup.objects.create(owner=self.owner, name="Equipe Produto")
        TemplateShareGroupMember.objects.create(group=group, email="other@example.com")
        TemplateShareGroupMember.objects.create(group=group, email="missing@example.com")

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("workspace-add-group", args=[workspace.pk]),
            data={"group_id": group.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            WorkspaceMembership.objects.filter(workspace=workspace, user=self.other, is_active=True).exists()
        )

    def test_group_detail_updates_name_and_members(self):
        group = TemplateShareGroup.objects.create(owner=self.owner, name="Equipe Antiga")
        TemplateShareGroupMember.objects.create(group=group, email="other@example.com")
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("group-detail", args=[group.pk]),
            data={
                "action": "update_group",
                "name": "Equipe Nova",
                "members_raw": "other@example.com,novo@example.com",
            },
        )
        self.assertEqual(response.status_code, 302)
        group.refresh_from_db()
        self.assertEqual(group.name, "Equipe Nova")
        members = set(group.members.values_list("email", flat=True))
        self.assertEqual(members, {"other@example.com", "novo@example.com"})

    def test_group_detail_remove_group_from_workspace(self):
        workspace = Workspace.objects.create(owner=self.owner, name="Suporte")
        WorkspaceMembership.objects.create(workspace=workspace, user=self.owner, role="owner", is_active=True)
        WorkspaceMembership.objects.create(workspace=workspace, user=self.other, role="member", is_active=True)
        group = TemplateShareGroup.objects.create(owner=self.owner, name="Equipe Suporte")
        TemplateShareGroupMember.objects.create(group=group, email="other@example.com")

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("group-detail", args=[group.pk]),
            data={"action": "remove_group_from_workspace", "workspace_id": workspace.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            WorkspaceMembership.objects.filter(workspace=workspace, user=self.other, is_active=True).exists()
        )

    def test_fill_template_creates_submission(self):
        template = self._create_template()
        TemplatePermission.objects.create(template=template, user=self.other, role="filler")
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("template-fill", args=[template.pk]),
            data={"nome_cliente": "Alice", "cpf": "12345678900"},
        )
        self.assertEqual(response.status_code, 302)
        submission = TemplateSubmission.objects.get(template=template)
        self.assertEqual(submission.payload["nome_cliente"], "Alice")
        self.assertTrue(submission.output_file.name.endswith(".docx"))
        self.assertTrue(
            TemplateAuditLog.objects.filter(template=template, action=AuditAction.TEMPLATE_FILLED).exists()
        )

    def test_viewer_cannot_submit_template(self):
        template = self._create_template()
        TemplatePermission.objects.create(template=template, user=self.other, role="viewer")
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("template-fill", args=[template.pk]),
            data={"nome_cliente": "Alice", "cpf": "12345678900"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TemplateSubmission.objects.filter(template=template).exists())

    def test_only_owner_can_close_template(self):
        template = self._create_template()
        self.client.force_login(self.other)
        response = self.client.post(reverse("template-close", args=[template.pk]))
        self.assertEqual(response.status_code, 302)
        template.refresh_from_db()
        self.assertEqual(template.status, TemplateStatus.ACTIVE)

        self.client.force_login(self.owner)
        response = self.client.post(reverse("template-close", args=[template.pk]))
        self.assertEqual(response.status_code, 302)
        template.refresh_from_db()
        self.assertEqual(template.status, TemplateStatus.CLOSED)
        self.assertTrue(
            TemplateAuditLog.objects.filter(template=template, action=AuditAction.TEMPLATE_CLOSED).exists()
        )

    def test_invite_flow_send_and_accept(self):
        template = self._create_template()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("template-invite", args=[template.pk]),
            data={"email": "other@example.com", "role": "viewer"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        invite = TemplateInvite.objects.get(template=template, invited_email="other@example.com")
        self.assertEqual(invite.status, InviteStatus.PENDING)
        self.assertTrue(
            TemplateAuditLog.objects.filter(template=template, action=AuditAction.TEMPLATE_INVITED).exists()
        )

        self.client.force_login(self.other)
        response = self.client.get(reverse("template-invite-accept", args=[invite.token]))
        self.assertEqual(response.status_code, 302)
        invite.refresh_from_db()
        self.assertEqual(invite.status, InviteStatus.ACCEPTED)
        self.assertTrue(
            TemplatePermission.objects.filter(template=template, user=self.other, role="viewer").exists()
        )
        self.assertTrue(
            TemplateAuditLog.objects.filter(template=template, action=AuditAction.INVITE_ACCEPTED).exists()
        )

    def test_audit_page_for_user_with_access(self):
        template = self._create_template()
        TemplatePermission.objects.create(template=template, user=self.other, role="viewer")
        TemplateAuditLog.objects.create(
            template=template,
            action=AuditAction.TEMPLATE_SHARED,
            actor=self.owner,
            metadata={"target_email": "other@example.com"},
        )
        self.client.force_login(self.other)
        response = self.client.get(reverse("template-audit", args=[template.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historico de acoes")

    def test_audit_filters_and_csv_export(self):
        template = self._create_template()
        TemplatePermission.objects.create(template=template, user=self.other, role="viewer")
        TemplateAuditLog.objects.create(
            template=template,
            action=AuditAction.TEMPLATE_SHARED,
            actor=self.owner,
            metadata={"target_email": "other@example.com"},
        )
        TemplateAuditLog.objects.create(
            template=template,
            action=AuditAction.TEMPLATE_FILLED,
            actor=self.other,
            metadata={"submission_id": 99},
        )
        self.client.force_login(self.owner)
        filtered_page = self.client.get(
            reverse("template-audit", args=[template.pk]),
            {"action": "template_shared", "actor_email": "owner@"},
        )
        self.assertEqual(filtered_page.status_code, 200)
        self.assertContains(filtered_page, "Template compartilhado")
        self.assertNotContains(filtered_page, "submission_id")

        export_response = self.client.get(
            reverse("template-audit-export", args=[template.pk]),
            {"action": "template_shared", "actor_email": "owner@"},
        )
        self.assertEqual(export_response.status_code, 200)
        self.assertEqual(export_response["Content-Type"], "text/csv")
        csv_text = export_response.content.decode("utf-8")
        self.assertIn("timestamp,action,actor_email,metadata", csv_text)
        self.assertIn("template_shared", csv_text)
        self.assertNotIn("template_filled", csv_text)

    def test_audit_pagination(self):
        template = self._create_template()
        for idx in range(25):
            TemplateAuditLog.objects.create(
                template=template,
                action=AuditAction.TEMPLATE_SHARED,
                actor=self.owner,
                metadata={"idx": idx},
            )
        self.client.force_login(self.owner)
        page_1 = self.client.get(reverse("template-audit", args=[template.pk]))
        self.assertEqual(page_1.status_code, 200)
        self.assertTrue(page_1.context["is_paginated"])
        self.assertEqual(len(page_1.context["audit_logs"]), 10)

        page_2 = self.client.get(reverse("template-audit", args=[template.pk]), {"page": 2})
        self.assertEqual(page_2.status_code, 200)
        self.assertEqual(len(page_2.context["audit_logs"]), 10)

    def test_audit_pagination_respects_user_settings(self):
        template = self._create_template()
        UserSettings.objects.create(user=self.owner, items_per_page=20)
        for idx in range(25):
            TemplateAuditLog.objects.create(
                template=template,
                action=AuditAction.TEMPLATE_SHARED,
                actor=self.owner,
                metadata={"idx": idx},
            )
        self.client.force_login(self.owner)
        page_1 = self.client.get(reverse("template-audit", args=[template.pk]))
        self.assertEqual(page_1.status_code, 200)
        self.assertTrue(page_1.context["is_paginated"])
        self.assertEqual(len(page_1.context["audit_logs"]), 20)

        page_2 = self.client.get(reverse("template-audit", args=[template.pk]), {"page": 2})
        self.assertEqual(page_2.status_code, 200)
        self.assertEqual(len(page_2.context["audit_logs"]), 5)

    def test_detail_page_for_user_with_access(self):
        template = self._create_template()
        TemplatePermission.objects.create(template=template, user=self.other, role="viewer")
        self.client.force_login(self.other)
        response = self.client.get(reverse("template-detail", args=[template.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detalhes")

    def test_detail_page_for_user_without_access_returns_404(self):
        template = self._create_template()
        stranger = User.objects.create_user(
            username="stranger",
            email="stranger@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(stranger)
        response = self.client.get(reverse("template-detail", args=[template.pk]))
        self.assertEqual(response.status_code, 404)

    def test_owner_can_revoke_permission(self):
        template = self._create_template()
        permission = TemplatePermission.objects.create(template=template, user=self.other, role="viewer")
        self.client.force_login(self.owner)
        response = self.client.post(reverse("template-permission-revoke", args=[template.pk, permission.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TemplatePermission.objects.filter(pk=permission.pk).exists())
        self.assertTrue(
            TemplateAuditLog.objects.filter(
                template=template, action=AuditAction.TEMPLATE_PERMISSION_REVOKED
            ).exists()
        )

    def test_owner_can_update_permission_role(self):
        template = self._create_template()
        permission = TemplatePermission.objects.create(template=template, user=self.other, role="viewer")
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("template-permission-update", args=[template.pk, permission.pk]),
            data={"role": "editor"},
        )
        self.assertEqual(response.status_code, 302)
        permission.refresh_from_db()
        self.assertEqual(permission.role, "editor")
        self.assertTrue(
            TemplateAuditLog.objects.filter(
                template=template, action=AuditAction.TEMPLATE_PERMISSION_UPDATED
            ).exists()
        )

    def test_owner_can_cancel_pending_invite(self):
        template = self._create_template()
        invite = TemplateInvite.objects.create(
            template=template,
            invited_email="pending@example.com",
            role="viewer",
            status=InviteStatus.PENDING,
            created_by=self.owner,
        )
        self.client.force_login(self.owner)
        response = self.client.post(reverse("template-invite-cancel", args=[template.pk, invite.pk]))
        self.assertEqual(response.status_code, 302)
        invite.refresh_from_db()
        self.assertEqual(invite.status, InviteStatus.CANCELED)
        self.assertTrue(
            TemplateAuditLog.objects.filter(template=template, action=AuditAction.INVITE_CANCELED).exists()
        )

    def test_template_list_search_filter_and_pagination(self):
        self.client.force_login(self.owner)
        for idx in range(12):
            DocumentTemplate.objects.create(
                owner=self.owner,
                name=f"Contrato {idx}",
                description="Descricao base",
                file=SimpleUploadedFile(
                    f"modelo_{idx}.docx",
                    make_fake_docx_with_placeholders("nome_cliente"),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
                file_type="docx",
                status="active",
                fields_schema=[{"key": "nome_cliente", "label": "Nome Cliente", "type": "text", "required": True}],
            )

        closed_pdf = DocumentTemplate.objects.create(
            owner=self.owner,
            name="Fechado PDF",
            description="Template fechado",
            file=SimpleUploadedFile(
                "modelo_fechado.pdf",
                b"%PDF-1.4",
                content_type="application/pdf",
            ),
            file_type="pdf",
            status="closed",
            fields_schema=[],
        )

        response_page_1 = self.client.get(reverse("template-list"))
        self.assertEqual(response_page_1.status_code, 200)
        self.assertTrue(response_page_1.context["is_paginated"])
        self.assertEqual(len(response_page_1.context["templates"]), 10)

        response_search = self.client.get(reverse("template-list"), {"q": "Fechado"})
        self.assertEqual(response_search.status_code, 200)
        self.assertContains(response_search, "Fechado PDF")

        response_filter = self.client.get(
            reverse("template-list"),
            {"status": "closed", "file_type": "pdf"},
        )
        self.assertEqual(response_filter.status_code, 200)
        templates = list(response_filter.context["templates"])
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0].id, closed_pdf.id)

    def test_submissions_filter_and_csv_export(self):
        template = self._create_template()
        TemplatePermission.objects.create(template=template, user=self.other, role="filler")

        first = TemplateSubmission.objects.create(
            template=template,
            submitted_by=self.owner,
            payload={"nome_cliente": "Owner"},
        )
        first.output_file.name = "generated/out1.docx"
        first.save(update_fields=["output_file"])

        TemplateSubmission.objects.create(
            template=template,
            submitted_by=self.other,
            payload={"nome_cliente": "Other"},
        )

        self.client.force_login(self.owner)
        detail = self.client.get(
            reverse("template-detail", args=[template.pk]),
            {"submitted_by_email": "owner@", "has_output": "yes"},
        )
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "#1")
        self.assertNotContains(detail, "#2")

        export = self.client.get(
            reverse("template-submissions-export", args=[template.pk]),
            {"submitted_by_email": "owner@", "has_output": "yes"},
        )
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export["Content-Type"], "text/csv")
        csv_text = export.content.decode("utf-8")
        self.assertIn("submitted_by_email", csv_text)
        self.assertIn("owner@example.com", csv_text)
        self.assertNotIn("other@example.com", csv_text)

    def test_submissions_pagination(self):
        template = self._create_template()
        for idx in range(12):
            TemplateSubmission.objects.create(
                template=template,
                submitted_by=self.owner,
                payload={"idx": idx},
            )
        self.client.force_login(self.owner)
        page_1 = self.client.get(reverse("template-detail", args=[template.pk]))
        self.assertEqual(page_1.status_code, 200)
        self.assertTrue(page_1.context["submissions_is_paginated"])
        self.assertEqual(len(page_1.context["recent_submissions"]), 10)

        page_2 = self.client.get(reverse("template-detail", args=[template.pk]), {"page_submissions": 2})
        self.assertEqual(page_2.status_code, 200)
        self.assertEqual(len(page_2.context["recent_submissions"]), 2)

    def test_submissions_pagination_respects_user_settings(self):
        template = self._create_template()
        UserSettings.objects.create(user=self.owner, items_per_page=20)
        for idx in range(12):
            TemplateSubmission.objects.create(
                template=template,
                submitted_by=self.owner,
                payload={"idx": idx},
            )
        self.client.force_login(self.owner)
        page = self.client.get(reverse("template-detail", args=[template.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertFalse(page.context["submissions_is_paginated"])
        self.assertEqual(len(page.context["recent_submissions"]), 12)

    def test_template_list_pagination_respects_user_settings(self):
        UserSettings.objects.create(user=self.owner, items_per_page=20)
        self.client.force_login(self.owner)
        for idx in range(12):
            DocumentTemplate.objects.create(
                owner=self.owner,
                name=f"Template Ajustado {idx}",
                description="Descricao base",
                file=SimpleUploadedFile(
                    f"settings_modelo_{idx}.docx",
                    make_fake_docx_with_placeholders("nome_cliente"),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
                file_type="docx",
                status="active",
                fields_schema=[{"key": "nome_cliente", "label": "Nome Cliente", "type": "text", "required": True}],
            )
        response = self.client.get(reverse("template-list"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_paginated"])
        self.assertEqual(len(response.context["templates"]), 12)
