from django.urls import path

from apps.templates_engine.views.institution import (
    InstitutionDetailView,
    InstitutionEditView,
    InstitutionListView,
    InstitutionMemberAddView,
    InstitutionMemberRemoveView,
    RequestDetailView,
    RequestListView,
    RequestUpdateView,
    SubmissionDownloadView,
    SubmissionListView,
    SubmissionShareRevokeView,
    SubmissionShareView,
    TemplateDownloadView,
    TemplateFieldsView,
)
from apps.templates_engine.views.metadata import TemplateMetadataView

urlpatterns = [
    path("templates/<int:pk>/editar/", TemplateMetadataView.as_view(), name="template-update"),
    path("instituicoes/", InstitutionListView.as_view(), name="institution-list"),
    path("instituicoes/nova/", InstitutionEditView.as_view(), name="institution-create"),
    path("instituicoes/<int:pk>/", InstitutionDetailView.as_view(), name="institution-detail"),
    path("instituicoes/<int:pk>/editar/", InstitutionEditView.as_view(), name="institution-update"),
    path(
        "instituicoes/<int:pk>/membros/",
        InstitutionMemberAddView.as_view(),
        name="institution-member-add",
    ),
    path(
        "instituicoes/<int:pk>/membros/<int:membership_id>/remover/",
        InstitutionMemberRemoveView.as_view(),
        name="institution-member-remove",
    ),
    path("solicitacoes/", RequestListView.as_view(), name="request-list"),
    path("solicitacoes/<int:pk>/", RequestDetailView.as_view(), name="request-detail"),
    path("solicitacoes/<int:pk>/atualizar/", RequestUpdateView.as_view(), name="request-update"),
    path("documentos/", SubmissionListView.as_view(), name="submission-list"),
    path(
        "documentos/<int:pk>/download/",
        SubmissionDownloadView.as_view(),
        name="submission-download",
    ),
    path(
        "documentos/<int:pk>/compartilhar/", SubmissionShareView.as_view(), name="submission-share"
    ),
    path(
        "documentos/<int:pk>/compartilhar/<int:share_id>/revogar/",
        SubmissionShareRevokeView.as_view(),
        name="submission-share-revoke",
    ),
    path("templates/<int:pk>/campos/", TemplateFieldsView.as_view(), name="template-fields"),
    path("templates/<int:pk>/download/", TemplateDownloadView.as_view(), name="template-download"),
]
