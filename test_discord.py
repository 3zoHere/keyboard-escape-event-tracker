import os
import requests

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]

payload = {
    "username": "Roblox Events",
    "content": "🧪 **Discord Webhook Test**\n\nإذا تشوف الصورة الجديدة، فالاختبار نجح ✅"
}

response = requests.post(
    WEBHOOK_URL,
    json=payload,
    timeout=30
)

print("Discord status:", response.status_code)
response.raise_for_status()
