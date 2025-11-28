import streamlit as st
from typing import Any, Dict, List

from functions.scraping import search_company_website, extract_website_context
from functions.email_builder import build_prospect_email
from functions.feedback_storage import save_email_feedback, save_search_feedback


def render_main_page() -> None:
    st.title("Auto Prospect AI")

    # ─────────────────────────────────────────
    # 1. Input de empresa y búsqueda
    # ─────────────────────────────────────────
    st.subheader("Company search")

    col1, col2 = st.columns([2, 1])
    with col1:
        company_name = st.text_input("Company name", placeholder="Acme Ltd")
        sector = st.text_input("Sector (optional)", placeholder="e.g. SaaS, consulting")

    with col2:
        country = st.text_input("Country (optional)", placeholder="e.g. UK, Spain")

    if st.button("Search website"):
        if not company_name.strip():
            st.error("Please enter at least a company name.")
        else:
            with st.spinner("Searching company website..."):
                search_results = search_company_website(
                    company_name=company_name,
                    sector=sector or None,
                    country=country or None,
                )

            if not search_results:
                st.warning("No results found.")
            else:
                st.session_state["search_results"] = search_results

    # Mostrar resultados si existen
    search_results: List[Dict[str, Any]] = st.session_state.get("search_results", [])
    selected_result = None
    if search_results:
        st.subheader("Search results")
        # Aquí puedes adaptar al formato que ya usabas (tablas, radios, botones)
        for i, res in enumerate(search_results):
            st.markdown(f"**{i+1}. {res.get('title', '')}**")
            st.write(res.get("url", ""))
            st.caption(res.get("snippet", ""))

        selected_index = st.number_input(
            "Select result index",
            min_value=1,
            max_value=len(search_results),
            step=1,
            value=1,
        )
        selected_result = search_results[int(selected_index) - 1]

    # ─────────────────────────────────────────
    # 2. Extracción de contexto de la web
    # ─────────────────────────────────────────
    website_context = None
    if selected_result:
        if st.button("Extract website context"):
            with st.spinner("Extracting website content..."):
                website_context = extract_website_context(selected_result["url"])
            st.session_state["website_context"] = website_context

    website_context = st.session_state.get("website_context")
    if website_context:
        with st.expander("Raw website context"):
            st.text(website_context[:4000])

    # ─────────────────────────────────────────
    # 3. Configuración del email
    # ─────────────────────────────────────────
    st.subheader("Email configuration")

    col_email1, col_email2 = st.columns(2)
    with col_email1:
        language = st.selectbox("Email language", ["English", "Spanish"])
        tone = st.selectbox("Tone", ["Formal", "Neutral", "Friendly"])
    with col_email2:
        include_demo = st.checkbox("Offer a demo call", value=True)
        include_value_prop = st.checkbox("Highlight value proposition", value=True)

    extra_context = st.text_area(
        "Additional context (optional)",
        placeholder="Anything specific about their company, product, or your offer...",
    )

    # ─────────────────────────────────────────
    # 4. Generación del email
    # ─────────────────────────────────────────
    if st.button("Generate email"):
        if not selected_result:
            st.error("Please select a search result first.")
        else:
            with st.spinner("Generating email..."):
                email_data = build_prospect_email(
                    company_name=company_name,
                    website_url=selected_result["url"],
                    website_context=website_context or "",
                    language=language,
                    tone=tone,
                    include_demo=include_demo,
                    include_value_prop=include_value_prop,
                    extra_context=extra_context,
                )

            st.session_state["email_data"] = email_data

    email_data = st.session_state.get("email_data")
    if email_data:
        st.subheader("Generated email")
        st.markdown("**Subject:**")
        st.code(email_data["subject"])
        st.markdown("**Body:**")
        st.code(email_data["body"])

        # ─────────────────────────────────────────
        # 5. Feedback del email
        # ─────────────────────────────────────────
        st.subheader("Feedback on this email")

        feedback_text = st.text_area(
            "What would you change or improve?",
            key="email_feedback_text",
        )
        accepted = st.checkbox("Would you use this email as is?", value=False)

        if st.button("Send email feedback"):
            save_email_feedback(
                company_name=company_name,
                website_url=email_data.get("website_url", selected_result["url"]),
                language=language,
                tone=tone,
                email_subject=email_data["subject"],
                email_body=email_data["body"],
                feedback_text=feedback_text,
                accepted=accepted,
            )
            st.success("Feedback saved. Thank you!")
