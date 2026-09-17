from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import UserSettings
from apps.templates_engine.models import DocumentTemplate, TemplateSubmission


User = get_user_model()


class DashboardAccessTests(TestCase):
    @staticmethod
    def _fake_docx_file(name="modelo.docx"):
        return SimpleUploadedFile(
            name,
            b"PK\x03\x04fake-docx-content",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_dashboard_logged_user(self):
        user = User.objects.create_user(username="user1", email="user1@example.com", password="StrongPass123!")
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_healthcheck_returns_success(self):
        response = self.client.get(reverse("healthcheck"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_recent_items_default_limit(self):
        user = User.objects.create_user(
            username="dashboard_default",
            email="dashboard_default@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(user)

        for idx in range(12):
            template = DocumentTemplate.objects.create(
                owner=user,
                name=f"Template {idx}",
                file=self._fake_docx_file(f"template_{idx}.docx"),
                file_type="docx",
                fields_schema=[],
            )
            TemplateSubmission.objects.create(template=template, submitted_by=user, payload={"idx": idx})

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["items_limit"], 10)
        self.assertEqual(len(response.context["recent_templates"]), 10)
        self.assertEqual(len(response.context["recent_submissions"]), 10)

    def test_dashboard_recent_items_respect_user_settings(self):
        user = User.objects.create_user(
            username="dashboard_custom",
            email="dashboard_custom@example.com",
            password="StrongPass123!",
        )
        UserSettings.objects.create(user=user, items_per_page=20)
        self.client.force_login(user)

        for idx in range(12):
            template = DocumentTemplate.objects.create(
                owner=user,
                name=f"Template Ajustado {idx}",
                file=self._fake_docx_file(f"template_custom_{idx}.docx"),
                file_type="docx",
                fields_schema=[],
            )
            TemplateSubmission.objects.create(template=template, submitted_by=user, payload={"idx": idx})

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["items_limit"], 20)
        self.assertEqual(len(response.context["recent_templates"]), 12)
        self.assertEqual(len(response.context["recent_submissions"]), 12)

    def test_settings_requires_authentication(self):
        response = self.client.get(reverse("settings"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_settings_page_updates_profile_and_preferences(self):
        user = User.objects.create_user(
            username="settingsuser",
            email="settings@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("settings"),
            {
                "action": "profile",
                "first_name": "Thomaz",
                "last_name": "Carvalho",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Thomaz")
        self.assertEqual(user.last_name, "Carvalho")

        response = self.client.post(
            reverse("settings"),
            {
                "action": "preferences",
                "notify_invites": "on",
                "items_per_page": "20",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        settings_obj = UserSettings.objects.get(user=user)
        self.assertTrue(settings_obj.notify_invites)
        self.assertFalse(settings_obj.notify_template_updates)
        self.assertEqual(settings_obj.items_per_page, 20)

    def test_profile_photo_upload_saves_without_crop_data(self):
        user = User.objects.create_user(
            username="settings_upload_crop",
            email="settings_upload_crop@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(user)

        upload = SimpleUploadedFile("avatar.png", b"not-a-real-image", content_type="image/png")
        response = self.client.post(
            reverse("settings"),
            {
                "action": "profile",
                "first_name": "NomeNovo",
                "last_name": "SobrenomeNovo",
                "profile_photo": upload,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        settings_obj = UserSettings.objects.get(user=user)
        self.assertEqual(user.first_name, "NomeNovo")
        self.assertTrue(bool(settings_obj.profile_photo))

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver", "localhost"])
    def test_custom_404_page_is_rendered(self):
        response = self.client.get("/rota-inexistente/")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Pagina nao encontrada", response.content.decode())
