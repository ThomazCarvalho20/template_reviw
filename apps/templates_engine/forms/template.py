from django import forms

from apps.templates_engine.domain import TemplateFormDomainService
from apps.templates_engine.models import DocumentTemplate, TemplateSubmission


ROLE_CHOICES = [
    ("editor", "Editor"),
    ("filler", "Preenchedor"),
    ("viewer", "Leitor"),
]


class TemplateUploadForm(forms.ModelForm):
    class Meta:
        model = DocumentTemplate
        fields = ["name", "description", "file", "file_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = "w-full rounded border p-2"
        for field in self.fields.values():
            field.widget.attrs["class"] = base_class

    def clean(self):
        cleaned = super().clean()
        upload_file = cleaned.get("file")
        file_type = cleaned.get("file_type")
        if upload_file and file_type:
            error = TemplateFormDomainService.validate_template_file(upload_file, file_type)
            if error:
                self.add_error("file", error)
        return cleaned


class DynamicTemplateFillForm(forms.Form):
    def __init__(self, *args, fields_schema=None, **kwargs):
        super().__init__(*args, **kwargs)
        fields_schema = fields_schema or []
        for field in fields_schema:
            field_key = field.get("key")
            if not field_key:
                continue
            field_label = field.get("label", field_key)
            field_type = field.get("type", "text")
            required = bool(field.get("required", False))

            widget = forms.TextInput(attrs={"class": "w-full rounded border p-2"})
            if field_type == "textarea":
                widget = forms.Textarea(attrs={"class": "w-full rounded border p-2", "rows": 3})
            if field_type == "number":
                self.fields[field_key] = forms.DecimalField(label=field_label, required=required, widget=widget)
            elif field_type == "date":
                self.fields[field_key] = forms.DateField(
                    label=field_label,
                    required=required,
                    widget=forms.DateInput(attrs={"type": "date", "class": "w-full rounded border p-2"}),
                )
            else:
                self.fields[field_key] = forms.CharField(label=field_label, required=required, widget=widget)


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = TemplateSubmission
        fields = []


class TemplateShareForm(forms.Form):
    email = forms.EmailField(label="E-mail do usuario")
    role = forms.ChoiceField(label="Permissao", choices=ROLE_CHOICES)

    def clean_email(self):
        return TemplateFormDomainService.validate_existing_user_email(self.cleaned_data["email"])


class TemplateInviteForm(forms.Form):
    email = forms.EmailField(label="E-mail do convite")
    role = forms.ChoiceField(label="Permissao", choices=ROLE_CHOICES)


class TemplateShareWithGroupForm(forms.Form):
    group_id = forms.IntegerField()
    role = forms.ChoiceField(label="Permissao", choices=ROLE_CHOICES)

    def __init__(self, *args, owner=None, **kwargs):
        self.owner = owner
        super().__init__(*args, **kwargs)

    def clean_group_id(self):
        group_id = self.cleaned_data["group_id"]
        TemplateFormDomainService.validate_group_owner(self.owner)
        return TemplateFormDomainService.validate_group_exists_for_owner(group_id, self.owner)
