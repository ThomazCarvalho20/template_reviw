from django.utils.dateparse import parse_date
from django.db.models import Q

from apps.templates_engine.models import AuditAction, TemplateAuditLog, TemplateSubmission


class TemplateFilterService:
    @staticmethod
    def get_filtered_audit_logs(request, template_obj):
        logs = TemplateAuditLog.objects.select_related("actor").filter(template=template_obj)

        action = (request.GET.get("action") or "").strip()
        actor_email = (request.GET.get("actor_email") or "").strip()
        date_from = (request.GET.get("date_from") or "").strip()
        date_to = (request.GET.get("date_to") or "").strip()

        valid_actions = {value for value, _ in AuditAction.choices}
        if action in valid_actions:
            logs = logs.filter(action=action)
        if actor_email:
            logs = logs.filter(actor__email__icontains=actor_email)
        if date_from:
            parsed_from = parse_date(date_from)
            if parsed_from:
                logs = logs.filter(created_at__date__gte=parsed_from)
        if date_to:
            parsed_to = parse_date(date_to)
            if parsed_to:
                logs = logs.filter(created_at__date__lte=parsed_to)
        return logs

    @staticmethod
    def get_filtered_submissions(request, template_obj):
        submissions = TemplateSubmission.objects.select_related("submitted_by").filter(template=template_obj)
        submitted_by_email = (request.GET.get("submitted_by_email") or "").strip()
        submitted_from = (request.GET.get("submitted_from") or "").strip()
        submitted_to = (request.GET.get("submitted_to") or "").strip()
        has_output = (request.GET.get("has_output") or "").strip()

        if submitted_by_email:
            submissions = submissions.filter(submitted_by__email__icontains=submitted_by_email)
        if submitted_from:
            parsed_from = parse_date(submitted_from)
            if parsed_from:
                submissions = submissions.filter(created_at__date__gte=parsed_from)
        if submitted_to:
            parsed_to = parse_date(submitted_to)
            if parsed_to:
                submissions = submissions.filter(created_at__date__lte=parsed_to)
        if has_output == "yes":
            submissions = submissions.exclude(output_file="")
        elif has_output == "no":
            submissions = submissions.filter(Q(output_file="") | Q(output_file__isnull=True))
        return submissions
