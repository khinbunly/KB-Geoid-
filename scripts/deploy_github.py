"""Upload latest KB-Geoid project files to GitHub repository automatically."""

import base64
import os
from pathlib import Path
import sys
import requests

REPO_OWNER = "khinbunly"
REPO_NAME = "KB-Geoid-"
BASE_DIR = Path(__file__).resolve().parent.parent

EXCLUDE_PATTERNS = [
    ".git",
    ".env",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".proj_cache",
    "logs",
]


def should_exclude(rel_path: str) -> bool:
    for pattern in EXCLUDE_PATTERNS:
        if pattern in rel_path.split(os.sep) or pattern in rel_path.split("/"):
            return True
    return False


def get_file_sha(token: str, path: str):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Accept": "application/vnd.github+json",
    }
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json().get("sha")
    return None


def upload_file_to_github(token: str, local_path: Path, rel_path: str):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{rel_path}"
    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Accept": "application/vnd.github+json",
    }

    with open(local_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode("utf-8")

    sha = get_file_sha(token, rel_path)
    payload = {
        "message": f"Update {rel_path} with latest production engine",
        "content": content_b64,
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=headers, json=payload)
    if r.status_code in [200, 201]:
        print(f" Uploaded: {rel_path}")
        return True
    else:
        print(f" Failed {rel_path} ({r.status_code}): {r.text}")
        return False


def deploy_all(token: str):
    print(f"Connecting to GitHub: {REPO_OWNER}/{REPO_NAME}...")
    count = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            full_path = Path(root) / file
            rel_path = full_path.relative_to(BASE_DIR).as_posix()
            if should_exclude(rel_path):
                continue
            upload_file_to_github(token, full_path, rel_path)
            count += 1

    print(f"\n Successfully synced {count} files to GitHub!")
    print("Render.com will now automatically rebuild with the latest code!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/deploy_github.py <GITHUB_TOKEN>")
        sys.exit(1)
    deploy_all(sys.argv[1])
