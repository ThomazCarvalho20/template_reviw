import io
import re
import zipfile
from html import escape, unescape
from pathlib import Path

PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def _import_pypdf():
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import BooleanObject, NameObject

    return PdfReader, PdfWriter, NameObject, BooleanObject


def _build_schema_from_keys(keys):
    ordered = sorted(set(keys))
    return [
        {"key": key, "label": key.replace("_", " ").title(), "type": "text", "required": False}
        for key in ordered
    ]


def validate_archive(archive):
    entries = archive.infolist()
    total = sum(item.file_size for item in entries)
    if len(entries) > 1000 or total > 100 * 1024 * 1024:
        raise ValueError("Arquivo compactado excede o limite de expansão.")
    if any(
        item.flag_bits & 1 or item.file_size > max(item.compress_size, 1) * 200 for item in entries
    ):
        raise ValueError("Arquivo compactado criptografado ou com expansão excessiva.")


def _text_segments(content):
    # Keep original XML tags and namespace declarations; only edit text nodes.
    return list(re.finditer(r"(?<=>)([^<]+)(?=<)", content))


def _transform_block(block, payload=None, keys=None):
    segments = _text_segments(block)
    texts = [unescape(segment.group()) for segment in segments]
    plain = "".join(texts)
    matches = list(PLACEHOLDER_PATTERN.finditer(plain))
    if keys is not None:
        keys.extend(match.group(1) for match in matches)
        return block
    offsets = []
    offset = 0
    for value in texts:
        offsets.append(offset)
        offset += len(value)
    for index in range(len(segments) - 1, -1, -1):
        text = texts[index]
        start = offsets[index]
        end = start + len(text)
        changed = False
        for match in reversed(matches):
            if match.group(1) not in payload or match.end() <= start or match.start() >= end:
                continue
            left = max(match.start() - start, 0)
            right = min(match.end() - start, len(text))
            value = payload[match.group(1)]
            if value is not None and re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", str(value)):
                raise ValueError("O conteúdo contém caracteres incompatíveis com XML.")
            replacement = ("" if value is None else str(value)) if match.start() >= start else ""
            text = text[:left] + replacement + text[right:]
            changed = True
        if changed:
            segment = segments[index]
            block = block[: segment.start()] + escape(text, quote=False) + block[segment.end() :]
    return block


def _transform_xml(content, prefix, payload=None, keys=None):
    if "<!DOCTYPE" in content.upper() or "<!ENTITY" in content.upper():
        raise ValueError("Declarações XML externas não são permitidas.")
    # Do not join distinct paragraphs or spreadsheet cells when recognizing tokens.
    group = (
        r"<w:p(?:\s[^>]*)?>.*?</w:p>"
        if prefix == "word/"
        else r"<(?:si|is|c)(?:\s[^>]*)?>.*?</(?:si|is|c)>"
    )
    blocks = list(re.finditer(group, content, flags=re.DOTALL))
    if not blocks:
        return _transform_block(content, payload, keys)
    for match in reversed(blocks):
        content = (
            content[: match.start()]
            + _transform_block(match.group(), payload, keys)
            + content[match.end() :]
        )
    return content


def _extract_placeholders(path, prefix):
    keys = []
    with zipfile.ZipFile(path) as archive:
        validate_archive(archive)
        for name in archive.namelist():
            if name.startswith(prefix) and name.endswith(".xml"):
                _transform_xml(archive.read(name).decode("utf-8"), prefix, keys=keys)
    return _build_schema_from_keys(keys)


def _extract_placeholders_from_docx(path: Path):
    return _extract_placeholders(path, "word/")


def _extract_placeholders_from_xlsx(path: Path):
    return _extract_placeholders(path, "xl/")


def _extract_fields_from_pdf(path: Path):
    try:
        PdfReader, _, _, _ = _import_pypdf()
    except ImportError as error:
        raise ValueError("O leitor de PDF não está disponível.") from error

    reader = PdfReader(str(path))
    fields = reader.get_fields() or {}
    keys = list(fields.keys())
    return _build_schema_from_keys(keys)


def _generate_filled_pdf(file_path: str, payload: dict):
    try:
        PdfReader, PdfWriter, NameObject, BooleanObject = _import_pypdf()
    except ImportError as error:
        raise ValueError("O leitor de PDF não está disponível.") from error

    reader = PdfReader(file_path)
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)

    for page in writer.pages:
        writer.update_page_form_field_values(
            page, {key: "" if value is None else str(value) for key, value in payload.items()}
        )

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


def _generate_zip_based_file(file_path: str, xml_prefix: str, payload: dict):
    output_io = io.BytesIO()
    with (
        zipfile.ZipFile(file_path) as source_zip,
        zipfile.ZipFile(output_io, mode="w") as target_zip,
    ):
        validate_archive(source_zip)
        for info in source_zip.infolist():
            data = source_zip.read(info.filename)
            if info.filename.startswith(xml_prefix) and info.filename.endswith(".xml"):
                data = _transform_xml(data.decode("utf-8"), xml_prefix, payload=payload).encode(
                    "utf-8"
                )
            target_zip.writestr(info, data)
    return output_io.getvalue()


def generate_filled_document(file_path: str, file_type: str, payload: dict):
    if file_type == "docx":
        return _generate_zip_based_file(file_path, "word/", payload)
    if file_type == "xlsx":
        return _generate_zip_based_file(file_path, "xl/", payload)
    if file_type == "pdf":
        return _generate_filled_pdf(file_path, payload)
    raise ValueError("Tipo de documento não suportado.")
