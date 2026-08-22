import json
import os
import requests
from datetime import datetime, timezone

GROUP_ID = "1074557114"
UNIVERSE_ID = "9584852943"

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]

API_URL = (
    f"https://apis.roblox.com/virtual-events/v1/"
    f"universes/{UNIVERSE_ID}/virtual-events"
)

EVENTS_STATE_FILE = "events_state.json"
ALERTS_STATE_FILE = "alerts_state.json"


def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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


def parse_time(value):
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def send_to_discord(event, message):
    event_id = event["id"]

    title = (
        event.get("displayTitle")
        or event.get("title")
        or "Roblox Event"
    )

    subtitle = (
        event.get("displaySubtitle")
        or event.get("subtitle")
        or ""
    )

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
        start_timestamp = int(
            parse_time(start).timestamp()
        )

        fields.append({
            "name": "Starts",
            "value": f"<t:{start_timestamp}:F>",
            "inline": True
        })

    if end:
        end_timestamp = int(
            parse_time(end).timestamp()
        )

        fields.append({
            "name": "Ends",
            "value": f"<t:{end_timestamp}:F>",
            "inline": True
        })

    embed = {
        "title": title,
        "url": event_url,
        "description": description[:4096],
        "fields": fields,
        "footer": {
            "text": "SecretVerse Roblox Events"
        }
    }

    payload = {
        "username": "Roblox Events",
        "content": message,
        "embeds": [embed]
    }

    response = requests.post(
        WEBHOOK_URL,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    print(
        f"Discord message sent successfully: {response.status_code}"
    )


def send_new_event(event):
    title = (
        event.get("displayTitle")
        or event.get("title")
        or "New Roblox Event"
    )

    send_to_discord(
        event,
        f"📢 **NEW EVENT!**\n**{title}**"
    )

    print(
        f"New event announced: {event['id']}"
    )


def send_alert(event, alert_type):
    title = (
        event.get("displayTitle")
        or event.get("title")
        or "Roblox Event"
    )

    messages = {
        "1h": (
            f"🟡 **EVENT STARTING IN 1 HOUR!**\n"
            f"**{title}**"
        ),

        "15m": (
            f"🟠 **EVENT STARTING IN 15 MINUTES!**\n"
            f"**{title}**"
        ),

        "start": (
            f"🔴 **EVENT IS LIVE NOW!**\n"
            f"**{title}**"
        )
    }

    send_to_discord(
        event,
        messages[alert_type]
    )

    print(
        f"Sent {alert_type} alert for event {event['id']}"
    )


def check_alerts(events, alerts_state):
    now = datetime.now(timezone.utc)

    for event in events:

        event_id = str(event["id"])

        event_time = event.get("eventTime", {})

        start = parse_time(
            event_time.get("startUtc")
        )

        end = parse_time(
            event_time.get("endUtc")
        )

        if not start:
            continue

        # Ignore ended events
        if end and now >= end:
            continue

        if event_id not in alerts_state:
            alerts_state[event_id] = []

        sent_alerts = alerts_state[event_id]

        seconds_until_start = (
            start - now
        ).total_seconds()

        # -------------------------
        # 1 HOUR ALERT
        # -------------------------

        if (
            "1h" not in sent_alerts
            and 0 < seconds_until_start <= 3600
        ):

            send_alert(
                event,
                "1h"
            )

            sent_alerts.append("1h")

        # -------------------------
        # 15 MINUTE ALERT
        # -------------------------

        if (
            "15m" not in sent_alerts
            and 0 < seconds_until_start <= 900
        ):

            send_alert(
                event,
                "15m"
            )

            sent_alerts.append("15m")

        # -------------------------
        # EVENT STARTED
        # -------------------------

        if (
            "start" not in sent_alerts
            and seconds_until_start <= 0
        ):

            send_alert(
                event,
                "start"
            )

            sent_alerts.append("start")

    return alerts_state


def main():

    events = get_events()

    # Only SecretVerse Studio events
    events = [
        event
        for event in events
        if str(
            event.get("host", {}).get("hostId")
        ) == GROUP_ID
    ]

    print(
        f"Found {len(events)} SecretVerse events."
    )

    events_state = load_json(
        EVENTS_STATE_FILE,
        None
    )

    alerts_state = load_json(
        ALERTS_STATE_FILE,
        {}
    )

    current_ids = {
        str(event["id"])
        for event in events
    }

    # -------------------------
    # NEW EVENTS
    # -------------------------

    if events_state is None:

        save_json(
            EVENTS_STATE_FILE,
            {
                "event_ids": sorted(
                    current_ids
                )
            }
        )

        print(
            "First run: existing events saved."
        )

    else:

        old_ids = set(
            events_state.get(
                "event_ids",
                []
            )
        )

        new_events = [
            event
            for event in events
            if str(event["id"])
            not in old_ids
        ]

        new_events.sort(
            key=lambda event:
            event.get(
                "createdUtc",
                ""
            )
        )

        for event in new_events:

            send_new_event(event)

        save_json(
            EVENTS_STATE_FILE,
            {
                "event_ids": sorted(
                    current_ids
                )
            }
        )

        print(
            f"New events announced: "
            f"{len(new_events)}"
        )

    # -------------------------
    # EVENT ALERTS
    # -------------------------

    alerts_state = check_alerts(
        events,
        alerts_state
    )

    save_json(
        ALERTS_STATE_FILE,
        alerts_state
    )

    print("Alert system check completed.")


if __name__ == "__main__":
    main()
