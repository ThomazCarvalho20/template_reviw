from django.conf import settings
from django.db import models


class ProfilePhotoDisplayScope(models.TextChoices):
    HEADER = "header", "Somente no cabecalho"
    SIDEBAR = "sidebar", "Somente no menu lateral"
    BOTH = "both", "Cabecalho e menu lateral"


class UserSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="settings"
    )
    profile_photo = models.FileField(upload_to="profile_photos/", blank=True, null=True)
    profile_photo_display_scope = models.CharField(
        max_length=16,
        choices=ProfilePhotoDisplayScope.choices,
        default=ProfilePhotoDisplayScope.HEADER,
    )
    profile_photo_focus_x = models.PositiveSmallIntegerField(default=50)
    profile_photo_focus_y = models.PositiveSmallIntegerField(default=50)
    notify_invites = models.BooleanField(default=True)
    notify_template_updates = models.BooleanField(default=True)
    items_per_page = models.PositiveSmallIntegerField(default=10)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuracao do usuario"
        verbose_name_plural = "Configuracoes dos usuarios"

    def __str__(self):
        return f"Configuracoes de {self.user_id}"
