from django.db import models


class TemplateFileType(models.TextChoices):
    PDF = "pdf", "PDF"
    DOCX = "docx", "Word"
    XLSX = "xlsx", "Excel"


class TemplateStatus(models.TextChoices):
    ACTIVE = "active", "Ativo"
    CLOSED = "closed", "Encerrado"


class AccessRole(models.TextChoices):
    OWNER = "owner", "Dono"
    EDITOR = "editor", "Editor"
    FILLER = "filler", "Preenchedor"
    VIEWER = "viewer", "Leitor"


class WorkspaceMemberRole(models.TextChoices):
    OWNER = "owner", "Criador"
    ADMIN = "admin", "Administrador"
    MEMBER = "member", "Membro"


class WorkspaceJoinRequestStatus(models.TextChoices):
    PENDING = "pending", "Pendente"
    APPROVED = "approved", "Aprovado"
    REJECTED = "rejected", "Rejeitado"


class NotificationType(models.TextChoices):
    DOCUMENT_REQUEST = "document_request", "Solicitação de documento"
    WORKSPACE_JOIN_REQUEST = "workspace_join_request", "Solicitacao de entrada em ambiente"


class InviteStatus(models.TextChoices):
    PENDING = "pending", "Pendente"
    ACCEPTED = "accepted", "Aceito"
    CANCELED = "canceled", "Cancelado"


class AuditAction(models.TextChoices):
    TEMPLATE_UPDATED = "template_updated", "Modelo atualizado"
    TEMPLATE_FIELDS_UPDATED = "template_fields_updated", "Campos do modelo atualizados"
    SUBMISSION_SHARED = "submission_shared", "Documento emitido compartilhado"
    SUBMISSION_SHARE_REVOKED = "submission_share_revoked", "Compartilhamento de documento revogado"
    TEMPLATE_CREATED = "template_created", "Template criado"
    TEMPLATE_SHARED = "template_shared", "Template compartilhado"
    TEMPLATE_INVITED = "template_invited", "Convite enviado"
    INVITE_ACCEPTED = "invite_accepted", "Convite aceito"
    TEMPLATE_FILLED = "template_filled", "Template preenchido"
    TEMPLATE_CLOSED = "template_closed", "Template encerrado"
    TEMPLATE_PERMISSION_REVOKED = "template_permission_revoked", "Permissao revogada"
    TEMPLATE_PERMISSION_UPDATED = "template_permission_updated", "Permissao atualizada"
    INVITE_CANCELED = "invite_canceled", "Convite cancelado"
    WORKSPACE_JOIN_REQUESTED = "workspace_join_requested", "Solicitacao de entrada em ambiente"
    WORKSPACE_JOIN_APPROVED = "workspace_join_approved", "Entrada em ambiente aprovada"
    WORKSPACE_MEMBER_REMOVED = "workspace_member_removed", "Membro removido do ambiente"
