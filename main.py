import os
import requests

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]

payload = {
    "username": "Roblox Events",
    "content": "🧪 **Test successful!** Roblox Events bot is connected to Discord."
}

response = requests.post(
    WEBHOOK_URL,
    json=payload,
    timeout=30
)

print("Discord status:", response.status_code)
print(response.text)

response.raise_for_status()
