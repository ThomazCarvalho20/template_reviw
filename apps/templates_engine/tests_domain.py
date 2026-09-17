import io
import zipfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.templates_engine.domain import (
    TemplateAccessService,
    TemplateEngineSelector,
    TemplateFilterService,
    TemplateFormDomainService,
    TemplateSharingService,
    WorkspaceService,
)
from apps.templates_engine.models import (
    AccessRole,
    AuditAction,
    DocumentTemplate,
    TemplateAuditLog,
    TemplatePermission,
    TemplateShareGroup,
    TemplateShareGroupMember,
    TemplateSubmission,
    Workspace,
    WorkspaceMembership,
)


User = get_user_model()


def _fake_docx_bytes(*placeholders):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        xml_content = " ".join(f"{{{{{field}}}}}" for field in placeholders)
        archive.writestr("word/document.xml", f"<w:document><w:body>{xml_content}</w:body></w:document>")
    return buffer.getvalue()


class TemplateAccessServiceTests(TestCase):
    def setUp(self):
        self.service = TemplateAccessService()
        self.owner = User.objects.create_user(username="owner_dom", email="owner_dom@example.com", password="StrongPass123!")
        self.other = User.objects.create_user(username="other_dom", email="other_dom@example.com", password="StrongPass123!")
        self.workspace = Workspace.objects.create(owner=self.owner, name="Workspace Dom")
        self.template = DocumentTemplate.objects.create(
            owner=self.owner,
            workspace=self.workspace,
            name="Template Dom",
            file_type="docx",
            fields_schema=[],
            file="templates/fake.docx",
        )

    def test_resolve_user_role_owner_and_permission(self):
        self.assertEqual(self.service.resolve_user_role(self.template, self.owner), AccessRole.OWNER)

        self.template.workspace = None
        self.template.save(update_fields=["workspace"])
        TemplatePermission.objects.create(template=self.template, user=self.other, role=AccessRole.EDITOR)
        self.assertEqual(self.service.resolve_user_role(self.template, self.other), AccessRole.EDITOR)

    def test_resolve_user_role_workspace_member(self):
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.other,
            role="member",
            is_active=True,
        )
        self.assertEqual(self.service.resolve_user_role(self.template, self.other), "member")

    def test_user_can_access_template_for_owner_permission_and_member(self):
        self.assertTrue(self.service.user_can_access_template(self.template, self.owner))
        self.assertFalse(self.service.user_can_access_template(self.template, self.other))

        TemplatePermission.objects.create(template=self.template, user=self.other, role=AccessRole.VIEWER)
        self.assertTrue(self.service.user_can_access_template(self.template, self.other))

    def test_get_accessible_templates_queryset(self):
        outsider = User.objects.create_user(username="outsider_dom", email="outsider_dom@example.com", password="StrongPass123!")
        qs = self.service.get_accessible_templates_queryset(self.owner, DocumentTemplate.objects.all())
        self.assertEqual(list(qs), [self.template])

        qs_out = self.service.get_accessible_templates_queryset(outsider, DocumentTemplate.objects.all())
        self.assertEqual(list(qs_out), [])


class TemplateFilterServiceTests(TestCase):
    def setUp(self):
        self.service = TemplateFilterService()
        self.factory = RequestFactory()
        self.owner = User.objects.create_user(username="owner_filter", email="owner_filter@example.com", password="StrongPass123!")
        self.other = User.objects.create_user(username="other_filter", email="other_filter@example.com", password="StrongPass123!")
        self.template = DocumentTemplate.objects.create(
            owner=self.owner,
            name="Template Filter",
            file_type="docx",
            fields_schema=[],
            file="templates/filter.docx",
        )

    def _request(self, params):
        req = self.factory.get("/fake-url/", data=params)
        req.GET = QueryDict(mutable=True)
        req.GET.update(params)
        return req

    def test_get_filtered_audit_logs_by_action_and_actor(self):
        log1 = TemplateAuditLog.objects.create(
            template=self.template,
            action=AuditAction.TEMPLATE_SHARED,
            actor=self.owner,
            metadata={},
        )
        TemplateAuditLog.objects.create(
            template=self.template,
            action=AuditAction.TEMPLATE_FILLED,
            actor=self.other,
            metadata={},
        )
        request = self._request({"action": "template_shared", "actor_email": "owner_filter@"})
        logs = self.service.get_filtered_audit_logs(request, self.template)
        self.assertEqual(list(logs), [log1])

    def test_get_filtered_audit_logs_by_date_window(self):
        older = TemplateAuditLog.objects.create(
            template=self.template,
            action=AuditAction.TEMPLATE_SHARED,
            actor=self.owner,
            metadata={},
        )
        older.created_at = timezone.now() - timedelta(days=5)
        older.save(update_fields=["created_at"])
        newer = TemplateAuditLog.objects.create(
            template=self.template,
            action=AuditAction.TEMPLATE_SHARED,
            actor=self.owner,
            metadata={},
        )
        request = self._request({"date_from": str((timezone.now() - timedelta(days=1)).date())})
        logs = self.service.get_filtered_audit_logs(request, self.template)
        self.assertEqual(list(logs), [newer])

    def test_get_filtered_submissions_has_output(self):
        s1 = TemplateSubmission.objects.create(template=self.template, submitted_by=self.owner, payload={"a": 1})
        s1.output_file.name = "generated/out.docx"
        s1.save(update_fields=["output_file"])
        s2 = TemplateSubmission.objects.create(template=self.template, submitted_by=self.other, payload={"b": 2})

        req_yes = self._request({"has_output": "yes"})
        yes_results = self.service.get_filtered_submissions(req_yes, self.template)
        self.assertEqual(list(yes_results), [s1])

        req_no = self._request({"has_output": "no"})
        no_results = self.service.get_filtered_submissions(req_no, self.template)
        self.assertEqual(list(no_results), [s2])


class TemplateFormDomainServiceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner_form", email="owner_form@example.com", password="StrongPass123!")
        self.group = TemplateShareGroup.objects.create(owner=self.owner, name="Grupo Form")

    def test_parse_email_list_normalizes_and_deduplicates(self):
        emails = TemplateFormDomainService.parse_email_list("A@EXAMPLE.com; b@example.com\nA@example.com")
        self.assertEqual(emails, ["a@example.com", "b@example.com"])

    def test_parse_email_list_rejects_invalid(self):
        with self.assertRaisesMessage(Exception, "E-mails invalidos"):
            TemplateFormDomainService.parse_email_list("ok@example.com,nao-email")

    def test_validate_group_and_template_checks(self):
        self.assertEqual(
            TemplateFormDomainService.validate_group_exists_for_owner(self.group.pk, self.owner),
            self.group.pk,
        )
        with self.assertRaisesMessage(Exception, "Grupo nao encontrado."):
            TemplateFormDomainService.validate_group_exists_for_owner(999999, self.owner)

        template = DocumentTemplate.objects.create(
            owner=self.owner,
            name="Template Form",
            file_type="docx",
            fields_schema=[],
            file="templates/form.docx",
        )
        self.assertEqual(TemplateFormDomainService.validate_template_exists(template.pk), template.pk)


class WorkspaceAndSharingDomainServiceTests(TestCase):
    def setUp(self):
        self.access_service = TemplateAccessService()
        self.workspace_service = WorkspaceService(self.access_service)
        self.sharing_service = TemplateSharingService()
        self.owner = User.objects.create_user(username="owner_ws", email="owner_ws@example.com", password="StrongPass123!")
        self.member = User.objects.create_user(username="member_ws", email="member_ws@example.com", password="StrongPass123!")
        self.workspace = Workspace.objects.create(owner=self.owner, name="WS Domain")
        self.group = TemplateShareGroup.objects.create(owner=self.owner, name="Grupo WS")
        TemplateShareGroupMember.objects.create(group=self.group, email="member_ws@example.com")
        TemplateShareGroupMember.objects.create(group=self.group, email="missing_ws@example.com")

    def test_add_members_by_email_and_touch_presence(self):
        added, missing = self.workspace_service.add_members_by_email(
            self.workspace,
            ["member_ws@example.com", "missing_ws@example.com"],
        )
        self.assertEqual(added, 1)
        self.assertEqual(missing, ["missing_ws@example.com"])

        membership = WorkspaceMembership.objects.get(workspace=self.workspace, user=self.member)
        self.assertIsNone(membership.last_seen_at)
        self.workspace_service.touch_presence(self.workspace, self.member)
        membership.refresh_from_db()
        self.assertIsNotNone(membership.last_seen_at)

    def test_add_and_remove_group_members_from_workspace(self):
        added, missing = self.sharing_service.add_group_members_to_workspace(self.group, self.workspace)
        self.assertEqual(added, 1)
        self.assertEqual(missing, ["missing_ws@example.com"])

        removed, skipped = self.sharing_service.remove_group_members_from_workspace(self.group, self.workspace)
        self.assertEqual(removed, 1)
        self.assertEqual(skipped, 0)


class TemplateSelectorTests(TestCase):
    def setUp(self):
        self.selector = TemplateEngineSelector()
        self.owner = User.objects.create_user(username="owner_sel", email="owner_sel@example.com", password="StrongPass123!")
        self.other = User.objects.create_user(username="other_sel", email="other_sel@example.com", password="StrongPass123!")
        self.workspace = Workspace.objects.create(owner=self.owner, name="WS Selector")
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.owner, role="owner", is_active=True)
        self.group = TemplateShareGroup.objects.create(owner=self.owner, name="Grupo Selector")
        TemplateShareGroupMember.objects.create(group=self.group, email="other_sel@example.com")

    def test_workspace_and_group_selectors(self):
        self.assertEqual(self.selector.workspace_memberships_for_user(self.owner).count(), 1)
        self.assertEqual(self.selector.owned_workspaces(self.owner).count(), 1)
        self.assertEqual(self.selector.owner_groups_with_members(self.owner).count(), 1)

    def test_notification_selectors(self):
        from apps.templates_engine.models import UserNotification

        UserNotification.objects.create(
            user=self.owner,
            notification_type="workspace_join_request",
            title="n1",
            is_read=False,
        )
        UserNotification.objects.create(
            user=self.owner,
            notification_type="workspace_join_request",
            title="n2",
            is_read=True,
        )
        self.assertEqual(self.selector.unread_notifications_count(self.owner), 1)
        self.assertEqual(len(self.selector.notifications_for_user(self.owner, limit=8)), 2)
        self.selector.mark_all_notifications_read(self.owner)
        self.assertEqual(self.selector.unread_notifications_count(self.owner), 0)
