import os


def parse_file(file_path: str, file_type: str) -> str:
    """Parse various file types into plain text."""
    if file_type == "pdf":
        return parse_pdf(file_path)
    elif file_type == "docx":
        return parse_docx(file_path)
    elif file_type == "txt":
        return parse_txt(file_path)
    elif file_type == "csv":
        return parse_csv(file_path)
    elif file_type == "url":
        return parse_url(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def parse_pdf(path: str) -> str:
    """Extract text from PDF using PyPDF2."""
    from PyPDF2 import PdfReader

    reader = PdfReader(path)
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n\n".join(text_parts)


def parse_docx(path: str) -> str:
    """Extract text from DOCX."""
    from docx import Document

    doc = Document(path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_txt(path: str) -> str:
    """Read plain text file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_csv(path: str) -> str:
    """Convert CSV rows to readable text."""
    import csv

    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if headers:
            for row in reader:
                row_text = ", ".join(f"{h}: {v}" for h, v in zip(headers, row) if v.strip())
                if row_text:
                    rows.append(row_text)
    return "\n".join(rows)


def parse_url(url: str) -> str:
    """Scrape and extract text from a webpage."""
    import httpx
    from bs4 import BeautifulSoup

    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove scripts, styles, nav, footer
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Clean up excessive whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
