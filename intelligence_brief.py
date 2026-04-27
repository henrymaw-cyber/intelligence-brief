import feedparser
import requests
from datetime import datetime, timedelta
import os

# =========================
# CONFIG
# =========================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =========================
# APIs
# =========================
WEATHER_API = "https://api.open-meteo.com/v1/forecast"
FX_API = "https://api.exchangerate-api.com/v4/latest/USD"
GOLD_API = "https://api.metals.live/v1/spot/gold"
NIKKEI_RSS = "https://asia.nikkei.com/rss/feed/nar"

# =========================
# DEDUP LOGIC
# =========================
def should_send():
    now = datetime.utcnow()
    minute = now.minute

    # Only allow sending close to minute 30
    return 28 <= minute <= 32

# =========================
# WEATHER ICONS
# =========================
def weather_icon(code):
    if code == 0:
        return "☀️"
    elif code in [1, 2]:
        return "⛅"
    elif code == 3:
        return "☁️"
    elif code in [45, 48]:
        return "🌫️"
    elif code in [51, 53, 55, 61, 63, 65]:
        return "🌧️"
    else:
        return "🌤️"

# =========================
# DATA FETCHERS
# =========================
def get_gold():
    try:
        d = requests.get(GOLD_API).json()
        return f"${d[0]['price']}/oz"
    except:
        return "N/A"

def get_fx():
    try:
        d = requests.get(FX_API).json()
        return f"{d['rates']['THB']:.2f}", f"{d['rates']['SGD']:.2f}"
    except:
        return "N/A", "N/A"

def get_weather(lat, lon):
    try:
        r = requests.get(WEATHER_API, params={
            "latitude": lat,
            "longitude": lon,
            "current_weather": True
        }).json()

        return f"{weather_icon(r['current_weather']['weathercode'])} {r['current_weather']['temperature']}°C"
    except:
        return "N/A"

def get_oil():
    try:
        r = requests.get("https://api.metals.live/v1/spot/brent")
        return f"${r.json()[0]['price']}/bbl"
    except:
        return "N/A"

def get_fed():
    return "Markets pricing ~1-2 cuts → easing liquidity, supportive for risk assets & VC funding"

# =========================
# NIKKEI HEADLINES
# =========================
def get_nikkei_trending():
    feed = feedparser.parse(NIKKEI_RSS)

    headlines = []
    for entry in feed.entries:
        title = entry.title.strip()

        if len(title) < 40:
            continue

        headlines.append(title)

        if len(headlines) >= 5:
            break

    if not headlines:
        return ["No Nikkei headlines available"]

    return headlines

# =========================
# EVENTS (NEXT 30 DAYS)
# =========================
def get_events():
    today = datetime.now()
    cutoff = today + timedelta(days=30)

    raw_events = [
        {
            "name": "GITEX Asia",
            "date": datetime(2026, 4, 23),
            "end_date": datetime(2026, 4, 25),
            "city": "Singapore"
        },
        {
            "name": "ASEAN Finance Ministers Meeting",
            "date": datetime(2026, 5, 10),
            "end_date": datetime(2026, 5, 12),
            "city": "Kuala Lumpur, Malaysia"
        },
        {
            "name": "Techsauce Global Summit",
            "date": datetime(2026, 8, 26),
            "end_date": datetime(2026, 8, 28),
            "city": "Bangkok, Thailand"
        }
    ]

    filtered = []

    for e in raw_events:
        if today <= e["date"] <= cutoff:
            formatted = f"{e['name']} — {e['date'].strftime('%d %b')} to {e['end_date'].strftime('%d %b %Y')} — {e['city']}"
            filtered.append(formatted)

    if not filtered:
        return ["No major ASEAN events in next 30 days"]

    return filtered

# =========================
# TELEGRAM
# =========================
def send(msg):
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }
    )
    print(r.text)

# =========================
# MAIN
# =========================
def main():
    if not should_send():
        print("Skipped send (outside target minute window)")
        return

    today_str = datetime.now().strftime("%Y-%m-%d")

    gold = get_gold()
    thb, sgd = get_fx()
    oil = get_oil()
    fed = get_fed()

    bangkok = get_weather(13.7563, 100.5018)
    yangon = get_weather(16.8661, 96.1951)

    nikkei = get_nikkei_trending()
    events = get_events()

    msg = f"*__Daily SEA Intelligence Stack — {today_str}__*\n\n"

    msg += "*__MARKETS__*\n"
    msg += f"Gold: {gold}\n"
    msg += f"Brent: {oil}\n"
    msg += f"USD/THB: {thb}\n"
    msg += f"USD/SGD: {sgd}\n"
    msg += f"Fed Outlook: {fed}\n\n"

    msg += "*__WEATHER__*\n"
    msg += f"Bangkok: {bangkok}\n"
    msg += f"Yangon: {yangon}\n\n"

    msg += "*__ASEAN EVENTS (NEXT 30 DAYS)__*\n"
    for e in events:
        msg += f"- {e}\n"
    msg += "\n"

    msg += "*__TOP HEADLINES (Nikkei Asia)__*\n"
    for h in nikkei:
        msg += f"- {h}\n"
    msg += "\n"

    msg += "— End —"

    send(msg)

if __name__ == "__main__":
    main()