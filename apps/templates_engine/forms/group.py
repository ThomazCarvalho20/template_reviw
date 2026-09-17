from django import forms

from apps.templates_engine.domain import TemplateFormDomainService
from apps.templates_engine.models import TemplateShareGroup, TemplateShareGroupMember


class TemplateShareGroupCreateForm(forms.ModelForm):
    members_raw = forms.CharField(
        label="E-mails do grupo",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "email1@dominio.com, email2@dominio.com"}),
        help_text="Separe por virgula, ponto e virgula ou quebra de linha.",
    )

    class Meta:
        model = TemplateShareGroup
        fields = ["name", "members_raw"]
        labels = {"name": "Nome do grupo"}

    def clean_members_raw(self):
        raw = self.cleaned_data["members_raw"]
        return TemplateFormDomainService.parse_email_list(
            raw,
            empty_message="Informe ao menos um e-mail para o grupo.",
            max_items_message="O grupo pode ter no maximo 100 e-mails.",
        )

    def save(self, owner):
        group = TemplateShareGroup.objects.create(owner=owner, name=self.cleaned_data["name"])
        members = [TemplateShareGroupMember(group=group, email=email) for email in self.cleaned_data["members_raw"]]
        TemplateShareGroupMember.objects.bulk_create(members)
        return group


class TemplateShareGroupUpdateForm(forms.Form):
    name = forms.CharField(max_length=120, label="Nome do grupo")
    members_raw = forms.CharField(
        label="E-mails do grupo",
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "email1@dominio.com, email2@dominio.com"}),
        help_text="Separe por virgula, ponto e virgula ou quebra de linha.",
    )

    def clean_members_raw(self):
        return TemplateFormDomainService.parse_email_list(self.cleaned_data["members_raw"])
