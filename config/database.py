import re

from django.core.exceptions import ImproperlyConfigured


def postgresql_options(schema):
    """Restrict the connection to an explicitly selected PostgreSQL schema."""
    if not schema:
        return {}
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema):
        raise ImproperlyConfigured(
            "DB_SCHEMA deve ser um identificador PostgreSQL minúsculo válido."
        )
    return {"options": f"-c search_path={schema}"}
