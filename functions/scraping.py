# functions/scraping.py

import re
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

import streamlit as st


EMAIL_REGEX = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
OBFUSCATED_AT_PATTERNS = [
    r"\[at\]",
    r"\(at\)",
    r"\sat\s",
]
OBFUSCATED_DOT_PATTERNS = [
    r"\[dot\]",
    r"\(dot\)",
    r"\sdot\s",
]

INTERNAL_LINK_KEYWORDS = [
    "contact", "contacto", "contacts", "support", "soporte", "sales", "team",
    "about", "nosotros", "quienes", "services", "servicios", "solutions",
    "equipo", "company", "empresa", "clients", "clientes", "partners",
    "cases", "case", "portfolio", "careers", "jobs", "locations", "sucursales",
]


def extract_emails_from_text(text: str) -> set[str]:
    emails = set(re.findall(EMAIL_REGEX, text, flags=re.IGNORECASE))

    for mailto_match in re.findall(r"mailto:([^\"'>\s]+)", text, flags=re.IGNORECASE):
        clean = mailto_match.split("?")[0].strip()
        if re.match(EMAIL_REGEX, clean, flags=re.IGNORECASE):
            emails.add(clean)

    obfuscated_matches = re.findall(
        r"[A-Za-z0-9._%+-]+\s?(?:\(|\[)?at(?:\)|\])?\s?[A-Za-z0-9.-]+(?:\s?(?:\(|\[)?dot(?:\)|\])?\s?[A-Za-z]{2,})+",
        text,
        flags=re.IGNORECASE,
    )
    for candidate in obfuscated_matches:
        normalized = candidate
        for pattern in OBFUSCATED_AT_PATTERNS:
            normalized = re.sub(pattern, "@", normalized, flags=re.IGNORECASE)
        for pattern in OBFUSCATED_DOT_PATTERNS:
            normalized = re.sub(pattern, ".", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s+", "", normalized)
        if re.match(EMAIL_REGEX, normalized, flags=re.IGNORECASE):
            emails.add(normalized)

    return {email.lower() for email in emails}


def discover_internal_links(base_url: str, base_domain: str, soup: BeautifulSoup, max_links: int = 8) -> List[str]:
    discovered: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.lower().startswith("mailto:"):
            continue

        anchor_text = a.get_text(" ", strip=True).lower()
        href_lower = href.lower()

        if not any(keyword in anchor_text or keyword in href_lower for keyword in INTERNAL_LINK_KEYWORDS):
            continue

        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        if not parsed.scheme or not parsed.netloc:
            continue
        if parsed.netloc != base_domain:
            continue
        if full_url not in discovered:
            discovered.append(full_url)
        if len(discovered) >= max_links:
            break
    return discovered


def fetch_website_info(url: str) -> dict:
    if not url:
        return {}

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    candidate_paths = set()
    initial_path = parsed.path or "/"
    candidate_paths.add(initial_path)

    common_paths = [
        "",
        "/",
        "/contact",
        "/contacto",
        "/contacts",
        "/contact-us",
        "/about",
        "/about-us",
        "/quienes-somos",
        "/team",
        "/equipo",
        "/services",
        "/servicios",
        "/solutions",
        "/company",
        "/nosotros",
        "/support",
        "/soporte",
        "/careers",
        "/careers/",
        "/jobs",
        "/locations",
    ]
    for p in common_paths:
        candidate_paths.add(p)

    urls_to_check: List[str] = []
    seen_planned = set()
    for p in candidate_paths:
        if p == initial_path:
            full_url = url
        else:
            full_url = urljoin(base, p)
        if full_url not in seen_planned:
            urls_to_check.append(full_url)
            seen_planned.add(full_url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    }

    html_pages: List[str] = []
    title = ""
    description = ""
    h1_text = ""
    secondary_headings: List[str] = []
    key_paragraphs: List[str] = []
    bullet_points: List[str] = []
    checked_urls: List[str] = []

    visited = set()
    max_pages = 10

    while urls_to_check and len(visited) < max_pages:
        full_url = urls_to_check.pop(0)
        if full_url in visited:
            continue

        try:
            resp = requests.get(full_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                continue

            html = resp.text
            html_pages.append(html)
            visited.add(full_url)
            checked_urls.append(full_url)

            soup = BeautifulSoup(html, "html.parser")

            if not title and not description and not h1_text:
                if soup.title and soup.title.string:
                    title = soup.title.string.strip()

                description_tag = soup.find("meta", attrs={"name": "description"})
                if description_tag and description_tag.get("content"):
                    description = description_tag["content"].strip()
                if not description:
                    og_desc = soup.find("meta", attrs={"property": "og:description"})
                    if og_desc and og_desc.get("content"):
                        description = og_desc["content"].strip()

                h1 = soup.find("h1")
                if h1:
                    h1_text = h1.get_text(strip=True)

            for heading in soup.find_all(["h2", "h3"]):
                text = heading.get_text(" ", strip=True)
                if not text:
                    continue
                if text not in secondary_headings:
                    secondary_headings.append(text)
                if len(secondary_headings) >= 6:
                    break

            for p_tag in soup.find_all("p"):
                text = p_tag.get_text(" ", strip=True)
                if len(text) < 50:
                    continue
                if text not in key_paragraphs:
                    key_paragraphs.append(text)
                if len(key_paragraphs) >= 4:
                    break

            for li in soup.find_all("li"):
                text = li.get_text(" ", strip=True)
                if 30 <= len(text) <= 220 and text not in bullet_points:
                    bullet_points.append(text)
                if len(bullet_points) >= 6:
                    break

            if len(urls_to_check) < max_pages:
                extra_links = discover_internal_links(base, parsed.netloc, soup, max_links=6)
                for extra_url in extra_links:
                    if extra_url not in visited and extra_url not in urls_to_check:
                        urls_to_check.append(extra_url)
                    if len(urls_to_check) >= max_pages:
                        break

        except Exception:
            continue

    if not html_pages:
        st.warning("Could not fetch website pages.")
        return {}

    aggregated_html = "\n".join(html_pages)

    emails = extract_emails_from_text(aggregated_html)

    return {
        "url": url,
        "title": title,
        "description": description,
        "headline": h1_text,
        "secondary_headlines": secondary_headings[:6],
        "key_paragraphs": key_paragraphs[:4],
        "bullet_points": bullet_points[:6],
        "emails": sorted(list(emails)),
        "checked_urls": checked_urls,
    }
