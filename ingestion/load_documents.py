from pathlib import Path
from urllib.parse import urlparse

import docx2txt
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
CATEGORY_LABELS = {
    "history": "History",
    "geography": "Geography",
    "government_laws": "Government & Laws",
    "economy": "Economy",
    "education": "Education",
    "culture": "Culture",
    "tourism": "Tourism",
    "public_services": "Public Services",
}


def get_category(file_path: str) -> str:
    folder = Path(file_path).resolve().parent.name.lower()
    return CATEGORY_LABELS.get(
        folder, folder.replace("_", " ").replace("-", " ").title() or "Uncategorized"
    )


def load_file(file_path: str) -> list[dict]:
    """Extract local PDF, DOCX or TXT content while preserving source metadata."""
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {extension}")

    common = {
        "source": str(path),
        "title": path.name,
        "source_type": "file",
        "category": get_category(str(path)),
    }
    documents = []

    if extension == ".pdf":
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise ValueError(f"Encrypted PDFs are not supported: {path.name}")
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                documents.append({**common, "text": text, "page": page_number})

    elif extension == ".docx":
        text = (docx2txt.process(str(path)) or "").strip()
        if text:
            documents.append({**common, "text": text})

    else:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp1252")
        text = text.strip()
        if text:
            documents.append({**common, "text": text})

    if not documents:
        raise ValueError(
            f"No extractable text found in {path.name}. Scanned PDFs may require OCR."
        )
    return documents


def load_url(url: str) -> dict:
    """Extract readable text and metadata from an HTML webpage."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Provide a valid HTTP or HTTPS webpage URL.")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing embedded credentials are not allowed.")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("Local URLs are not supported.")

    try:
        response = requests.get(
            url, timeout=20, headers={"User-Agent": "PakKnowledgeAI/1.0"}
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not retrieve webpage: {exc}") from exc

    content_type = response.headers.get("Content-Type", "").lower()
    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
        raise ValueError(f"Expected HTML, received: {content_type or 'unknown type'}")

    soup = BeautifulSoup(response.content, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        element.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else response.url
    main = soup.find("main") or soup.find("article") or soup.body
    if main is None:
        raise ValueError("No readable webpage content was found.")
    text = main.get_text(separator="\\n", strip=True)
    if not text:
        raise ValueError("The webpage contains no extractable text.")

    return {
        "text": text,
        "source": response.url,
        "title": title,
        "source_type": "webpage",
        "category": "Uncategorized",
    }


def chunk_documents(
    documents: list[dict], chunk_size: int = 1000, overlap: int = 150
) -> list[dict]:
    """Split text into overlapping chunks and retain citation metadata."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size.")

    chunks = []
    step = chunk_size - overlap
    for document in documents:
        text = (document.get("text") or "").strip()
        start = 0
        while start < len(text):
            part = text[start:start + chunk_size].strip()
            if part:
                chunks.append({**document, "text": part, "chunk_index": len(chunks)})
            if start + chunk_size >= len(text):
                break
            start += step
    return chunks
