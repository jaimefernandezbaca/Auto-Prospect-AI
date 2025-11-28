from typing import Optional
import csv
from datetime import datetime
import os


FEEDBACK_EMAIL_CSV = "email_feedback_log.csv"
FEEDBACK_SEARCH_CSV = "search_feedback_log.csv"


def _ensure_file_with_header(path: str, fieldnames: list[str]) -> None:
    if not os.path.exists(path):
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


def save_email_feedback(
    company_name: str,
    website_url: str,
    language: str,
    tone: str,
    email_subject: str,
    email_body: str,
    feedback_text: str,
    accepted: bool,
    context_text: Optional[str] = None,
) -> None:
    fieldnames = [
        "timestamp",
        "company_name",
        "website_url",
        "email_language",
        "tone",
        "subject",
        "body",
        "context_text",
        "feedback_text",
        "accepted",
    ]
    _ensure_file_with_header(FEEDBACK_EMAIL_CSV, fieldnames)

    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "company_name": company_name,
        "website_url": website_url,
        "email_language": language,
        "tone": tone,
        "subject": email_subject,
        "body": email_body,
        "context_text": context_text or "",
        "feedback_text": feedback_text,
        "accepted": "yes" if accepted else "no",
    }

    with open(FEEDBACK_EMAIL_CSV, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)


def save_search_feedback(
    company_name: str,
    sector: str,
    search_results_serialized: str,
    selected_index: int,
    selected_url: str,
    feedback_text: str,
    accepted: bool,
) -> None:
    fieldnames = [
        "timestamp",
        "company_name",
        "sector",
        "search_results",
        "selected_index",
        "selected_url",
        "feedback_text",
        "accepted",
    ]
    _ensure_file_with_header(FEEDBACK_SEARCH_CSV, fieldnames)

    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "company_name": company_name,
        "sector": sector,
        "search_results": search_results_serialized,
        "selected_index": selected_index,
        "selected_url": selected_url,
        "feedback_text": feedback_text,
        "accepted": "yes" if accepted else "no",
    }

    with open(FEEDBACK_SEARCH_CSV, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)
