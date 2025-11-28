from typing import Any, Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from urllib.parse import urlparse, urljoin


def search_company_website(
    company_name: str,
    sector: Optional[str] = None,
    country: Optional[str] = None,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """
    Wrap around DDGS (DuckDuckGo Search) to get candidate websites.
    """
    query_parts = [company_name]
    if sector:
        query_parts.append(sector)
    if country:
        query_parts.append(country)
    query = " ".join(query_parts)

    results: List[Dict[str, Any]] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            # r suele tener 'title', 'href', 'body', etc.
            url = r.get("href") or r.get("url")
            if not url:
                continue
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": url,
                    "snippet": r.get("body", ""),
                }
            )

    return results


def fetch_url(url: str, timeout: int = 10) -> str:
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.text


def extract_website_context(url: str, max_chars: int = 8000) -> str:
    """
    Fetches the page and extracts readable text content.
    You can adapt esto a lo que ya hacías en app.py.
    """
    html_content = fetch_url(url)
    soup = BeautifulSoup(html_content, "lxml")

    # Ejemplo muy simple: juntar todos los textos
    texts = soup.stripped_strings
    joined = " ".join(texts)

    if len(joined) > max_chars:
        joined = joined[:max_chars]

    return joined
