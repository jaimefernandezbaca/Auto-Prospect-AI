import requests
from requests.exceptions import RequestException

def get_latest_commit(repo_owner: str, repo_name: str, branch: str = "main"):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits/{branch}"
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
    except RequestException as e:
        return None, f"Error fetching commit: {e!r}"
    try:
        data = resp.json()
        sha = data.get("sha")
        if not sha:
            return None, "No SHA in response"
        sha7 = sha[:7]
        message = data.get("commit", {}).get("message", "").split("\n")[0]
        return sha7, message or "(no message)"
    except ValueError:
        return None, "Invalid JSON response"
