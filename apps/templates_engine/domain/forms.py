from django import forms
from django.contrib.auth import get_user_model

from apps.templates_engine.models import DocumentTemplate, TemplateShareGroup
from apps.templates_engine.validators import validate_template_upload

User = get_user_model()


class TemplateFormDomainService:
    @staticmethod
    def validate_template_file(uploaded_file, file_type):
        return validate_template_upload(uploaded_file, file_type)

    @staticmethod
    def validate_existing_user_email(email):
        normalized = email.strip().lower()
        if not User.objects.filter(email__iexact=normalized).exists():
            raise forms.ValidationError("Usuario nao encontrado. Ele precisa estar cadastrado e com email verificado.")
        return normalized

    @staticmethod
    def validate_group_owner(owner):
        if not owner:
            raise forms.ValidationError("Dono do grupo nao informado.")

    @staticmethod
    def validate_generic_owner(owner):
        if not owner:
            raise forms.ValidationError("Dono nao informado.")

    @staticmethod
    def validate_group_exists_for_owner(group_id, owner):
        if not TemplateShareGroup.objects.filter(pk=group_id, owner=owner).exists():
            raise forms.ValidationError("Grupo nao encontrado.")
        return group_id

    @staticmethod
    def validate_template_exists(template_id):
        if not DocumentTemplate.objects.filter(pk=template_id).exists():
            raise forms.ValidationError("Template nao encontrado.")
        return template_id

    @staticmethod
    def parse_email_list(
        raw,
        *,
        empty_message="Informe ao menos um e-mail.",
        invalid_message_prefix="E-mails invalidos:",
        max_items=100,
        max_items_message="No maximo 100 e-mails por operacao.",
    ):
        tokens = [item.strip().lower() for item in raw.replace(";", ",").replace("\n", ",").split(",")]
        emails = [item for item in tokens if item]
        if not emails:
            raise forms.ValidationError(empty_message)

        invalid = []
        validator = forms.EmailField()
        normalized = []
        for email in emails:
            try:
                normalized.append(validator.clean(email))
            except forms.ValidationError:
                invalid.append(email)
        if invalid:
            raise forms.ValidationError(f"{invalid_message_prefix} {', '.join(invalid)}")

        unique_emails = sorted(set(normalized))
        if len(unique_emails) > max_items:
            raise forms.ValidationError(max_items_message)
        return unique_emails
