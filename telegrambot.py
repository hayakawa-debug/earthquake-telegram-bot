import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import re

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FEED_URL = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"

LAST_EVENT_FILE = "last_event.txt"


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    r = requests.post(url, data=data)
    print("📤 Telegram API Response:", r.status_code, r.text)


def format_time(iso_time):
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        dt_jst = dt.astimezone(timezone(timedelta(hours=9)))
        return dt_jst.strftime("%H時%M分ごろ")
    except:
        return "不明"


def main():
    # 前回のイベントを読み込み
    last_event = None
    if os.path.exists(LAST_EVENT_FILE):
        with open(LAST_EVENT_FILE, "r", encoding="utf-8") as f:
            last_event = f.read().strip()

    r = requests.get(FEED_URL)
    r.encoding = "utf-8"
    root = ET.fromstring(r.text)

    ns = {
        "eb": "http://xml.kishou.go.jp/jmaxml1/body/seismology1/",
        "jmx_eb": "http://xml.kishou.go.jp/jmaxml1/elementBasis1/"
    }

    new_events = []
    found_last = False

    # FEEDの新しい順に取得
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = entry.find("{http://www.w3.org/2005/Atom}title").text
        link = entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]

        if not any(key in title for key in ["震源", "震度", "津波"]):
            continue

        detail_xml = requests.get(link)
        detail_xml.encoding = "utf-8"
        detail_root = ET.fromstring(detail_xml.text)

        origin_time = detail_root.findtext(".//eb:OriginTime", namespaces=ns)
        hypocenter = detail_root.findtext(".//eb:Hypocenter/eb:Area/eb:Name", namespaces=ns) or "不明"
        magnitude = detail_root.findtext(".//jmx_eb:Magnitude", namespaces=ns)

        depth = "不明"
        coord = detail_root.find(".//jmx_eb:Coordinate", namespaces=ns)
        if coord is not None and "description" in coord.attrib:
            desc = coord.attrib["description"]
            m = re.search(r"深さ　?([０-９0-9]+)ｋｍ", desc)
            if m:
                depth = m.group(1) + "km"
            else:
                if "ごく浅い" in desc:
                    depth = "ごく浅い"
                elif "不明" in desc:
                    depth = "不明"
                else:
                    depth = desc

        max_intensity = detail_root.findtext(".//eb:MaxInt", namespaces=ns) or "不明"

        event_key = f"{origin_time}-{hypocenter}"

        if event_key == last_event:
            found_last = True
            break

        # 新しい地震をリストに追加
        new_events.append({
            "event_key": event_key,
            "origin_time": origin_time,
            "hypocenter": hypocenter,
            "depth": depth,
            "magnitude": magnitude,
            "max_intensity": max_intensity,
            "link": link
        })

    # 新しいイベントを古い順に送信（時系列を守る）
    for ev in reversed(new_events):
        msg = (
            f"📢 地震情報\n"
            f"{format_time(ev['origin_time'])}、地震がありました。\n"
            f"震源地: {ev['hypocenter']}\n"
            f"震源の深さ: {ev['depth']}\n"
            f"マグニチュード: {ev['magnitude'] or '不明'}\n"
            f"最大震度: {ev['max_intensity']}\n"
            f"詳細: {ev['link']}"
        )
        send_telegram_message(msg)

    # 最後に処理したイベントを保存
    if new_events:
        with open(LAST_EVENT_FILE, "w", encoding="utf-8") as f:
            f.write(new_events[0]["event_key"])


if __name__ == "__main__":
    main()
