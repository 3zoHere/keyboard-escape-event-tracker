import json
import os
import requests
from datetime import datetime, timezone


# ============================================================
# SETTINGS
# ============================================================

GROUP_ID = "1074557114"
UNIVERSE_ID = "9584852943"

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]
CONTROL_WEBHOOK_URL = os.environ.get("CONTROL_WEBHOOK")

API_URL = (
    f"https://apis.roblox.com/virtual-events/v1/"
    f"universes/{UNIVERSE_ID}/virtual-events"
)

EVENTS_STATE_FILE = "events_state.json"
ALERTS_STATE_FILE = "alerts_state.json"
STATS_STATE_FILE = "stats_state.json"
CONTROL_STATE_FILE = "control_state.json"
EVENT_MESSAGES_STATE_FILE = "event_messages_state.json"

# Pink
EMBED_COLOR = 0xFF69B4


# ============================================================
# JSON
# ============================================================

def load_json(filename, default):

    if not os.path.exists(filename):
        return default

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            f"Could not load {filename}: {e}"
        )

        return default


def save_json(filename, data):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# STATS
# ============================================================

def default_stats():

    return {
        "runs": 0,
        "events_checked": 0,
        "new_events": 0,
        "notifications_sent": 0,
        "errors": 0,
        "last_run": None,
        "last_event": None,
        "last_run_events": 0
    }


# ============================================================
# ROBLOX EVENTS
# ============================================================

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

        events.extend(
            data.get("data", [])
        )

        cursor = data.get(
            "nextPageCursor"
        )

        if not cursor:
            break

    return events


# ============================================================
# TIME
# ============================================================

def parse_time(value):

    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def get_timestamp(value):

    parsed = parse_time(value)

    if not parsed:
        return None

    return int(
        parsed.timestamp()
    )


def format_time_remaining(start_time):

    now = datetime.now(
        timezone.utc
    )

    total_seconds = int(
        (
            start_time - now
        ).total_seconds()
    )

    if total_seconds <= 0:
        return "🔴 **الفعالية مباشرة الآن**"

    days = (
        total_seconds // 86400
    )

    hours = (
        total_seconds % 86400
    ) // 3600

    minutes = (
        total_seconds % 3600
    ) // 60

    return (
        f"**{days} يوم • "
        f"{hours} ساعة • "
        f"{minutes} دقيقة**"
    )


# ============================================================
# MESSAGE STATE
# ============================================================

def get_message_state():

    return load_json(
        EVENT_MESSAGES_STATE_FILE,
        {}
    )


def save_message_id(
    event_id,
    message_id
):

    state = get_message_state()

    state[str(event_id)] = {
        "message_id": str(message_id)
    }

    save_json(
        EVENT_MESSAGES_STATE_FILE,
        state
    )


# ============================================================
# EVENT EMBED
# ============================================================

