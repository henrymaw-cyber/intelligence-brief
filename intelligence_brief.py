import feedparser
import requests
from datetime import datetime, timedelta
import os
import json

# =========================
# CONFIG
# =========================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

STATE_FILE = "send_state.json"

# =========================
# LOAD / SAVE STATE
# =========================
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# =========================
# SEND LOGIC (DEDUP + FAILSAFE)
# =========================
def should_send():
    now = datetime.utcnow()
    minute = now.minute
    hour = now.hour
    today = now.strftime("%Y-%m-%d")

    state = load_state()

    # Identify window
    if hour == 2:  # Morning (Thailand 9:30)
        key = f"{today}_morning"

        # Normal send window
        if 28 <= minute <= 32:
            if not state.get(key):
                state[key] = True
                save_state(state)
                return True

        # Failsafe window
        if 33 <= minute <= 40:
            if not state.get(key):
                print("⚠️ Failsafe triggered (morning)")
                state[key] = True
                save_state(state)
                return True

    elif hour == 10:  # Evening (Thailand 5:30)
        key = f"{today}_evening"

        if 28 <= minute <= 32:
            if not state.get(key):
                state[key] = True
                save_state(state)
                return True

        if 33 <= minute <= 40:
            if not state.get(key):
                print("⚠️ Failsafe triggered (evening)")
                state[key] = True
                save_state(state)
                return True

    return False

# =========================
# APIs
# =========================
WEATHER_API = "https://api.open-meteo.com/v1/forecast"
FX_API = "https://api.exchangerate-api.com/v4/latest/USD"
GOLD_API = "https://api.metals.live/v1/spot/gold"
NIKKEI_RSS = "https://asia.nikkei.com/rss/feed/nar"

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
# DATA
# =========================
def get_gold():
    try:
        return f"${requests.get(GOLD_API).json()[0]['price']}/oz"
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
        return f"${requests.get('https://api.metals.live/v1/spot/brent').json()[0]['price']}/bbl"
    except:
        return "N/A"

def get_fed():
    return "Markets pricing ~1-2 cuts → easing liquidity, supportive for risk assets & VC funding"

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

    return headlines or ["No Nikkei headlines available"]

def get_events():
    today = datetime.now()
    cutoff = today + timedelta(days=30)

    raw = [
        ("ASEAN Finance Ministers Meeting", datetime(2026,5,10), datetime(2026,5,12), "Kuala Lumpur"),
    ]

    events = []
    for name, d1, d2, city in raw:
        if today <= d1 <= cutoff:
            events.append(f"{name} — {d1.strftime('%d %b')} to {d2.strftime('%d %b %Y')} — {city}")

    return events or ["No major ASEAN events in next 30 days"]

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
        print("Skipped send")
        return

    today = datetime.now().strftime("%Y-%m-%d")

    gold = get_gold()
    thb, sgd = get_fx()
    oil = get_oil()
    fed = get_fed()

    bangkok = get_weather(13.7563, 100.5018)
    yangon = get_weather(16.8661, 96.1951)

    nikkei = get_nikkei_trending()
    events = get_events()

    msg = f"*__Daily SEA Intelligence Stack — {today}__*\n\n"

    msg += "*__MARKETS__*\n"
    msg += f"Gold: {gold}\nBrent: {oil}\nUSD/THB: {thb}\nUSD/SGD: {sgd}\nFed: {fed}\n\n"

    msg += "*__WEATHER__*\n"
    msg += f"Bangkok: {bangkok}\nYangon: {yangon}\n\n"

    msg += "*__EVENTS__*\n"
    for e in events:
        msg += f"- {e}\n"

    msg += "\n*__HEADLINES__*\n"
    for h in nikkei:
        msg += f"- {h}\n"

    send(msg)

if __name__ == "__main__":
    main()