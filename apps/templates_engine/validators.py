import zipfile
from pathlib import Path

from django.conf import settings


def detect_real_file_type(uploaded_file):
    position = uploaded_file.tell()
    uploaded_file.seek(0)
    header = uploaded_file.read(8)
    uploaded_file.seek(0)

    if header.startswith(b"%PDF-"):
        uploaded_file.seek(position)
        return "pdf"

    if header.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(uploaded_file) as archive:
                names = archive.namelist()
            if any(name.startswith("word/") for name in names):
                uploaded_file.seek(position)
                return "docx"
            if any(name.startswith("xl/") for name in names):
                uploaded_file.seek(position)
                return "xlsx"
        except Exception:
            uploaded_file.seek(position)
            return None

    uploaded_file.seek(position)
    return None


def validate_template_upload(uploaded_file, selected_file_type):
    max_mb = int(getattr(settings, "MAX_TEMPLATE_FILE_SIZE_MB", 10))
    max_bytes = max_mb * 1024 * 1024

    if uploaded_file.size > max_bytes:
        return f"Arquivo excede o limite de {max_mb}MB."

    real_type = detect_real_file_type(uploaded_file)
    if not real_type:
        return "Nao foi possivel identificar o tipo real do arquivo."

    if real_type != selected_file_type:
        return "Tipo real do arquivo nao corresponde ao tipo selecionado."

    extension = Path(uploaded_file.name).suffix.lower().replace(".", "")
    if extension and extension != selected_file_type:
        return "Extensao do arquivo nao corresponde ao tipo selecionado."

    return None
