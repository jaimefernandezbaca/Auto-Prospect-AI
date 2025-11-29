# functions/email_generation.py

import requests


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
