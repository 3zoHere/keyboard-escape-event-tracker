import requests

UNIVERSE_ID = "9584852943"

url = f"https://apis.roblox.com/virtual-events/v1/universes/{UNIVERSE_ID}/virtual-events"

response = requests.get(url, timeout=30)

print("Status:", response.status_code)
print("Response:")
print(response.text)
