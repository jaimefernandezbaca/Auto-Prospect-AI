# functions/email_parsing.py

import json
import re


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
