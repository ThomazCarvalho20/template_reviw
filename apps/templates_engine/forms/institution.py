from django import forms
from django.contrib.auth import get_user_model
from django.forms import BaseFormSet, formset_factory

from apps.templates_engine.domain.institution import managed_institutions
from apps.templates_engine.models import DocumentRequest, Institution, InstitutionMembership

User = get_user_model()


class InstitutionForm(forms.ModelForm):
    responsible_email = forms.EmailField(
        label="E-mail do responsável já cadastrado", required=False
    )

    class Meta:
        model = Institution
        fields = ["name", "description", "contact_email", "is_active"]

    def clean_responsible_email(self):
        email = self.cleaned_data["responsible_email"].strip().lower()
        if not self.instance.pk and not email:
            raise forms.ValidationError("Informe um responsável cadastrado.")
        if email and User.objects.filter(email__iexact=email, is_active=True).count() != 1:
            raise forms.ValidationError("Informe o e-mail de uma única conta ativa cadastrada.")
        return email


class InstitutionMemberForm(forms.Form):
    email = forms.EmailField(label="E-mail do usuário cadastrado")
    role = forms.ChoiceField(label="Perfil", choices=InstitutionMembership.Role.choices)

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        if not actor.is_superuser:
            self.fields["role"].choices = [("member", "Usuário")]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email, is_active=True).count() != 1:
            raise forms.ValidationError("Informe o e-mail de uma única conta ativa cadastrada.")
        return email


class TemplateFieldForm(forms.Form):
    key = forms.CharField(label="Chave no documento", max_length=128)
    label = forms.CharField(label="Nome exibido", max_length=200)
    type = forms.ChoiceField(
        label="Tipo",
        choices=[
            ("text", "Texto"),
            ("textarea", "Texto longo"),
            ("number", "Número"),
            ("date", "Data"),
        ],
    )
    required = forms.BooleanField(label="Obrigatório", required=False)

    def clean_key(self):
        key = self.cleaned_data["key"].strip()
        # PDF field names are not restricted to placeholder identifiers.
        if not key or any(ord(char) < 32 for char in key):
            raise forms.ValidationError("Chave inválida.")
        return key


class SchemaFormSet(BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        keys = set()
        for form in self.forms:
            data = form.cleaned_data
            if not data or data.get("DELETE"):
                continue
            if data["key"] in keys:
                raise forms.ValidationError("Chave repetida. Cada campo deve ter uma chave única.")
            keys.add(data["key"])


TemplateFieldFormSet = formset_factory(
    TemplateFieldForm,
    formset=SchemaFormSet,
    extra=1,
    can_delete=True,
    max_num=100,
    validate_max=True,
    absolute_max=110,
)


class RequestUpdateForm(forms.Form):
    status = forms.ChoiceField(label="Situação", choices=DocumentRequest.Status.choices)
    note = forms.CharField(
        label="Observação / motivo", widget=forms.Textarea, max_length=2000, required=False
    )
    assigned_to = forms.ModelChoiceField(
        label="Responsável", queryset=User.objects.none(), required=False
    )
    revision = forms.IntegerField(widget=forms.HiddenInput, min_value=0)

    def __init__(self, *args, document_request, actor, **kwargs):
        super().__init__(*args, **kwargs)
        managers = User.objects.filter(is_active=True).filter(
            institution_memberships__institution=document_request.institution,
            institution_memberships__role="manager",
            institution_memberships__is_active=True,
        )
        self.fields["assigned_to"].queryset = (
            managers | User.objects.filter(is_superuser=True, is_active=True)
        ).distinct()
        if (
            not actor.is_superuser
            and not managed_institutions(actor).filter(pk=document_request.institution_id).exists()
        ):
            self.fields["status"].choices = [("canceled", "Cancelar solicitação")]
            self.fields["assigned_to"].queryset = User.objects.none()
            self.fields["assigned_to"].widget = forms.HiddenInput()


class SubmissionShareForm(forms.Form):
    email = forms.EmailField(label="E-mail do destinatário cadastrado")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email, is_active=True).count() != 1:
            raise forms.ValidationError("Informe o e-mail de uma única conta ativa cadastrada.")
        return email
