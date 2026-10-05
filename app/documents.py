"""Read bounded project documents as text, without storing or executing them."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree

from pypdf import PdfReader

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TEXT_CHARS = 5000


class DocumentError(ValueError):
    pass


def extract_document(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt"}:
        raise DocumentError("Choose a PDF, Word (.docx), or UTF-8 text (.txt) file.")
    if not data:
        raise DocumentError("The file is empty. Choose a document containing your project description.")
    if len(data) > MAX_FILE_BYTES:
        raise DocumentError("The file is too large. Choose a document smaller than 5 MB.")
    try:
        if suffix == ".txt":
            text = data.decode("utf-8-sig")
            if "\x00" in text:
                raise DocumentError("This file is not readable plain text. Save it as UTF-8 text and try again.")
        elif suffix == ".docx":
            with ZipFile(BytesIO(data)) as archive:
                if sum(item.file_size for item in archive.infolist()) > 20 * 1024 * 1024:
                    raise DocumentError("The Word document expands beyond the supported size. Upload a shorter project brief.")
                xml = archive.read("word/document.xml")
                if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                    raise DocumentError("This Word file contains unsupported XML declarations. Save a clean .docx copy.")
                root = ElementTree.fromstring(xml)
                ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                text = "\n".join("".join(node.text or "" for node in paragraph.iter(ns + "t"))
                                 for paragraph in root.iter(ns + "p"))
        else:
            if not data.startswith(b"%PDF-"):
                raise DocumentError("This file does not contain a valid PDF. Export it again and retry.")
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                raise DocumentError("Password-protected PDFs are not supported. Upload an unlocked copy.")
            if len(reader.pages) > 30:
                raise DocumentError("Upload a project brief of 30 pages or fewer.")
            pages = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if not page_text.strip():
                    raise DocumentError("A PDF page has no readable text. Scans and images need OCR first; upload a text-based PDF, Word or text file.")
                pages.append(page_text)
                if sum(map(len, pages)) > MAX_TEXT_CHARS:
                    raise DocumentError("The document contains more than 5,000 characters. Upload a shorter brief or paste the relevant project description.")
            text = "\n".join(pages)
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError("Could not read this document. It may be damaged or use an unsupported format. Try exporting it as .docx, a text-based PDF, or UTF-8 .txt.") from exc
    text = text.strip()
    if not 10 <= len(text) <= MAX_TEXT_CHARS:
        raise DocumentError("The document must contain 10 to 5,000 characters of readable project text. Upload a shorter brief or paste the relevant description.")
    return text
