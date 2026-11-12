from django import forms

from apps.templates_engine.domain import TemplateFormDomainService
from apps.templates_engine.models import Workspace


class WorkspaceCreateForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ["name", "description"]
        labels = {
            "name": "Nome do ambiente",
            "description": "Descricao",
        }


class WorkspaceAddMembersForm(forms.Form):
    members_raw = forms.CharField(
        label="Adicionar pessoas (e-mails)",
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "email1@dominio.com, email2@dominio.com"}
        ),
    )

    def clean_members_raw(self):
        return TemplateFormDomainService.parse_email_list(self.cleaned_data["members_raw"])


class WorkspaceAttachTemplateForm(forms.Form):
    template_id = forms.IntegerField()

    def __init__(self, *args, owner=None, workspace=None, **kwargs):
        self.owner = owner
        self.workspace = workspace
        super().__init__(*args, **kwargs)

    def clean_template_id(self):
        template_id = self.cleaned_data["template_id"]
        return TemplateFormDomainService.validate_template_exists(template_id)


class WorkspaceAddGroupForm(forms.Form):
    group_id = forms.IntegerField()

    def __init__(self, *args, owner=None, **kwargs):
        self.owner = owner
        super().__init__(*args, **kwargs)

    def clean_group_id(self):
        group_id = self.cleaned_data["group_id"]
        TemplateFormDomainService.validate_generic_owner(self.owner)
        return TemplateFormDomainService.validate_group_exists_for_owner(group_id, self.owner)
