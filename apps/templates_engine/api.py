from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import include, path, reverse
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from apps.templates_engine.domain.access import TemplateAccessService
from apps.templates_engine.domain.institution import (
    downloadable_submissions,
    transition_request,
    visible_requests,
)
from apps.templates_engine.forms.institution import RequestUpdateForm
from apps.templates_engine.models import DocumentRequest, DocumentTemplate, TemplateSubmission


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentTemplate
        fields = [
            "id",
            "name",
            "description",
            "file_type",
            "fields_schema",
            "status",
            "institution_id",
        ]
        read_only_fields = fields


class SubmissionSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    def get_download_url(self, obj):
        return (
            self.context["request"].build_absolute_uri(
                reverse("submission-download", args=[obj.pk])
            )
            if obj.output_file
            else None
        )

    class Meta:
        model = TemplateSubmission
        fields = ["id", "template_id", "created_at", "download_url"]
        read_only_fields = fields


class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentRequest
        fields = [
            "id",
            "protocol",
            "institution_id",
            "submission_id",
            "status",
            "assigned_to_id",
            "revision",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TemplateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TemplateSerializer

    def get_queryset(self):
        return TemplateAccessService.get_accessible_templates_queryset(
            self.request.user, DocumentTemplate.objects.all()
        )


class SubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubmissionSerializer

    def get_queryset(self):
        return downloadable_submissions(self.request.user).select_related("template")


class RequestViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RequestSerializer

    def get_queryset(self):
        return visible_requests(self.request.user)

    @action(detail=True, methods=["post"], url_path="situacao")
    def change_status(self, request, pk=None):
        document_request = self.get_object()
        form = RequestUpdateForm(
            request.data, document_request=document_request, actor=request.user
        )
        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            obj = transition_request(document_request.pk, request.user, **form.cleaned_data)
        except ValidationError as error:
            return Response({"detail": error.messages}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied:
            return Response({"detail": "Acesso negado."}, status=status.HTTP_403_FORBIDDEN)
        return Response(self.get_serializer(obj).data)


router = DefaultRouter()
router.register("templates", TemplateViewSet, basename="api-template")
router.register("documentos", SubmissionViewSet, basename="api-submission")
router.register("solicitacoes", RequestViewSet, basename="api-request")
urlpatterns = [path("", include(router.urls))]
