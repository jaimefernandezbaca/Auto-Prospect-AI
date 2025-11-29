# layout/main_layout.py

import json
import re
import html
from datetime import datetime
from urllib.parse import urlparse, quote

import streamlit as st

from functions.config import (
    GREETING_OPTIONS,
    KNOWLEDGE_OPTIONS,
    OFFER_OPTIONS,
    DEMO_OPTIONS,
    GOODBYE_OPTIONS,
    SECTOR_OPTIONS,
)
from functions.search import search_company_websites
from functions.scraping import fetch_website_info
from functions.email_generation import generate_email_with_groq
from functions.email_parsing import parse_email_json
from functions.feedback_storage import save_feedback_row, save_search_feedback_row
from functions.version import get_latest_commit


def render_page() -> None:
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
    # Streamlit basic config (set_page_config va en app.py)
    # ---------------------------------------------------------
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

        .section-hint {
            color: #475569;
            font-size: 0.95rem;
            margin-top: -0.5rem;
            margin-bottom: 0.8rem;
        }

        .optional-note {
            color: #6366f1;
            font-style: italic;
            font-size: 0.95rem;
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
    
    # --- Existing sidebar code ---
    st.sidebar.markdown("---")

    sha, msg = get_latest_commit("jaimefernandezbaca", "Auto-Prospect-AI")
    if sha:
        st.sidebar.caption(f"Version: `{sha}` — {msg}")
    else:
        st.sidebar.caption(f"Version: unavailable ({msg})")



    # ---------------------------------------------------------
    # 1. Search company + sector
    # ---------------------------------------------------------
    st.markdown("### 1. Search company")
    st.markdown(
        '<p class="section-hint">Start by identifying a company or website so we can pull the right context.</p>',
        unsafe_allow_html=True,
    )

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
        st.markdown(
            '<p class="section-hint">Choose the domain that best matches your target.</p>',
            unsafe_allow_html=True,
        )

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
        st.markdown(
            '<p class="optional-note">Optional: Let us know if these candidates were useful.</p>',
            unsafe_allow_html=True,
        )
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

    st.divider()

    # ---------------------------------------------------------
    # 2. Fetch and review website info
    # ---------------------------------------------------------
    if website_url:
        st.markdown("### 2. Review and select information to use")
        st.markdown(
            '<p class="section-hint">Scan the site and decide which details the AI should reference.</p>',
            unsafe_allow_html=True,
        )

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
            st.write("Website:", info.get("url", ""))
            st.write("Title:", info.get("title", ""))
            st.write("Meta description:", info.get("description", ""))
            st.write("Headline (H1):", info.get("headline", ""))

            if info.get("secondary_headlines"):
                st.write("Supporting headlines:")
                st.markdown("\n".join(f"- {text}" for text in info["secondary_headlines"]))

            if info.get("key_paragraphs"):
                st.write("Key paragraphs:")
                for para in info["key_paragraphs"]:
                    st.markdown(f"> {para}")

            if info.get("bullet_points"):
                st.write("Service highlights:")
                st.markdown("\n".join(f"- {item}" for item in info["bullet_points"]))

            if info.get("checked_urls"):
                st.caption(f"Pages scanned: {len(info['checked_urls'])}")

        # -----------------------------------------------------
        # 3. Configure sections and generate email (using Groq)
        # -----------------------------------------------------
        st.divider()
        st.markdown("### 3. Configure sections and generate email")
        st.markdown(
            '<p class="section-hint">Pick the narrative style, confirm your value proposition, and let Groq draft the message.</p>',
            unsafe_allow_html=True,
        )

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

        sender_name = st.text_input(
            "Your name for the signature",
            value="Your Name"
        )

        if st.button("Generate cold email"):

            if not value_prop.strip():
                st.error("Please enter your value proposition in the sidebar before generating the email.")
            elif sender_name.strip() == "" or sender_name.strip().lower() == "your name".lower():
                st.error("Please enter the name you want to use in the signature.")
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
Your task is to write a short cold email tailored to the value proposition described below.

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

Value proposition to highlight (use this to understand the offer we sell):
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
        st.divider()
        st.markdown("### 4. Feedback and save example")
        st.markdown(
            '<p class="optional-note">Optional: Capture what worked so you can train future prompts.</p>',
            unsafe_allow_html=True,
        )

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
        st.divider()
        st.markdown("### 5. Send email (opens your mail client)")
        st.markdown(
            '<p class="section-hint">When you like the copy, preview or send it via your default email client.</p>',
            unsafe_allow_html=True,
        )

        default_to = ""
        if "selected_emails" in locals() and selected_emails:
            if len(selected_emails) == 1:
                default_to = selected_emails[0]
            else:
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
