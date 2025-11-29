# functions/config.py

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
