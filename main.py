import json
import os
import requests
from datetime import datetime

GROUP_ID = "1074557114"
UNIVERSE_ID = "9584852943"

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]

API_URL = (
    f"https://apis.roblox.com/virtual-events/v1/"
    f"universes/{UNIVERSE_ID}/virtual-events"
)

STATE_FILE = "events_state.json"


def load_state():
    if not os.path.exists(STATE_FILE):
        return None

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(event_ids):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"event_ids": event_ids},
            f,
            ensure_ascii=False,
            indent=2
        )


def get_events():
    events = []
    cursor = ""

    while True:
        params = {}

        if cursor:
            params["cursor"] = cursor

        response = requests.get(
            API_URL,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        events.extend(data.get("data", []))

        cursor = data.get("nextPageCursor")

        if not cursor:
            break

    return events


def send_to_discord(event):
    event_id = event["id"]

    title = event.get("displayTitle") or event.get("title") or "New Roblox Event"
    subtitle = event.get("displaySubtitle") or event.get("subtitle") or ""
    description = (
        event.get("displayDescription")
        or event.get("description")
        or ""
    )

    event_time = event.get("eventTime", {})

    start = event_time.get("startUtc")
    end = event_time.get("endUtc")

    event_url = f"https://www.roblox.com/events/{event_id}"

    fields = []

    if subtitle:
        fields.append({
            "name": "Details",
            "value": subtitle[:1024],
            "inline": False
        })

    if start:
        fields.append({
            "name": "Starts",
            "value": f"<t:{int(datetime.fromisoformat(start.replace('Z', '+00:00')).timestamp())}:F>",
            "inline": True
        })

    if end:
        fields.append({
            "name": "Ends",
            "value": f"<t:{int(datetime.fromisoformat(end.replace('Z', '+00:00')).timestamp())}:F>",
            "inline": True
        })

    embed = {
        "title": f"📢 {title}",
        "url": event_url,
        "description": description[:4096],
        "fields": fields,
        "footer": {
            "text": "SecretVerse Roblox Events"
        }
    }

    payload = {
        "username": "Roblox Events",
        "embeds": [embed]
    }

    response = requests.post(
        WEBHOOK_URL,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    print(f"Sent event: {event_id}")


def main():
    events = get_events()

    # Only events belonging to SecretVerse Studio
    events = [
        event
        for event in events
        if str(event.get("host", {}).get("hostId")) == GROUP_ID
    ]

    print(f"Found {len(events)} SecretVerse events.")

    current_ids = {str(event["id"]) for event in events}

    state = load_state()

    # First run:
    # Save existing events without announcing them.
    if state is None:
        save_state(sorted(current_ids))
        print("First run: existing events saved. No Discord messages sent.")
        return

    old_ids = set(state.get("event_ids", []))

    new_events = [
        event
        for event in events
        if str(event["id"]) not in old_ids
    ]

    new_events.sort(
        key=lambda event: event.get("createdUtc", "")
    )

    for event in new_events:
        send_to_discord(event)

    save_state(sorted(current_ids))

    print(f"New events sent: {len(new_events)}")


if __name__ == "__main__":
    main()
