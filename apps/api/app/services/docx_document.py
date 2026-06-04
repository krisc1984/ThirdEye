from __future__ import annotations

from html import escape
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException


DOCX_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
MAX_DOCX_TEXT_CHARS = 512 * 1024

ElementTree.register_namespace("w", W_NS)
ElementTree.register_namespace("xml", XML_NS)


def extract_docx_text(path: Path) -> tuple[str, bool]:
    try:
        with ZipFile(path) as archive:
            raw_document = archive.read("word/document.xml")
    except KeyError as error:
        raise HTTPException(status_code=400, detail="docx document body not found") from error
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"invalid docx file: {error}") from error

    try:
        root = ElementTree.fromstring(raw_document)
    except ElementTree.ParseError as error:
        raise HTTPException(status_code=400, detail="invalid docx document xml") from error

    paragraphs: list[str] = []
    for paragraph in root.iter(f"{DOCX_NAMESPACE}p"):
        text_parts: list[str] = []
        for node in paragraph.iter():
            if node.tag == f"{DOCX_NAMESPACE}t" and node.text:
                text_parts.append(node.text)
            elif node.tag == f"{DOCX_NAMESPACE}tab":
                text_parts.append("\t")
            elif node.tag == f"{DOCX_NAMESPACE}br":
                text_parts.append("\n")
        paragraphs.append("".join(text_parts))

    content = "\n".join(paragraphs).strip()
    truncated = len(content) > MAX_DOCX_TEXT_CHARS
    return content[:MAX_DOCX_TEXT_CHARS], truncated


def write_docx(path: Path, content: str) -> None:
    path.write_bytes(render_docx_bytes(content))


def write_docx_preserving_package(source_path: Path, target_path: Path, content: str) -> None:
    temporary_path: Path | None = None
    output_path = target_path
    if source_path.resolve() == target_path.resolve():
        temporary_path = target_path.with_name(f".{target_path.name}.tmp")
        output_path = temporary_path

    try:
        with ZipFile(source_path) as source_archive:
            try:
                raw_document = source_archive.read("word/document.xml")
                document_info = source_archive.getinfo("word/document.xml")
            except KeyError as error:
                raise HTTPException(status_code=400, detail="docx document body not found") from error

            patched_document = _replace_document_text(raw_document, content)

            with ZipFile(output_path, "w") as target_archive:
                wrote_document = False
                for item in source_archive.infolist():
                    if item.filename == "word/document.xml":
                        target_archive.writestr(document_info, patched_document)
                        wrote_document = True
                    else:
                        target_archive.writestr(item, source_archive.read(item.filename))
                if not wrote_document:
                    target_archive.writestr("word/document.xml", patched_document)
        if temporary_path is not None:
            temporary_path.replace(target_path)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"invalid docx file: {error}") from error
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def render_docx_bytes(content: str) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_relationships_xml())
        archive.writestr("word/_rels/document.xml.rels", _document_relationships_xml())
        archive.writestr("word/document.xml", _document_xml(content))
        archive.writestr("word/styles.xml", _styles_xml())
    return buffer.getvalue()


def _replace_document_text(raw_document: bytes, content: str) -> bytes:
    try:
        root = ElementTree.fromstring(raw_document)
    except ElementTree.ParseError as error:
        raise HTTPException(status_code=400, detail="invalid docx document xml") from error

    paragraphs = list(root.iter(f"{DOCX_NAMESPACE}p"))
    next_lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for index, paragraph in enumerate(paragraphs):
        _replace_paragraph_text(paragraph, next_lines[index] if index < len(next_lines) else "")

    if len(next_lines) > len(paragraphs):
        _append_document_paragraphs(root, next_lines[len(paragraphs) :])

    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def _replace_paragraph_text(paragraph: ElementTree.Element, text: str) -> None:
    text_nodes = [node for node in paragraph.iter(f"{DOCX_NAMESPACE}t")]
    if not text_nodes:
        if text:
            run = ElementTree.SubElement(paragraph, f"{DOCX_NAMESPACE}r")
            text_node = ElementTree.SubElement(run, f"{DOCX_NAMESPACE}t")
            text_node.set(f"{{{XML_NS}}}space", "preserve")
            text_node.text = text
        return

    for index, text_node in enumerate(text_nodes):
        text_node.set(f"{{{XML_NS}}}space", "preserve")
        text_node.text = text if index == 0 else ""


def _append_document_paragraphs(root: ElementTree.Element, lines: list[str]) -> None:
    body = root.find(f"{DOCX_NAMESPACE}body")
    if body is None:
        return

    section_properties = body.find(f"{DOCX_NAMESPACE}sectPr")
    insert_index = list(body).index(section_properties) if section_properties is not None else len(list(body))
    for line in lines:
        paragraph = ElementTree.Element(f"{DOCX_NAMESPACE}p")
        if line:
            run = ElementTree.SubElement(paragraph, f"{DOCX_NAMESPACE}r")
            text_node = ElementTree.SubElement(run, f"{DOCX_NAMESPACE}t")
            text_node.set(f"{{{XML_NS}}}space", "preserve")
            text_node.text = line
        body.insert(insert_index, paragraph)
        insert_index += 1


def _document_xml(content: str) -> str:
    paragraphs = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    paragraph_xml = "\n".join(_paragraph_xml(paragraph) for paragraph in paragraphs) or _paragraph_xml("")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {paragraph_xml}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>"""


def _paragraph_xml(text: str) -> str:
    if not text:
        return "<w:p/>"
    lines = text.split("\n")
    runs = []
    for index, line in enumerate(lines):
        if index:
            runs.append("<w:r><w:br/></w:r>")
        runs.append(f'<w:r><w:t xml:space="preserve">{escape(line)}</w:t></w:r>')
    return f"<w:p>{''.join(runs)}</w:p>"


def _content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""


def _root_relationships_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""


def _document_relationships_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>"""


def _styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
  </w:style>
</w:styles>"""
