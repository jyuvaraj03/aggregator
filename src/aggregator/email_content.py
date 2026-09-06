"""Consistent text selection for mining, extraction, and presentation."""

from bs4 import BeautifulSoup


def readable_body(body_html: str | None, body_text: str | None) -> str:
    soup = BeautifulSoup(body_html or "", "html.parser")
    normalized_html = " ".join(soup.get_text("\n", strip=True).split())
    return normalized_html or body_text or ""
