from apps.templates_engine.models import TemplateAuditLog


def log_template_action(*, template, action, actor=None, metadata=None):
    TemplateAuditLog.objects.create(
        template=template,
        action=action,
        actor=actor,
        metadata=metadata or {},
    )
