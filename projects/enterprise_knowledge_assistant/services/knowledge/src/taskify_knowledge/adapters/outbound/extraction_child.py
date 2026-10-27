"""Isolated local parser entry point; bounded CPU/memory, no credentials and no network fetches."""

import io
import json
import resource
import subprocess
import sys
import unicodedata
import zipfile
from importlib.metadata import version
from pathlib import Path
from typing import Any

MAX_PIXELS = 40_000_000
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_MEMORY_BYTES = 512 * 1024 * 1024


class ParseFailure(Exception):
    """Carry only a safe processing code; parser details and private file contents never escape."""

    def __init__(self, code: str) -> None:
        """Retain one application-owned error identifier, never a parser exception payload."""
        self.code = code
        super().__init__(code)


def normalize(raw: str, *, bom: bool = False) -> tuple[str, list[int]]:
    """Normalize NFC/newlines while mapping every output code point back to original clusters."""
    import regex

    if "\x00" in raw:
        raise ParseFailure("unreadable_file")
    output: list[str] = []
    offsets: list[int] = []
    for cluster in regex.finditer(r"\X", raw):
        if bom and cluster.start() == 0 and cluster.group() == "\ufeff":
            continue
        text = unicodedata.normalize(
            "NFC", cluster.group().replace("\r\n", "\n").replace("\r", "\n")
        )
        output.append(text)
        offsets.extend([cluster.start()] * len(text))
    normalized = "".join(output)
    offsets.append(len(raw))
    return normalized, offsets


def block(
    raw: str, locator: dict[str, object], extractor: str, *, bom: bool = False
) -> dict[str, Any] | None:
    """Retain readable source text and complete offsets, skipping only empty extraction blocks."""
    normalized, offsets = normalize(raw, bom=bom)
    if not any(char.isprintable() and not char.isspace() for char in normalized):
        return None
    return {
        "normalized_text": normalized,
        "locator": locator,
        "source_offset_map": offsets,
        "extractor_version": extractor,
    }


def ocr(image: Any, languages: str) -> str:
    """Recognize printed text with Tesseract; never execute shell/file/network instructions from input."""
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    result = subprocess.run(
        ["tesseract", "stdin", "stdout", "-l", languages, "--psm", "3"],
        input=stream.getvalue(),
        capture_output=True,
        timeout=80,
        check=False,
    )
    if result.returncode != 0:
        raise ParseFailure("unreadable_file")
    return result.stdout.decode("utf-8")


def parse_text(path: Path, inspect_only: bool) -> list[dict[str, Any]]:
    """Decode strict UTF-8/BOM text and retain inclusive normalized line locations."""
    try:
        raw = path.read_bytes().decode("utf-8")
    except UnicodeError:
        raise ParseFailure("invalid_encoding") from None
    if inspect_only:
        if "\x00" in raw:
            raise ParseFailure("unreadable_file")
        return []
    value = block(
        raw,
        {
            "kind": "text",
            "line_start": 1,
            "line_end": max(1, raw.replace("\r\n", "\n").replace("\r", "\n").count("\n") + 1),
        },
        "utf8-nfc-v1",
        bom=True,
    )
    return [value] if value else []


def parse_image(
    path: Path, media_type: str, languages: str, inspect_only: bool
) -> list[dict[str, Any]]:
    """Validate matching PNG/JPEG and decoded pixels before any raster allocation or OCR."""
    from PIL import Image

    with Image.open(path) as image:
        if image.width * image.height > MAX_PIXELS:
            raise ParseFailure("resource_limit")
        if image.format != ("PNG" if media_type == "image/png" else "JPEG"):
            raise ParseFailure("corrupt_file")
        image.verify()
    if inspect_only:
        return []
    with Image.open(path) as image:
        value = block(
            ocr(image.convert("RGB"), languages), {"kind": "image", "page": 1}, "tesseract-image-v1"
        )
    return [value] if value else []


