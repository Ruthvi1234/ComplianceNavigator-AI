from __future__ import annotations

from io import BytesIO

import requests
import pymupdf


def extract_pdf_text(pdf_url: str) -> tuple[str, int]:
    """
    Download a PDF and extract its text.

    Returns:
        tuple[str, int]: (extracted_text, page_count)

    Raises:
        requests.RequestException: if the PDF cannot be downloaded.
        pymupdf.MuPDFError: if the downloaded content is not a valid PDF.
    """

    response = requests.get(
        pdf_url,
        timeout=60,
        headers={
            "User-Agent": (
                "ComplianceNavigator/1.0 "
                "(waste-regulation document indexing)"
            )
        },
    )

    response.raise_for_status()

    pdf_bytes = response.content

    document = pymupdf.open(
        stream=BytesIO(pdf_bytes),
        filetype="pdf",
    )

    try:
        text_parts: list[str] = []

        for page in document:
            page_text = page.get_text()

            if page_text:
                text_parts.append(page_text)

        text = "\n".join(text_parts)

        return text, len(document)

    finally:
        document.close()