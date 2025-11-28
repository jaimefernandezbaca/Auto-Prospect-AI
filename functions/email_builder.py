from typing import Dict, Any


def build_prospect_email(
    company_name: str,
    website_url: str,
    website_context: str,
    language: str,
    tone: str,
    include_demo: bool,
    include_value_prop: bool,
    extra_context: str,
) -> Dict[str, str]:
    """
    Pure logic to build subject and body for the email.
    Puedes llamar aquí a tu modelo (Groq, OpenAI, etc.)
    o componer el prompt y luego la UI hace la llamada.
    """

    # Aquí deberías reusar tus dicts de opciones:
    # GREETING_OPTIONS, KNOWLEDGE_OPTIONS, OFFER_OPTIONS, DEMO_OPTIONS...
    # Puedes importarlos desde otro módulo o definirlos aquí.

    # Ejemplo tonto a modo de placeholder:
    subject = f"{company_name} – Exploring how we can help with data & reporting"
    body_parts = []

    body_parts.append(f"Hi {company_name} team,")
    body_parts.append("")
    body_parts.append(
        "I've been reviewing your website and it seems you are growing in the "
        "area of [replace with sector / value]."
    )
    if include_value_prop:
        body_parts.append(
            "I help teams structure their data and reporting so they can make faster, "
            "clearer decisions using Power BI and automated dashboards."
        )
    if include_demo:
        body_parts.append(
            "If this is relevant, I'm happy to show you a quick 15-minute demo with a "
            "concrete example tailored to your context."
        )

    if extra_context:
        body_parts.append("")
        body_parts.append(f"Additional context taken into account: {extra_context}")

    body_parts.append("")
    body_parts.append("Best regards,")
    body_parts.append("Jaime")

    body = "\n".join(body_parts)

    return {
        "subject": subject,
        "body": body,
        "website_url": website_url,
    }
