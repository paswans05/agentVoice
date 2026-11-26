"""Modular document parsing and sanitization for Knowledge Base uploads."""

from __future__ import annotations

from dataclasses import dataclass
import csv
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".html", ".htm", ".json"}


class DocumentParseError(ValueError):
    """Raised when a document is unsupported, empty, oversized, or corrupted."""


@dataclass(slots=True)
class ParsedSection:
    """Extracted text segment with optional page number and section heading."""

    text: str
    page_number: int | None = None
    section_title: str | None = None


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in ("script", "style", "noscript"):
            self._skip = False
        elif tag.lower() in ("p", "div", "li", "br", "h1", "h2", "h3", "h4", "tr"):
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped + " ")

    def get_text(self) -> str:
        raw = "".join(self._parts)
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


class DocumentParserService:
    """Extracts clean text sections from supported local document formats."""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Strip path components and unsafe characters from uploaded filenames."""
        base = Path(filename).name
        cleaned = re.sub(r"[^A-Za-z0-9._\- ]+", "_", base).strip()
        if not cleaned or cleaned in (".", ".."):
            raise DocumentParseError("Invalid filename.")
        return cleaned

    @staticmethod
    def validate_file(filename: str, content: bytes, max_size_mb: int = 10) -> tuple[str, str]:
        """Validate extension and size. Returns (sanitized_filename, extension)."""
        safe_name = DocumentParserService.sanitize_filename(filename)
        ext = Path(safe_name).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise DocumentParseError(
                f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )
        if not content:
            raise DocumentParseError(f"File '{safe_name}' is empty.")
        max_bytes = max_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise DocumentParseError(
                f"File '{safe_name}' exceeds maximum size limit of {max_size_mb} MB."
            )
        return safe_name, ext

    @classmethod
    def parse(cls, filename: str, content: bytes, max_size_mb: int = 10) -> list[ParsedSection]:
        """Extract clean text sections from supported document formats."""
        safe_name, ext = cls.validate_file(filename, content, max_size_mb=max_size_mb)

        if ext in (".txt", ".md"):
            sections = cls._parse_text_or_markdown(content, is_markdown=(ext == ".md"))
        elif ext == ".csv":
            sections = cls._parse_csv(content)
        elif ext == ".json":
            sections = cls._parse_json(content)
        elif ext in (".html", ".htm"):
            sections = cls._parse_html(content)
        elif ext == ".docx":
            sections = cls._parse_docx(content)
        elif ext == ".pdf":
            sections = cls._parse_pdf(content)
        else:  # pragma: no cover
            raise DocumentParseError(f"Unsupported extension: {ext}")

        non_empty = [s for s in sections if s.text.strip()]
        if not non_empty:
            raise DocumentParseError(f"No readable text could be extracted from '{safe_name}'.")
        return non_empty

    @staticmethod
    def _decode_utf8(content: bytes) -> str:
        try:
            return content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="replace")

    @classmethod
    def _parse_text_or_markdown(cls, content: bytes, *, is_markdown: bool) -> list[ParsedSection]:
        text = cls._decode_utf8(content).strip()
        if not text:
            return []
        if not is_markdown:
            return [ParsedSection(text=text)]

        sections: list[ParsedSection] = []
        current_title: str | None = None
        current_lines: list[str] = []
        for line in text.splitlines():
            heading_match = re.match(r"^#{1,6}\s+(.+)$", line.strip())
            if heading_match:
                if current_lines:
                    sections.append(
                        ParsedSection(
                            text="\n".join(current_lines).strip(),
                            section_title=current_title,
                        )
                    )
                    current_lines = []
                current_title = heading_match.group(1).strip()
            else:
                current_lines.append(line)
        if current_lines:
            sections.append(
                ParsedSection(text="\n".join(current_lines).strip(), section_title=current_title)
            )
        return sections or [ParsedSection(text=text)]

    @classmethod
    def _parse_csv(cls, content: bytes) -> list[ParsedSection]:
        text = cls._decode_utf8(content)
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return []
        headers = rows[0]
        lines: list[str] = []
        for row in rows[1:]:
            if not any(cell.strip() for cell in row):
                continue
            pairs = [
                f"{headers[i].strip() if i < len(headers) else f'col_{i}'}: {val.strip()}"
                for i, val in enumerate(row)
                if val.strip()
            ]
            if pairs:
                lines.append(" | ".join(pairs))
        if not lines:
            lines = [" | ".join(headers)]
        return [ParsedSection(text="\n".join(lines), section_title="CSV Table")]

    @classmethod
    def _parse_json(cls, content: bytes) -> list[ParsedSection]:
        text = cls._decode_utf8(content)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DocumentParseError(f"Corrupted JSON document: {exc}") from exc
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
        return [ParsedSection(text=pretty, section_title="JSON Data")]

    @classmethod
    def _parse_html(cls, content: bytes) -> list[ParsedSection]:
        parser = _TextHTMLParser()
        parser.feed(cls._decode_utf8(content))
        parser.close()
        extracted = parser.get_text()
        return [ParsedSection(text=extracted)] if extracted else []

    @staticmethod
    def _parse_docx(content: bytes) -> list[ParsedSection]:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                if "word/document.xml" not in zf.namelist():
                    raise DocumentParseError("Corrupted DOCX: missing word/document.xml.")
                xml_bytes = zf.read("word/document.xml")
        except zipfile.BadZipFile as exc:
            raise DocumentParseError(f"Corrupted DOCX file: {exc}") from exc

        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as exc:
            raise DocumentParseError(f"Corrupted DOCX XML: {exc}") from exc

        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: list[str] = []
        for p in root.findall(".//w:p", ns):
            texts = [t.text for t in p.findall(".//w:t", ns) if t.text]
            joined = "".join(texts).strip()
            if joined:
                paragraphs.append(joined)
        return [ParsedSection(text="\n\n".join(paragraphs))] if paragraphs else []

    @staticmethod
    def _parse_pdf(content: bytes) -> list[ParsedSection]:
        if not content.lstrip().startswith(b"%PDF"):
            raise DocumentParseError("Corrupted or invalid PDF header.")
        try:
            from pypdf import PdfReader  # type: ignore[import-not-found]
        except ImportError as exc:
            raise DocumentParseError(
                "PDF extraction requires `pypdf`. Install RAG extras: `uv sync --extra rag`."
            ) from exc

        try:
            reader = PdfReader(io.BytesIO(content))
        except Exception as exc:
            raise DocumentParseError(f"Corrupted PDF document: {exc}") from exc

        sections: list[ParsedSection] = []
        for idx, page in enumerate(reader.pages, start=1):
            txt = (page.extract_text() or "").strip()
            if txt:
                sections.append(ParsedSection(text=txt, page_number=idx))

        if not sections:
            raise DocumentParseError(
                "No extractable text found in PDF. It may be a scanned image PDF (OCR is not enabled)."
            )
        return sections
