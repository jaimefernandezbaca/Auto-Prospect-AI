import json
import re
import requests
import streamlit as st

import html

from bs4 import BeautifulSoup
from ddgs import DDGS
from urllib.parse import urlparse, parse_qs, quote

import os
import csv
from datetime import datetime


# ---------------------------------------------------------
# Clear cached data/session so prior test data is hidden
# ---------------------------------------------------------
CACHE_CLEARED_FLAG = "__cache_cleared__"

if CACHE_CLEARED_FLAG not in st.session_state:
    st.cache_data.clear()
    st.cache_resource.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state[CACHE_CLEARED_FLAG] = True


# ---------------------------------------------------------
# Streamlit basic config
# ---------------------------------------------------------
st.set_page_config(page_title="🤖 Prospecting Assistant", page_icon="🤖", layout="wide")
st.title("🤖 Prospecting Assistant")

st.markdown(
    """
    <style>
    button[title="feedback-good"] {
        background-color: #d1fae5 !important;
        color: #065f46 !important;
        border: 1px solid #86efac !important;
    }

    button[title="feedback-bad"] {
        background-color: #fee2e2 !important;
        color: #991b1b !important;
        border: 1px solid #fecaca !important;
    }

    a.mailto-button {
        display: inline-block;
        padding: 0.6rem 1.2rem;
        background-color: #22c55e;
        color: #0f172a !important;
        border-radius: 6px;
        text-decoration: none;
        font-weight: 600;
    }

    a.mailto-button:hover {
        background-color: #16a34a;
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "email_subject" not in st.session_state:
    st.session_state["email_subject"] = ""
if "email_body" not in st.session_state:
    st.session_state["email_body"] = ""


# ---------------------------------------------------------
# Sidebar configuration
# ---------------------------------------------------------

st.sidebar.header("Configuration")

# Groq API config (visible + persistente en sesión)
if "groq_api_key" not in st.session_state:
    st.session_state["groq_api_key"] = ""

groq_api_key = st.sidebar.text_input(
    "Groq API key",
    value=st.session_state["groq_api_key"],
    help="❓ Create a free key at https://console.groq.com (API Keys > Create API Key)."
)
st.session_state["groq_api_key"] = groq_api_key

# Groq model name
model_name = st.sidebar.text_input(
    "Groq model name",
    value="llama-3.1-8b-instant"
)

# Email language
email_language = st.sidebar.selectbox(
    "Email language",
    [
        "English",
        "Spanish",
        "French",
        "German",
        "Italian",
        "Portuguese"
    ],
    index=0
)

st.sidebar.markdown("---")

value_prop = st.sidebar.text_area(
    "Value proposition to highlight",
    value="",
    placeholder="Describe the service you're offering (e.g., \"We build custom AI automations for brokers\").",
)

tone = st.sidebar.selectbox(
    "Tone of the email",
    ["Professional", "Friendly", "Consultative", "Direct"],
    index=2,
)


# ---------------------------------------------------------
# Section configuration options
# ---------------------------------------------------------

GREETING_OPTIONS = {
    "formal_company": "Formal greeting addressing the company or team (e.g. 'Dear [Company] team').",
    "neutral_company": "Neutral greeting mentioning the company name (e.g. 'Hello [Company]').",
    "friendly": "Friendly greeting as if writing to a potential collaborator (e.g. 'Hi there')."
}

KNOWLEDGE_OPTIONS = {
    "generic_ref": "Generic reference to their website and online presence without specific details.",
    "specific_site": "Specific reference to what we see on their website (e.g. services, focus, locations).",
    "pain_point_guess": "Mention one or two likely challenges based on their type of business."
}

OFFER_OPTIONS = {
    "benefit_focused": "Explain how we help focusing on business outcomes (time savings, clarity, better decisions).",
    "technical_light": "Short explanation, light on technical details (mentions dashboards, automation, reporting).",
    "technical_heavier": "Slightly more technical, mentioning Power BI, data models and report automation."
}

DEMO_OPTIONS = {
    "short_call": "Propose a short introductory call of 15–20 minutes with one clear time suggestion.",
    "open_invite": "Ask if they would like to see a quick demo and let them propose a time.",
    "value_first": "Offer to show a small, relevant example/dashboard tailored to their context before a call."
}

GOODBYE_OPTIONS = {
    "formal": "Formal sign-off with thanks and full name.",
    "warm": "Warm, friendly sign-off but still professional.",
    "short": "Very short and concise sign-off."
}

SECTOR_OPTIONS = {
    "Any": "",
    "Dental / Clinics": "dental clinic",
    "Retail / eCommerce": "retail e-commerce online shop",
    "Software / SaaS": "software SaaS B2B",
    "Real Estate": "real estate property",
    "Hospitality": "hotel restaurant hospitality",
    "Professional Services": "consulting professional services",
}


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def looks_like_url(text: str) -> bool:
    text = text.strip()
    if text.startswith("http://") or text.startswith("https://"):
        return True
    if "." in text and " " not in text:
        return True
    return False


def normalize_url(maybe_url: str) -> str:
    maybe_url = maybe_url.strip()
    if maybe_url.startswith("http://") or maybe_url.startswith("https://"):
        return maybe_url
    return "https://" + maybe_url


def google_search_company_websites(
    company: str,
    sector_terms: str,
    max_results: int = 5
) -> list:
    """
    Usa Google para buscar webs candidatas de la empresa.
    Devuelve una lista de dicts: {"url", "title", "snippet", "source"}.
    """
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

    results = []

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
    """
    Fallback con DuckDuckGo. Devuelve lista de dicts: {"url", "title", "snippet", "source"}.
    """
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
        st.error(f"Error searching website (DuckDuckGo): {e}")
        return []

    return results


def search_company_websites(
    company: str,
    sector_terms: str,
    max_results: int = 5
) -> list:
    """
    Si el input parece URL, se usa directamente.
    Si no, Google -> DuckDuckGo, devolviendo hasta max_results candidatos.
    """
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


def fetch_website_info(url: str) -> dict:
    """
    Busca título, descripción, H1 y emails.
    - Usa la URL dada.
    - Intenta también paths típicos: /, /contacto, /contact, etc.
    - Extrae TODOS los emails encontrados.
    """
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
    ]
    for p in common_paths:
        candidate_paths.add(p)

    urls_to_check = []
    for p in candidate_paths:
        if p == initial_path:
            full_url = url
        else:
            if p.startswith("http"):
                full_url = p
            else:
                if not p.startswith("/"):
                    p = "/" + p
                full_url = base + p
        urls_to_check.append(full_url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    }

    html_pages = []
    title = ""
    description = ""
    h1_text = ""

    for full_url in urls_to_check:
        try:
            resp = requests.get(full_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                continue

            html = resp.text
            html_pages.append(html)

            if not title and not description and not h1_text:
                soup = BeautifulSoup(html, "html.parser")

                if soup.title and soup.title.string:
                    title = soup.title.string.strip()

                description_tag = soup.find("meta", attrs={"name": "description"})
                if description_tag and description_tag.get("content"):
                    description = description_tag["content"].strip()

                h1 = soup.find("h1")
                if h1:
                    h1_text = h1.get_text(strip=True)

        except Exception:
            continue

    if not html_pages:
        st.warning("Could not fetch website pages.")
        return {}

    aggregated_html = "\n".join(html_pages)

    emails = set(
        re.findall(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            aggregated_html,
        )
    )

    return {
        "url": url,
        "title": title,
        "description": description,
        "headline": h1_text,
        "emails": list(emails),
    }


def parse_email_json(raw: str) -> dict:
    if not raw:
        return {}

    cleaned = raw.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            snippet = match.group(0)
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                return {}
    return {}


def generate_email_with_groq(
    groq_api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    if not groq_api_key:
        raise ValueError("Groq API key is missing.")

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    return data["choices"][0]["message"]["content"]


def save_feedback_row(filename: str, row: dict) -> None:
    file_exists = os.path.isfile(filename)
    fieldnames = [
        "timestamp",
        "company_name",
        "website_url",
        "email_language",
        "tone",
        "greeting_choice",
        "knowledge_choice",
        "offer_choice",
        "demo_choice",
        "goodbye_choice",
        "context_text",
        "subject",
        "body",
        "feedback_text",
        "accepted",
    ]

    with open(filename, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def save_search_feedback_row(filename: str, row: dict) -> None:
    file_exists = os.path.isfile(filename)
    fieldnames = [
        "timestamp",
        "company_name",
        "sector_choice",
        "search_results",
        "selected_index",
        "selected_url",
        "feedback_text",
        "accepted",
    ]

    with open(filename, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ---------------------------------------------------------
# 1. Search company + sector
# ---------------------------------------------------------
st.markdown("### 1. Search company")

company_name = st.text_input(
    "Company name or website",
    placeholder="e.g. ExampleCorp or https://example.com"
)

sector_choice = st.selectbox(
    "Sector (optional)",
    list(SECTOR_OPTIONS.keys()),
    index=0,
)

if st.button("Search website"):
    if not company_name:
        st.error("Please enter a company name or website.")
    else:
        with st.spinner("Searching company websites..."):
            candidates = search_company_websites(
                company_name,
                SECTOR_OPTIONS[sector_choice],
                max_results=5,
            )

        if not candidates:
            st.warning("No website candidates found. Check the name or try another sector/term.")
        else:
            st.session_state["search_results"] = candidates
            st.session_state["website_url"] = ""
            st.session_state["company_info"] = {}
            st.success(f"Found {len(candidates)} candidate(s). Please select the correct one below.")


search_results = st.session_state.get("search_results", [])

if search_results:
    st.markdown("### 1b. Select website")

    def format_candidate(idx: int) -> str:
        c = search_results[idx]
        url = c["url"]
        parsed = urlparse(url)
        domain = parsed.netloc or url
        title = c.get("title") or ""
        snippet = c.get("snippet") or ""
        base = f"{domain}"
        if title:
            base += f" – {title}"
        elif snippet:
            base += f" – {snippet[:80]}"
        return base[:140]

    indices = list(range(len(search_results)))
    selected_index = st.radio(
        "Select the correct website",
        indices,
        format_func=format_candidate,
        key="selected_site_index"
    )

    if st.button("Use selected website"):
        selected = search_results[selected_index]
        st.session_state["website_url"] = selected["url"]
        st.success(f"Selected website: {selected['url']}")

    st.markdown("### 1c. Feedback about the search results")
    search_feedback_text = st.text_area(
        "Feedback about the website suggestions (what worked, what didn't)",
        key="search_feedback_note"
    )

    search_good_col, search_bad_col = st.columns(2)

    def build_search_feedback_row(accepted_flag: int) -> dict:
        selected_candidate = search_results[selected_index] if search_results else {}
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "company_name": company_name,
            "sector_choice": sector_choice,
            "search_results": json.dumps(search_results),
            "selected_index": selected_index,
            "selected_url": selected_candidate.get("url", ""),
            "feedback_text": search_feedback_text,
            "accepted": accepted_flag,
        }

    with search_good_col:
        if st.button(
            "💚 Save as good example",
            key="search_feedback_good",
            help="feedback-good",
        ):
            if not search_results:
                st.error("No search results to save feedback about.")
            else:
                row = build_search_feedback_row(1)
                save_search_feedback_row("search_feedback_log.csv", row)
                st.success("Saved search feedback as good example.")

    with search_bad_col:
        if st.button(
            "🚩 Save as needs improvement",
            key="search_feedback_bad",
            help="feedback-bad",
        ):
            if not search_results:
                st.error("No search results to save feedback about.")
            else:
                row = build_search_feedback_row(0)
                save_search_feedback_row("search_feedback_log.csv", row)
                st.success("Saved search feedback as needs improvement.")


website_url = st.session_state.get("website_url", "")


# ---------------------------------------------------------
# 2. Fetch and review website info
# ---------------------------------------------------------
if website_url:
    st.markdown("### 2. Review and select information to use")

    if st.button("Fetch website info"):
        info = fetch_website_info(website_url)
        st.session_state["company_info"] = info

info = st.session_state.get("company_info", {})

if info:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Fields to use as context")

        use_url = st.checkbox("Use website URL", value=True)
        use_title = st.checkbox("Use title", value=True)
        use_description = st.checkbox("Use meta description", value=True)
        use_headline = st.checkbox("Use main headline (H1)", value=True)

        selected_emails = []
        st.subheader("Emails found")
        if info["emails"]:
            for email in info["emails"]:
                if st.checkbox(
                    f"Use email: {email}", value=True, key=f"email_{email}"
                ):
                    selected_emails.append(email)
        else:
            st.write("No emails found on the page(s).")

    with col2:
        st.subheader("Raw info preview")
        st.write("Website:", info["url"])
        st.write("Title:", info["title"])
        st.write("Meta description:", info["description"])
        st.write("Headline (H1):", info["headline"])


    # -----------------------------------------------------
    # 3. Configure sections and generate email (using Groq)
    # -----------------------------------------------------
    st.markdown("### 3. Configure sections and generate email")

    st.markdown("**Section styles**")

    greeting_choice = st.selectbox(
        "Greeting style",
        options=list(GREETING_OPTIONS.keys()),
        format_func=lambda k: GREETING_OPTIONS[k]
    )

    knowledge_choice = st.selectbox(
        "What we know about them",
        options=list(KNOWLEDGE_OPTIONS.keys()),
        format_func=lambda k: KNOWLEDGE_OPTIONS[k]
    )

    offer_choice = st.selectbox(
        "How we can help / what we offer",
        options=list(OFFER_OPTIONS.keys()),
        format_func=lambda k: OFFER_OPTIONS[k]
    )

    demo_choice = st.selectbox(
        "How to propose a demo / next step",
        options=list(DEMO_OPTIONS.keys()),
        format_func=lambda k: DEMO_OPTIONS[k]
    )

    goodbye_choice = st.selectbox(
        "Goodbye / sign-off style",
        options=list(GOODBYE_OPTIONS.keys()),
        format_func=lambda k: GOODBYE_OPTIONS[k]
    )

    # Nombre con el que se firma
    sender_name = st.text_input(
        "Your name for the signature",
        value="Your Name"
    )

    if st.button("Generate cold email"):

        if not value_prop.strip():
            st.error("Please enter your value proposition in the sidebar before generating the email.")
        elif not groq_api_key:
            st.error("Please enter your Groq API key in the sidebar.")
        else:
            context_parts = []
            if use_url and info.get("url"):
                context_parts.append(f"Website: {info['url']}")
            if use_title and info.get("title"):
                context_parts.append(f"Title: {info['title']}")
            if use_description and info.get("description"):
                context_parts.append(f"Meta description: {info['description']}")
            if use_headline and info.get("headline"):
                context_parts.append(f"Headline (H1): {info['headline']}")

            context_text = "\n".join(context_parts)

            greeting_desc = GREETING_OPTIONS[greeting_choice]
            knowledge_desc = KNOWLEDGE_OPTIONS[knowledge_choice]
            offer_desc = OFFER_OPTIONS[offer_choice]
            demo_desc = DEMO_OPTIONS[demo_choice]
            goodbye_desc = GOODBYE_OPTIONS[goodbye_choice]

            system_prompt = (
                "You are an expert B2B sales copywriter who always returns valid JSON. "
                "You write clear, concise, value-driven cold emails."
            )

            user_prompt = f"""
Your task is to write a short cold email to offer Power BI consulting services.

Language:
- Write the entire email in: {email_language}.

Constraints:
- Max 120 words.
- Tone: {tone}.
- 1 clear CTA.
- Do not be generic — use the context when relevant.
- Keep the copy sharp and value-driven.

Company name: {company_name}

Context from the website:
{context_text}

Value proposition to highlight:
{value_prop}

STRUCTURE REQUIRED (in this exact order):

1. Greeting:
   - Style: {greeting_desc}

2. What we know about them:
   - Style: {knowledge_desc}

3. How we can help / what we offer:
   - Style: {offer_desc}

4. How to propose a demo / next step:
   - Style: {demo_desc}

5. Goodbye / sign-off:
   - Style: {goodbye_desc}
   - Sign with this exact name: {sender_name}

Return ONLY a valid JSON object:
{{
  "subject": "...",
  "body": "..."
}}
No explanations, no markdown, no extra text.
"""

            with st.spinner("Generating email using Groq…"):
                try:
                    raw = generate_email_with_groq(
                        groq_api_key=groq_api_key,
                        model=model_name,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                    )
                except Exception as e:
                    st.error(f"Error calling Groq API: {e}")
                    raw = ""

            data = parse_email_json(raw)
            if not data:
                st.warning("Model did not return valid JSON. Showing raw output.")
                data = {"subject": "", "body": raw}

            subject = data.get("subject", "")
            body = data.get("body", "")

            st.session_state["email_subject"] = subject
            st.session_state["email_body"] = body

            st.success("Email generated. You can edit it below.")

    st.markdown("### 3b. Review generated email")
    if not st.session_state.get("email_body"):
        st.info("Generate an email to populate these fields, or edit them manually.")

    st.text_input("Subject", key="email_subject")
    st.text_area("Body", height=220, key="email_body")

    # -----------------------------------------------------
    # 4. Feedback & save to CSV
    # -----------------------------------------------------
    st.markdown("### 4. Feedback and save example")

    feedback_text = st.text_area(
        "Optional feedback about this email (what you like, what you'd change, etc.)",
        key="feedback_note"
    )

    col_good, col_bad = st.columns(2)

    with col_good:
        if st.button("💚 Save as good example", help="feedback-good"):
            current_subject = st.session_state.get("email_subject", "")
            current_body = st.session_state.get("email_body", "")

            if not current_body:
                st.error("No email to save yet. Generate an email first.")
            else:
                context_parts = []
                if info.get("url") and use_url:
                    context_parts.append(f"Website: {info['url']}")
                if info.get("title") and use_title:
                    context_parts.append(f"Title: {info['title']}")
                if info.get("description") and use_description:
                    context_parts.append(f"Meta description: {info['description']}")
                if info.get("headline") and use_headline:
                    context_parts.append(f"Headline (H1): {info['headline']}")
                context_text = "\n".join(context_parts)

                row = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "company_name": company_name,
                    "website_url": website_url,
                    "email_language": email_language,
                    "tone": tone,
                    "greeting_choice": greeting_choice,
                    "knowledge_choice": knowledge_choice,
                    "offer_choice": offer_choice,
                    "demo_choice": demo_choice,
                    "goodbye_choice": goodbye_choice,
                    "context_text": context_text,
                    "subject": current_subject,
                    "body": current_body,
                    "feedback_text": feedback_text,
                    "accepted": 1,
                }
                save_feedback_row("email_feedback_log.csv", row)
                st.success("Saved as good example.")

    with col_bad:
        if st.button("🚩 Save as needs improvement", help="feedback-bad"):
            current_subject = st.session_state.get("email_subject", "")
            current_body = st.session_state.get("email_body", "")

            if not current_body:
                st.error("No email to save yet. Generate an email first.")
            else:
                context_parts = []
                if info.get("url") and use_url:
                    context_parts.append(f"Website: {info['url']}")
                if info.get("title") and use_title:
                    context_parts.append(f"Title: {info['title']}")
                if info.get("description") and use_description:
                    context_parts.append(f"Meta description: {info['description']}")
                if info.get("headline") and use_headline:
                    context_parts.append(f"Headline (H1): {info['headline']}")
                context_text = "\n".join(context_parts)

                row = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "company_name": company_name,
                    "website_url": website_url,
                    "email_language": email_language,
                    "tone": tone,
                    "greeting_choice": greeting_choice,
                    "knowledge_choice": knowledge_choice,
                    "offer_choice": offer_choice,
                    "demo_choice": demo_choice,
                    "goodbye_choice": goodbye_choice,
                    "context_text": context_text,
                    "subject": current_subject,
                    "body": current_body,
                    "feedback_text": feedback_text,
                    "accepted": 0,
                }
                save_feedback_row("email_feedback_log.csv", row)
                st.success("Saved as needs improvement.")

    # -----------------------------------------------------
    # 5. Send email (opens your mail client)
    # -----------------------------------------------------
    st.markdown("### 5. Send email (opens your mail client)")

    # If multiple emails were selected, default to all of them
    default_to = ""
    if 'selected_emails' in locals() and selected_emails:
        if len(selected_emails) == 1:
            default_to = selected_emails[0]
        else:
            # join multiple recipients with comma so the mail client sends to all
            default_to = ", ".join(selected_emails)

    to_email = st.text_input(
        "Recipient email(s)",
        value=default_to,
        key="recipient_email"
    )

    current_subject = st.session_state.get("email_subject", "")
    current_body = st.session_state.get("email_body", "")

    if not current_subject or not current_body:
        st.info("Generate the email first to enable the mailto link.")
    else:
        if not to_email:
            st.warning("Please enter at least one recipient email.")
        else:
            # Clean up recipient list so mailto links don't include raw spaces
            recipients = [addr.strip() for addr in re.split(r"[;,]", to_email) if addr.strip()]
            mailto_recipients = ",".join(recipients)

            if not mailto_recipients:
                st.warning("Please enter at least one valid recipient email.")
            else:
                mailto_url = (
                    f"mailto:{mailto_recipients}?subject={quote(current_subject)}&body={quote(current_body)}"
                )
                safe_mailto = html.escape(mailto_url, quote=True)
                st.markdown(
                    f'<a class="mailto-button" href="{safe_mailto}">Open in your email client</a>',
                    unsafe_allow_html=True,
                )
