# 🤖 Prospecting Assistant

## Overview
Prospecting Assistant is a Streamlit app that helps you research companies, capture website context, and generate personalized cold emails using Groq’s LLMs. It also lets you log feedback on the search results and on each generated email so you can keep iterating toward the copy that works best for your outreach.

## Prerequisites
- Python 3.10+
- Groq API key (create one for free at [console.groq.com](https://console.groq.com))
- Recommended: virtual environment such as `venv` or `conda`

## Setup
1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure environment**
   - Copy `api-key.env` to `.env` (or export `GROQ_API_KEY`) if you want the app to preload a key.
   - Optional: customize any defaults inside `app.py` (e.g., tone options, sectors).

## Running Locally
```bash
streamlit run app.py
```
The app opens in your browser at `http://localhost:8501`.

## Using the App
1. **Find targets** – Describe a sector or type a company to pull candidate websites.
2. **Review website info** – Fetch titles, meta descriptions, and emails; select what you want to feed into the AI.
3. **Set your value proposition** – Fill the sidebar field with the offer you are pitching; the prompt uses this verbatim.
4. **Configure tone & sections** – Pick greeting, offer style, CTA, etc., then generate the email via Groq.
5. **Give feedback** – Save “good” or “needs improvement” examples to CSV logs for future fine-tuning.
6. **Send** – Use the green mailto button to open your default email client with the subject/body pre-filled.

## Helpful Git Commands
The repo includes a `commands` file with quick references. The most common workflow is:
```bash
git pull origin main --allow-unrelated-histories
git add .
git commit -m "Your message"
git push origin main
```
Adapt these as needed for your branching strategy.
