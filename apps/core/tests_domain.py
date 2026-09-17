import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.core.domain import CoreSelector, DashboardService, NavigationService, SettingsService
from apps.core.models import ProfilePhotoDisplayScope
from apps.templates_engine.models import DocumentTemplate, TemplatePermission, TemplateSubmission, UserNotification


User = get_user_model()


class DashboardDomainServiceTests(TestCase):
    def setUp(self):
        self.service = DashboardService()
        self.owner = User.objects.create_user(
            username="dash_owner_dom",
            email="dash_owner_dom@example.com",
            password="StrongPass123!",
        )
        self.other = User.objects.create_user(
            username="dash_other_dom",
            email="dash_other_dom@example.com",
            password="StrongPass123!",
        )

    def test_get_items_limit_uses_user_settings(self):
        settings_obj = self.service.get_user_settings(self.owner)
        settings_obj.items_per_page = 20
        settings_obj.save(update_fields=["items_per_page"])
        self.assertEqual(self.service.get_items_limit(self.owner), 20)

    def test_get_recent_templates_and_submissions_for_accessible_templates(self):
        template_owned = DocumentTemplate.objects.create(
            owner=self.owner,
            name="Owned Template",
            file="templates/owned.docx",
            file_type="docx",
            fields_schema=[],
        )
        template_shared = DocumentTemplate.objects.create(
            owner=self.other,
            name="Shared Template",
            file="templates/shared.docx",
            file_type="docx",
            fields_schema=[],
        )
        TemplatePermission.objects.create(template=template_shared, user=self.owner, role="viewer")
        TemplateSubmission.objects.create(template=template_owned, submitted_by=self.owner, payload={})
        TemplateSubmission.objects.create(template=template_shared, submitted_by=self.other, payload={})

        templates, submissions = self.service.get_recent_templates_and_submissions(self.owner, 10)
        self.assertEqual({item.id for item in templates}, {template_owned.id, template_shared.id})
        self.assertEqual({item.template_id for item in submissions}, {template_owned.id, template_shared.id})


class SettingsDomainServiceTests(TestCase):
    ONE_PIXEL_PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7ZxioAAAAASUVORK5CYII="

    def setUp(self):
        self.service = SettingsService()
        self.user = User.objects.create_user(
            username="settings_domain",
            email="settings_domain@example.com",
            password="StrongPass123!",
        )
        self.settings_obj = self.service.get_user_settings(self.user)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_save_cropped_profile_photo_saves_valid_payload(self):
        payload = f"data:image/png;base64,{self.ONE_PIXEL_PNG}"
        with patch.object(self.settings_obj.profile_photo, "save") as mocked_photo_save:
            saved = self.service.save_cropped_profile_photo(self.user, self.settings_obj, payload)
        self.assertTrue(saved)
        mocked_photo_save.assert_called_once()

    def test_save_cropped_profile_photo_rejects_invalid_payload(self):
        saved = self.service.save_cropped_profile_photo(self.user, self.settings_obj, "invalid")
        self.assertFalse(saved)

    def test_force_header_profile_scope(self):
        self.settings_obj.profile_photo_display_scope = ProfilePhotoDisplayScope.BOTH
        self.settings_obj.save(update_fields=["profile_photo_display_scope"])
        self.service.force_header_profile_scope(self.settings_obj)
        self.settings_obj.refresh_from_db()
        self.assertEqual(self.settings_obj.profile_photo_display_scope, ProfilePhotoDisplayScope.HEADER)


class NavigationDomainServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="nav_domain",
            email="nav_domain@example.com",
            password="StrongPass123!",
        )

    def test_build_navigation_context_for_anonymous(self):
        request = SimpleNamespace(user=SimpleNamespace(is_authenticated=False))
        context = NavigationService.build_navigation_context(request)
        self.assertEqual(context["nav_user_settings"], None)
        self.assertEqual(context["nav_notifications"], [])
        self.assertEqual(context["nav_notifications_unread_count"], 0)

    def test_build_navigation_context_for_authenticated(self):
        UserNotification.objects.create(
            user=self.user,
            notification_type="workspace_join_request",
            title="Nova solicitacao",
            message="Teste",
            is_read=False,
        )
        UserNotification.objects.create(
            user=self.user,
            notification_type="workspace_join_request",
            title="Lida",
            message="Teste",
            is_read=True,
        )
        request = SimpleNamespace(user=self.user)
        context = NavigationService.build_navigation_context(request)
        self.assertEqual(context["nav_user_settings"].user_id, self.user.id)
        self.assertEqual(len(context["nav_notifications"]), 2)
        self.assertEqual(context["nav_notifications_unread_count"], 1)


class CoreSelectorTests(TestCase):
    def setUp(self):
        self.selector = CoreSelector()
        self.owner = User.objects.create_user(
            username="core_sel_owner",
            email="core_sel_owner@example.com",
            password="StrongPass123!",
        )
        self.other = User.objects.create_user(
            username="core_sel_other",
            email="core_sel_other@example.com",
            password="StrongPass123!",
        )

    def test_accessible_templates_and_submissions(self):
        t1 = DocumentTemplate.objects.create(
            owner=self.owner,
            name="Owner Template",
            file="templates/t1.docx",
            file_type="docx",
            fields_schema=[],
        )
        t2 = DocumentTemplate.objects.create(
            owner=self.other,
            name="Shared Template",
            file="templates/t2.docx",
            file_type="docx",
            fields_schema=[],
        )
        TemplatePermission.objects.create(template=t2, user=self.owner, role="viewer")
        TemplateSubmission.objects.create(template=t1, submitted_by=self.owner, payload={})
        TemplateSubmission.objects.create(template=t2, submitted_by=self.other, payload={})

        templates = self.selector.accessible_templates(self.owner)
        self.assertEqual({obj.id for obj in templates}, {t1.id, t2.id})

        subs = self.selector.template_submissions_for_template_ids([t1.id, t2.id])
        self.assertEqual(subs.count(), 2)
