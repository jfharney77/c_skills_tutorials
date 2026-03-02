"""
document_loader.py — Load and extract plain text from URLs, PDFs, and DOCX files.
"""

import io
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document


def load_document(source, source_type: str) -> str:
    """
    Load a document and return its plain text content.

    Args:
        source: URL string, file-like object (PDF/DOCX), or bytes
        source_type: "url" | "pdf" | "docx"

    Returns:
        Plain text string extracted from the document.
    """
    if source_type == "url":
        return _load_url(source)
    elif source_type == "pdf":
        return _extract_pdf(source)
    elif source_type == "docx":
        return _extract_docx(source)
    else:
        raise ValueError(f"Unsupported source_type: {source_type!r}")


def _load_url(url: str) -> str:
    response = requests.get(url, timeout=30, headers={"User-Agent": "ResearchAnalyzer/1.0"})
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        return _extract_pdf(io.BytesIO(response.content))
    elif "officedocument.wordprocessingml" in content_type or url.lower().endswith(".docx"):
        return _extract_docx(io.BytesIO(response.content))
    else:
        soup = BeautifulSoup(response.text, "html.parser")
        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)


def _extract_pdf(file_obj) -> str:
    reader = PdfReader(file_obj)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def _extract_docx(file_obj) -> str:
    doc = Document(file_obj)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)
