import io
import re
import zipfile
from pathlib import Path


PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def _import_pypdf():
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import BooleanObject, NameObject

    return PdfReader, PdfWriter, NameObject, BooleanObject


def _build_schema_from_keys(keys):
    ordered = sorted(set(keys))
    return [{"key": key, "label": key.replace("_", " ").title(), "type": "text", "required": False} for key in ordered]


def _extract_placeholders_from_docx(path: Path):
    keys = []
    with zipfile.ZipFile(path) as archive:
        xml_files = [name for name in archive.namelist() if name.startswith("word/") and name.endswith(".xml")]
        for xml_file in xml_files:
            content = archive.read(xml_file).decode("utf-8", errors="ignore")
            keys.extend(match.group(1) for match in PLACEHOLDER_PATTERN.finditer(content))
    return _build_schema_from_keys(keys)


def _extract_placeholders_from_xlsx(path: Path):
    keys = []
    with zipfile.ZipFile(path) as archive:
        xml_files = [name for name in archive.namelist() if name.startswith("xl/") and name.endswith(".xml")]
        for xml_file in xml_files:
            content = archive.read(xml_file).decode("utf-8", errors="ignore")
            keys.extend(match.group(1) for match in PLACEHOLDER_PATTERN.finditer(content))
    return _build_schema_from_keys(keys)


def _extract_fields_from_pdf(path: Path):
    try:
        PdfReader, _, _, _ = _import_pypdf()
    except Exception:
        return []

    reader = PdfReader(str(path))
    fields = reader.get_fields() or {}
    keys = list(fields.keys())
    return _build_schema_from_keys(keys)


def _generate_filled_pdf(file_path: str, payload: dict):
    try:
        PdfReader, PdfWriter, NameObject, BooleanObject = _import_pypdf()
    except Exception:
        return Path(file_path).read_bytes()

    reader = PdfReader(file_path)
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)

    for page in reader.pages:
        writer.add_page(page)
        writer.update_page_form_field_values(writer.pages[-1], payload)

    # Requests most PDF viewers to render appearance streams from updated values.
    if "/AcroForm" in writer._root_object:  # noqa: SLF001
        acro_form = writer._root_object["/AcroForm"]  # noqa: SLF001
        acro_form.update({NameObject("/NeedAppearances"): BooleanObject(True)})

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def detect_template_schema(file_path: str, file_type: str):
    path = Path(file_path)
    if file_type == "docx":
        return _extract_placeholders_from_docx(path)
    if file_type == "xlsx":
        return _extract_placeholders_from_xlsx(path)
    if file_type == "pdf":
        return _extract_fields_from_pdf(path)
    return []


def _replace_placeholders(content: str, payload: dict):
    for key, value in payload.items():
        token = "{{" + str(key) + "}}"
        content = content.replace(token, str(value))
    return content


def _generate_zip_based_file(file_path: str, xml_prefix: str, payload: dict):
    input_buffer = Path(file_path).read_bytes()
    source_zip = zipfile.ZipFile(io.BytesIO(input_buffer), mode="r")
    output_io = io.BytesIO()
    with zipfile.ZipFile(output_io, mode="w") as target_zip:
        for info in source_zip.infolist():
            data = source_zip.read(info.filename)
            if info.filename.startswith(xml_prefix) and info.filename.endswith(".xml"):
                text = data.decode("utf-8", errors="ignore")
                text = _replace_placeholders(text, payload)
                data = text.encode("utf-8")
            target_zip.writestr(info, data)
    source_zip.close()
    return output_io.getvalue()


def generate_filled_document(file_path: str, file_type: str, payload: dict):
    if file_type == "docx":
        return _generate_zip_based_file(file_path, "word/", payload)
    if file_type == "xlsx":
        return _generate_zip_based_file(file_path, "xl/", payload)
    if file_type == "pdf":
        return _generate_filled_pdf(file_path, payload)
    return Path(file_path).read_bytes()
