import base64

from django.core.files.base import ContentFile

from apps.core.domain.selectors import CoreSelector
from apps.core.models import ProfilePhotoDisplayScope, UserSettings


class SettingsService:
    @staticmethod
    def get_user_settings(user):
        return CoreSelector.user_settings(user)

    @staticmethod
    def save_cropped_profile_photo(user, settings_obj, cropped_data):
        if not cropped_data.startswith("data:image/"):
            return False

        try:
            header, encoded = cropped_data.split(",", 1)
        except ValueError:
            return False

        try:
            decoded = base64.b64decode(encoded)
        except Exception:
            return False

        if not decoded:
            return False

        extension = "png"
        if "image/jpeg" in header or "image/jpg" in header:
            extension = "jpg"
        elif "image/webp" in header:
            extension = "webp"

        settings_obj.profile_photo.save(
            f"profile-crop-{user.id}.{extension}",
            ContentFile(decoded),
            save=False,
        )
        settings_obj.save(update_fields=["profile_photo", "updated_at"])
        return True

    @staticmethod
    def force_header_profile_scope(settings_obj):
        settings_obj.profile_photo_display_scope = ProfilePhotoDisplayScope.HEADER
        settings_obj.save(update_fields=["profile_photo_display_scope", "updated_at"])