def parse_pdf(path: Path, languages: str, inspect_only: bool) -> list[dict[str, Any]]:
    """Extract native text by page and OCR only empty pages under the same child resource limits."""
    from pypdf import PdfReader

    reader = PdfReader(path, strict=True)
    if reader.is_encrypted:
        raise ParseFailure("protected_file")
    if not len(reader.pages):
        raise ParseFailure("unreadable_file")
    if inspect_only:
        return []
    blocks: list[dict[str, Any]] = []
    rendered = None
    try:
        for index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            extractor = "pypdf-" + version("pypdf")
            if not text.strip():
                import pypdfium2

                if rendered is None:
                    rendered = pypdfium2.PdfDocument(path)
                raster_page = rendered[index]
                try:
                    width, height = raster_page.get_size()
                    if width * height * 4 > MAX_PIXELS:
                        raise ParseFailure("resource_limit")
                    bitmap = raster_page.render(scale=2)
                    try:
                        text = ocr(bitmap.to_pil(), languages)
                    finally:
                        bitmap.close()
                finally:
                    raster_page.close()
                extractor = "pdfium-tesseract-v1"
            value = block(
                text,
                {
                    "kind": "pdf",
                    "page": index + 1,
                    "text_start": 0,
                    "text_end": len(unicodedata.normalize("NFC", text)),
                },
                extractor,
            )
            if value:
                blocks.append(value)
    finally:
        if rendered is not None:
            rendered.close()
    return blocks


def parse_docx(path: Path, inspect_only: bool) -> list[dict[str, Any]]:
    """Preserve paragraph/table order, heading paths and cell locations, including nested tables."""
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    with zipfile.ZipFile(path) as archive:
        if sum(part.file_size for part in archive.infolist()) > MAX_ARCHIVE_BYTES:
            raise ParseFailure("resource_limit")
        if (
            "word/document.xml" not in archive.namelist()
            or "[Content_Types].xml" not in archive.namelist()
        ):
            raise ParseFailure("corrupt_file")
    document = Document(str(path))
    if inspect_only:
        return []
    headings: list[str] = []
    blocks: list[dict[str, Any]] = []
    table_number = 0

    def append(raw: str, locator: dict[str, object]) -> None:
        """Append one paragraph/cell block without combining unrelated sections or changing originals."""
        value = block(raw, locator, "python-docx-" + version("python-docx"))
        if value:
            blocks.append(value)

    def table_rows(table: Any, ordinal: int) -> None:
        """Walk nested tables in document order while retaining their actual row/cell positions."""
        nonlocal table_number
        current = table_number
        table_number += 1
        for row_number, row in enumerate(table.rows):
            for cell_number, cell in enumerate(row.cells):
                for content in cell.iter_inner_content():
                    if isinstance(content, Table):
                        table_rows(content, ordinal)
                    elif isinstance(content, Paragraph):
                        append(
                            content.text,
                            {
                                "kind": "docx",
                                "heading_path": list(headings),
                                "block": ordinal,
                                "table": current,
                                "row": row_number,
                                "cell": cell_number,
                            },
                        )

    for ordinal, content in enumerate(document.iter_inner_content()):
        if isinstance(content, Table):
            table_rows(content, ordinal)
        elif isinstance(content, Paragraph):
            name = content.style.name if content.style is not None else ""
            if name.startswith("Heading ") and name[8:].isdigit():
                headings = headings[: int(name[8:]) - 1] + [content.text]
            append(content.text, {"kind": "docx", "heading_path": list(headings), "block": ordinal})
    return blocks


def main() -> None:
    """Read a private structured request and emit only structured blocks or a safe error code."""
    try:
        # Resource-isolated parsing is a Linux deployment capability; never silently relax its cap.
        if sys.platform != "linux":
            raise ParseFailure("processing_unavailable")
        resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
        resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
        resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024 * 1024, 32 * 1024 * 1024))
        request = json.load(sys.stdin)
        path = Path(request["path"])
        media = request["media_type"]
        inspect_only = request["inspect_only"]
        languages = request["languages"]
        if media == "text/plain":
            blocks = parse_text(path, inspect_only)
        elif media == "application/pdf":
            blocks = parse_pdf(path, languages, inspect_only)
        elif media in ("image/png", "image/jpeg"):
            blocks = parse_image(path, media, languages, inspect_only)
        elif media == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            blocks = parse_docx(path, inspect_only)
        else:
            raise ParseFailure("corrupt_file")
        if not inspect_only and not blocks:
            raise ParseFailure("unreadable_file")
        for ordinal, value in enumerate(blocks):
            value["ordinal"] = ordinal
        result: dict[str, Any] = {"blocks": blocks}
    except ParseFailure as error:
        result = {"error": error.code}
    except (MemoryError, subprocess.TimeoutExpired):
        result = {"error": "resource_limit"}
    except FileNotFoundError:
        result = {"error": "storage_unavailable"}
    except Exception:
        result = {"error": "corrupt_file"}
    json.dump(result, sys.stdout, ensure_ascii=True)


if __name__ == "__main__":
    main()
