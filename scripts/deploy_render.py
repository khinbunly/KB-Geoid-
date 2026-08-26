"""Deploy and configure Render.com service automatically via Render API."""

import sys
import time
import requests

SERVICE_ID = "srv-da74sg2d0e5s73damjgg"
BOT_TOKEN = "8907224822:AAET1E4Eb2h_MYHd-8qJ6kXCt_DLqDzTuAo"
RENDER_API_BASE = "https://api.render.com/v1"


def deploy_to_render(api_key: str):
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    print(f"1. Checking Render service: {SERVICE_ID}...")
    r = requests.get(f"{RENDER_API_BASE}/services/{SERVICE_ID}", headers=headers)
    if r.status_code != 200:
        print(f"Error connecting to Render API ({r.status_code}): {r.text}")
        return False

    service_data = r.json()
    print(f" Found service: {service_data.get('name')} (Type: {service_data.get('type')})")

    # 2. Update Environment Variables
    print("2. Setting Environment Variables on Render...")
    env_vars = [
        {"key": "TELEGRAM_BOT_TOKEN", "value": BOT_TOKEN},
        {"key": "APP_ENV", "value": "production"},
        {"key": "LOG_LEVEL", "value": "INFO"},
        {"key": "PROJ_NETWORK", "value": "true"},
    ]
    r_env = requests.put(
        f"{RENDER_API_BASE}/services/{SERVICE_ID}/env-vars",
        headers=headers,
        json=env_vars,
    )
    if r_env.status_code in [200, 201]:
        print(" Environment variables updated successfully!")
    else:
        print(f" Note on env vars ({r_env.status_code}): {r_env.text}")

    # 3. Trigger Deploy
    print("3. Triggering Deployment...")
    r_deploy = requests.post(
        f"{RENDER_API_BASE}/services/{SERVICE_ID}/deploys",
        headers=headers,
        json={"clearCache": "do_not_clear"},
    )
    if r_deploy.status_code in [200, 201]:
        deploy_data = r_deploy.json()
        deploy_id = deploy_data.get("id")
        print(f" Deployment triggered successfully! (Deploy ID: {deploy_id})")
        print("🚀 Your bot is now building and going live 24/7 on Render.com!")
        return True
    else:
        print(f" Deploy trigger response ({r_deploy.status_code}): {r_deploy.text}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/deploy_render.py <RENDER_API_KEY>")
        sys.exit(1)
    deploy_to_render(sys.argv[1])
