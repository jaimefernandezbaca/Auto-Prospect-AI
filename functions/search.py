# functions/search.py

import re
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from urllib.parse import urlparse, parse_qs

from .utils import looks_like_url, normalize_url


def google_search_company_websites(
    company: str,
    sector_terms: str,
    max_results: int = 5
) -> list:
    query = f"{company} {sector_terms} official website".strip()
    tokens = [
        t.lower()
        for t in re.findall(r"[A-Za-záéíóúñüÁÉÍÓÚÑÜ]+", company)
        if len(t) > 2
    ]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }

    params = {"q": query, "num": 10, "hl": "es"}

    bad_domains = [
        "linkedin.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "glassdoor.com",
        "indeed.com",
        "linkedin.",
        "zhihu.com",
        "quora.com",
        "reddit.com",
        "stackexchange.com",
        "stackoverflow.com",
    ]

    results: List[Dict] = []

    try:
        resp = requests.get(
            "https://www.google.com/search",
            params=params,
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.select("a"):
            href = a.get("href", "")
            if not href.startswith("/url?q="):
                continue

            parsed = urlparse(href)
            q = parse_qs(parsed.query).get("q", [""])[0]
            target_url = q.strip()
            if not target_url:
                continue

            parsed_target = urlparse(target_url)
            domain = parsed_target.netloc.lower()
            url_lower = target_url.lower()
            title_text = a.get_text(" ", strip=True).lower()

            if any(bad in domain for bad in bad_domains):
                continue

            if tokens:
                if not any(t in domain or t in title_text or t in url_lower for t in tokens):
                    continue

            title_clean = a.get_text(" ", strip=True) or parsed_target.netloc
            snippet = ""

            results.append(
                {
                    "url": target_url,
                    "title": title_clean,
                    "snippet": snippet,
                    "source": "google",
                }
            )

            if len(results) >= max_results:
                break

    except Exception:
        return []

    return results


def ddg_search_company_websites(
    company: str,
    sector_terms: str,
    max_results: int = 5
) -> list:
    from streamlit import error as st_error  # para mantener el st.error

    query = f"{company} {sector_terms} official website".strip()
    tokens = [
        t.lower()
        for t in re.findall(r"[A-Za-záéíóúñüÁÉÍÓÚÑÜ]+", company)
        if len(t) > 2
    ]

    bad_domains = [
        "linkedin.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "glassdoor.com",
        "indeed.com",
        "linkedin.",
        "zhihu.com",
        "quora.com",
        "reddit.com",
        "stackexchange.com",
        "stackoverflow.com",
    ]

    results = []

    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=20):
                url = r.get("href") or r.get("link")
                title = (r.get("title") or "").strip()
                snippet = (r.get("body") or "").strip()

                if not url:
                    continue

                parsed_target = urlparse(url)
                domain = parsed_target.netloc.lower()
                url_lower = url.lower()
                title_lower = title.lower()

                if any(bad in domain for bad in bad_domains):
                    continue

                if tokens:
                    if not any(t in domain or t in title_lower or t in url_lower for t in tokens):
                        continue

                results.append(
                    {
                        "url": url,
                        "title": title or domain,
                        "snippet": snippet,
                        "source": "duckduckgo",
                    }
                )
                if len(results) >= max_results:
                    break
    except Exception as e:
        st_error(f"Error searching website (DuckDuckGo): {e}")
        return []

    return results


def search_company_websites(
    company: str,
    sector_terms: str,
    max_results: int = 5
) -> list:
    company = company.strip()

    if looks_like_url(company):
        return [
            {
                "url": normalize_url(company),
                "title": company,
                "snippet": "",
                "source": "direct",
            }
        ]

    candidates = google_search_company_websites(company, sector_terms, max_results)
    if len(candidates) < max_results:
        extra = ddg_search_company_websites(company, sector_terms, max_results - len(candidates))
        candidates.extend(extra)

    seen = set()
    unique = []
    for c in candidates:
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        unique.append(c)

    return unique[:max_results]