def build_event_payload(
    event,
    message="",
    mention_everyone=False
):

    event_id = event["id"]

    title = (
        event.get("displayTitle")
        or event.get("title")
        or "فعالية Roblox"
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

    event_time = event.get(
        "eventTime",
        {}
    )

    start = event_time.get(
        "startUtc"
    )

    end = event_time.get(
        "endUtc"
    )

    event_url = (
        f"https://www.roblox.com/events/"
        f"{event_id}"
    )

    fields = []

    # --------------------------------------------------------
    # Description
    # --------------------------------------------------------

    if description:

        fields.append({
            "name": "📖 وصف الفعالية",
            "value": description[:1024],
            "inline": False
        })

    # --------------------------------------------------------
    # Details
    # --------------------------------------------------------

    if subtitle:

        fields.append({
            "name": "ℹ️ التفاصيل",
            "value": subtitle[:1024],
            "inline": False
        })

    # --------------------------------------------------------
    # Start + Countdown
    # --------------------------------------------------------

    if start:

        start_time = parse_time(start)
        start_timestamp = get_timestamp(start)

        if start_time and start_timestamp:

            fields.append({
                "name": "📅 موعد البداية",
                "value": f"<t:{start_timestamp}:F>",
                "inline": False
            })

            fields.append({
                "name": "⏳ الوقت المتبقي",
                "value": format_time_remaining(
                    start_time
                ),
                "inline": False
            })

    # --------------------------------------------------------
    # End
    # --------------------------------------------------------

    if end:

        end_timestamp = get_timestamp(end)

        if end_timestamp:

            fields.append({
                "name": "🏁 موعد الانتهاء",
                "value": f"<t:{end_timestamp}:F>",
                "inline": False
            })

    # --------------------------------------------------------
    # Roblox Link
    # --------------------------------------------------------

    fields.append({
        "name": "🔗 صفحة الفعالية",
        "value": (
            f"[اضغط هنا لفتح الفعالية]"
            f"({event_url})"
        ),
        "inline": False
    })

    # --------------------------------------------------------
    # Embed
    # --------------------------------------------------------

    embed = {

        "author": {
            "name": "🩷 SecretVerse Events"
        },

        "title": f"🎉 {title}",

        "url": event_url,

        "description": (
            "✨ **فعالية Roblox**\n\n"
            "تابع تفاصيل الفعالية "
            "وموعد بدايتها بالأسفل."
        ),

        "color": EMBED_COLOR,

        "fields": fields,

        "footer": {
            "text":
                "SecretVerse Roblox Events • يتحدث تلقائيًا"
        }
    }

    payload = {

        "username": "SecretVerse Events",

        "content": message,

        "embeds": [embed]

    }

    # --------------------------------------------------------
    # Allow @everyone
    # --------------------------------------------------------

    if mention_everyone:

        payload["allowed_mentions"] = {
            "parse": ["everyone"]
        }

    else:

        payload["allowed_mentions"] = {
            "parse": []
        }

    return payload


# ============================================================
# SEND DISCORD MESSAGE
# ============================================================

def send_to_discord(
    event,
    message,
    stats,
    mention_everyone=False
):

    payload = build_event_payload(
        event,
        message,
        mention_everyone
    )

    response = requests.post(

        f"{WEBHOOK_URL}?wait=true",

        json=payload,

        timeout=30

    )

    response.raise_for_status()

    data = response.json()

    message_id = data.get("id")

    if not message_id:

        raise RuntimeError(
            "Discord did not return message ID."
        )

    stats["notifications_sent"] += 1

    print(
        f"Discord message sent: "
        f"{message_id}"
    )

    return message_id


# ============================================================
# NEW EVENT
# ============================================================

def send_new_event(
    event,
    stats
):

    title = (
        event.get("displayTitle")
        or event.get("title")
        or "فعالية جديدة"
    )

    message = (
        "@everyone\n"
        "📢 **فعالية جديدة!**\n\n"
        f"🎉 **{title}**"
    )

    message_id = send_to_discord(
        event,
        message,
        stats,
        mention_everyone=True
    )

    save_message_id(
        event["id"],
        message_id
    )

    stats["new_events"] += 1
    stats["last_event"] = title

    print(
        f"New event announced: "
        f"{event['id']}"
    )


# ============================================================
# ALERTS
# ============================================================

def send_alert(
    event,
    alert_type,
    stats
):

    title = (
        event.get("displayTitle")
        or event.get("title")
        or "فعالية Roblox"
    )

    messages = {

        "1h": (
            "@everyone\n"
            "🟡 **تنبيه الفعالية**\n\n"
            f"🎉 **{title}**\n\n"
            "⏰ تبدأ الفعالية خلال "
            "**ساعة واحدة**!"
        ),

        "30m": (
            "@everyone\n"
            "🟠 **تنبيه الفعالية**\n\n"
            f"🎉 **{title}**\n\n"
            "⏰ تبدأ الفعالية خلال "
            "**30 دقيقة**!"
        ),

        "15m": (
            "@everyone\n"
            "🟠 **تنبيه الفعالية**\n\n"
            f"🎉 **{title}**\n\n"
            "⏰ تبدأ الفعالية خلال "
            "**15 دقيقة**!"
        ),

        "5m": (
            "@everyone\n"
            "🔴 **تنبيه الفعالية**\n\n"
            f"🎉 **{title}**\n\n"
            "🚨 تبدأ الفعالية خلال "
            "**5 دقائق**!"
        ),

        "start": (
            "@everyone\n"
            "🚨 **الفعالية بدأت الآن!**\n\n"
            f"🎉 **{title}**\n\n"
            "🔥 **ادخل الآن!**"
        )
    }

    message = messages.get(
        alert_type,
        "@everyone\n🔔 **تنبيه فعالية**"
    )

    send_to_discord(
        event,
        message,
        stats,
        mention_everyone=True
    )

    stats["last_event"] = title

    print(
        f"Sent {alert_type} alert "
        f"for event {event['id']}"
    )


# ============================================================
# CHECK ALERTS
# ============================================================

def check_alerts(
    events,
    alerts_state,
    stats
):

    now = datetime.now(
        timezone.utc
    )

    for event in events:

        event_id = str(
            event["id"]
        )

        event_time = event.get(
            "eventTime",
            {}
        )

        start = parse_time(
            event_time.get(
                "startUtc"
            )
        )

        end = parse_time(
            event_time.get(
                "endUtc"
            )
        )

        if not start:
            continue

        if end and now >= end:
            continue

        if event_id not in alerts_state:

            alerts_state[event_id] = []

        sent_alerts = (
            alerts_state[event_id]
        )

        seconds_until_start = (
            start - now
        ).total_seconds()

        # ====================================================
        # 1 HOUR
        # ====================================================

        if (
            "1h" not in sent_alerts
            and
            0 < seconds_until_start <= 3600
        ):

            send_alert(
                event,
                "1h",
                stats
            )

            sent_alerts.append("1h")

        # ====================================================
        # 30 MINUTES
        # ====================================================

        if (
            "30m" not in sent_alerts
            and
            0 < seconds_until_start <= 1800
        ):

            send_alert(
                event,
                "30m",
                stats
            )

            sent_alerts.append("30m")

        # ====================================================
        # 15 MINUTES
        # ====================================================

        if (
            "15m" not in sent_alerts
            and
            0 < seconds_until_start <= 900
        ):

            send_alert(
                event,
                "15m",
                stats
            )

            sent_alerts.append("15m")

        # ====================================================
        # 5 MINUTES
        # ====================================================

        if (
            "5m" not in sent_alerts
            and
            0 < seconds_until_start <= 300
        ):

            send_alert(
                event,
                "5m",
                stats
            )

            sent_alerts.append("5m")

        # ====================================================
        # START
        # ====================================================

        if (
            "start" not in sent_alerts
            and
            seconds_until_start <= 0
        ):

            send_alert(
                event,
                "start",
                stats
            )

            sent_alerts.append("start")

    return alerts_state


# ============================================================
# UPDATE EVENT MESSAGE
# ============================================================

def update_event_message(
    event
):

    state = get_message_state()

    event_id = str(
        event["id"]
    )

    if event_id not in state:

        print(
            f"No saved Discord message "
            f"for event {event_id}"
        )

        return

    message_id = (
        state[event_id].get(
            "message_id"
        )
    )

    if not message_id:
        return

    payload = build_event_payload(
        event,
        "",
        False
    )

    url = (
        f"{WEBHOOK_URL}"
        f"/messages/{message_id}"
    )

    try:

        response = requests.patch(
            url,
            json=payload,
            timeout=30
        )

        if response.status_code == 404:

            print(
                f"Discord message "
                f"{message_id} not found."
            )

            return

        response.raise_for_status()

        event_time = event.get(
            "eventTime",
            {}
        )

        start = parse_time(
            event_time.get(
                "startUtc"
            )
        )

        if start:

            print(
                f"Updated event "
                f"{event_id}: "
                f"{format_time_remaining(start)}"
            )

    except Exception as e:

        print(
            f"Failed to update event "
            f"{event_id}: {e}"
        )


# ============================================================
# UPDATE ALL COUNTDOWNS
# ============================================================

def update_all_countdowns(
    events
):

    print(
        "Updating event countdowns..."
    )

    for event in events:

        update_event_message(
            event
        )


# ============================================================
# CONTROL WEBHOOK
# ============================================================

def send_control_message(
    payload,
    wait=False
):

    if not CONTROL_WEBHOOK_URL:
        return None

    url = CONTROL_WEBHOOK_URL

    if wait:
        url += "?wait=true"

    response = requests.post(
        url,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    if wait:
        return response.json()

    return None


def edit_control_message(
    message_id,
    payload
):

    if (
        not CONTROL_WEBHOOK_URL
        or
        not message_id
    ):
        return False

    url = (
        f"{CONTROL_WEBHOOK_URL}"
        f"/messages/{message_id}"
    )

    response = requests.patch(
        url,
        json=payload,
        timeout=30
    )

    if response.status_code == 404:
        return False

    response.raise_for_status()

    return True


# ============================================================
# CONTROL LOG
# ============================================================

def send_control_log(
    title,
    description
):

    if not CONTROL_WEBHOOK_URL:
        return

    payload = {

        "username":
            "Roblox Bot Control",

        "embeds": [

            {

                "title":
                    title,

                "description":
                    description[:4096],

                "color":
                    EMBED_COLOR,

                "footer": {

                    "text":
                        "Private Bot Control"

                }

            }

        ]

    }

    try:

        send_control_message(
            payload
        )

    except Exception as e:

        print(
            f"Control log failed: {e}"
        )


# ============================================================
# CONTROL DASHBOARD
# ============================================================

def update_control_dashboard(
    stats,
    status,
    current_events
):

    if not CONTROL_WEBHOOK_URL:
        return

    control_state = load_json(

        CONTROL_STATE_FILE,

        {
            "dashboard_message_id":
                None
        }

    )

    status_text = {

        "online":
            "🟢 متصل",

        "error":
            "🔴 خطأ"

    }.get(
        status,
        "🟡 غير معروف"
    )

    last_run = (
        stats.get("last_run")
        or
        "لم يتم التشغيل بعد"
    )

    last_event = (
        stats.get("last_event")
        or
        "لا يوجد"
    )

    embed = {

        "title":
            "🤖 لوحة تحكم بوت الفعاليات",

        "description":
            "لوحة مراقبة خاصة للبوت",

        "color":
            EMBED_COLOR,

        "fields": [

            {
                "name": "الحالة",
                "value": status_text,
                "inline": True
            },

            {
                "name": "الفعاليات الحالية",
                "value": str(current_events),
                "inline": True
            },

            {
                "name": "مرات التشغيل",
                "value": str(stats["runs"]),
                "inline": True
            },

            {
                "name": "الفعاليات المفحوصة",
                "value": str(
                    stats["events_checked"]
                ),
                "inline": True
            },

            {
                "name": "فعاليات جديدة",
                "value": str(
                    stats["new_events"]
                ),
                "inline": True
            },

            {
                "name": "الإشعارات المرسلة",
                "value": str(
                    stats["notifications_sent"]
                ),
                "inline": True
            },

            {
                "name": "الأخطاء",
                "value": str(
                    stats["errors"]
                ),
                "inline": True
            },

            {
                "name": "آخر تشغيل",
                "value": last_run,
                "inline": False
            },

            {
                "name": "آخر فعالية",
                "value": last_event[:1024],
                "inline": False
            }

        ],

        "footer": {
            "text":
                "يتحدث كل دقيقة"
        }
    }

    payload = {

        "username":
            "Roblox Bot Control",

        "embeds":
            [embed]

    }

    message_id = control_state.get(
        "dashboard_message_id"
    )

    try:

        if message_id:

            if edit_control_message(
                message_id,
                payload
            ):
                return

        message = send_control_message(
            payload,
            wait=True
        )

        if (
            message
            and
            message.get("id")
        ):

            control_state[
                "dashboard_message_id"
            ] = message["id"]

            save_json(
                CONTROL_STATE_FILE,
                control_state
            )

    except Exception as e:

        print(
            f"Control dashboard update "
            f"failed: {e}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    stats = load_json(
        STATS_STATE_FILE,
        default_stats()
    )

    stats["runs"] += 1

    stats["last_run"] = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    try:

        # ----------------------------------------------------
        # GET EVENTS
        # ----------------------------------------------------

        events = get_events()

        # ----------------------------------------------------
        # SECRETVERSE ONLY
        # ----------------------------------------------------

        events = [

            event

            for event in events

            if str(
                event.get(
                    "host",
                    {}
                ).get(
                    "hostId"
                )
            ) == GROUP_ID

        ]

        stats[
            "last_run_events"
        ] = len(events)

        stats[
            "events_checked"
        ] += len(events)

        print(
            f"Found {len(events)} "
            f"SecretVerse events."
        )

        # ----------------------------------------------------
        # LOAD STATES
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # NEW EVENTS
        # ----------------------------------------------------

        if events_state is None:

            save_json(
                EVENTS_STATE_FILE,
                {
                    "event_ids":
                        sorted(current_ids)
                }
            )

            print(
                "First run: existing "
                "events saved."
            )

            send_control_log(
                "🟢 تم تشغيل البوت",
                (
                    "تم تشغيل البوت لأول مرة. "
                    f"تم العثور على "
                    f"**{len(events)}** "
                    "فعالية موجودة."
                )
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

                send_new_event(
                    event,
                    stats
                )

            save_json(
                EVENTS_STATE_FILE,
                {
                    "event_ids":
                        sorted(current_ids)
                }
            )

            print(
                f"New events announced: "
                f"{len(new_events)}"
            )

            if new_events:

                send_control_log(
                    "📢 تم اكتشاف فعالية جديدة",
                    (
                        "تم اكتشاف وإرسال "
                        f"**{len(new_events)}** "
                        "فعالية جديدة."
                    )
                )

        # ----------------------------------------------------
        # ALERTS
        # ----------------------------------------------------

        alerts_state = check_alerts(
            events,
            alerts_state,
            stats
        )

        save_json(
            ALERTS_STATE_FILE,
            alerts_state
        )

        # ----------------------------------------------------
        # UPDATE COUNTDOWNS
        # ----------------------------------------------------

        update_all_countdowns(
            events
        )

        # ----------------------------------------------------
        # SAVE STATS
        # ----------------------------------------------------

        save_json(
            STATS_STATE_FILE,
            stats
        )

        # ----------------------------------------------------
        # CONTROL DASHBOARD
        # ----------------------------------------------------

        update_control_dashboard(
            stats,
            "online",
            len(events)
        )

        print(
            "========================================"
        )

        print(
            "CHECK COMPLETED"
        )

        print(
            "========================================"
        )

    except Exception as e:

        stats["errors"] += 1

        save_json(
            STATS_STATE_FILE,
            stats
        )

        try:

            send_control_log(
                "🔴 خطأ في البوت",
                f"```{str(e)[:3500]}```"
            )

            update_control_dashboard(
                stats,
                "error",
                stats.get(
                    "last_run_events",
                    0
                )
            )

        except Exception as control_error:

            print(
                f"Control error: "
                f"{control_error}"
            )

        raise

    finally:

        save_json(
            STATS_STATE_FILE,
            stats
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
