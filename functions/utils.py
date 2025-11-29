# functions/utils.py

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
