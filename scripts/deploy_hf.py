"""Deploy KB-Geoid to Hugging Face Spaces automatically."""

import os
import sys
from pathlib import Path
from huggingface_hub import HfApi

REPO_ID = "KhinBunly/kb-geoid-bot"
BASE_DIR = Path(__file__).resolve().parent.parent


def deploy(hf_token: str):
    print(f"Connecting to Hugging Face Space: {REPO_ID}...")
    api = HfApi(token=hf_token)

    # 1. Set secret TELEGRAM_BOT_TOKEN
    bot_token = "8907224822:AAET1E4Eb2h_MYHd-8qJ6kXCt_DLqDzTuAo"
    print("Setting secret TELEGRAM_BOT_TOKEN...")
    try:
        api.add_space_secret(repo_id=REPO_ID, key="TELEGRAM_BOT_TOKEN", value=bot_token)
        print(" Secret TELEGRAM_BOT_TOKEN set successfully!")
    except Exception as e:
        print(f" Note on secret: {e}")

    # 2. Upload files
    print("Uploading project files to Space...")
    api.upload_folder(
        folder_path=str(BASE_DIR),
        repo_id=REPO_ID,
        repo_type="space",
        ignore_patterns=[
            ".git*",
            ".env",
            "venv*",
            ".venv*",
            "__pycache__*",
            "*.pyc",
            ".proj_cache*",
            "logs*",
            ".pytest_cache*",
        ],
    )
    print(" All files uploaded successfully!")
    print(f"🚀 Your bot is now building and running live at: https://huggingface.co/spaces/{REPO_ID}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/deploy_hf.py <HF_TOKEN>")
        sys.exit(1)
    deploy(sys.argv[1])
