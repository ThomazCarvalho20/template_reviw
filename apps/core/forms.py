from django import forms
from django.contrib.auth import get_user_model

from apps.core.models import UserSettings

User = get_user_model()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name"]
        labels = {
            "first_name": "Nome",
            "last_name": "Sobrenome",
        }


class ProfilePhotoForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ["profile_photo"]
        labels = {
            "profile_photo": "Foto de perfil",
        }
        widgets = {
            "profile_photo": forms.ClearableFileInput(
                attrs={"accept": "image/png,image/jpeg,image/webp"}
            ),
        }


class UserSettingsForm(forms.ModelForm):
    items_per_page = forms.ChoiceField(
        choices=((10, "10"), (20, "20"), (50, "50")),
        label="Itens por pagina",
    )

    class Meta:
        model = UserSettings
        fields = ["notify_invites", "notify_template_updates", "items_per_page"]
        labels = {
            "notify_invites": "Receber notificacoes de convites",
            "notify_template_updates": "Receber notificacoes de alteracoes em templates",
        }
