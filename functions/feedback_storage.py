# functions/feedback_storage.py

import os
import csv
from datetime import datetime


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
