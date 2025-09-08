import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LAST_EVENT_FILE = "last_event.txt"

FEED_URL = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"


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
    last_event = None
    if os.path.exists(LAST_EVENT_FILE):
        with open(LAST_EVENT_FILE, "r", encoding="utf-8") as f:
            last_event = f.read().strip()

    r = requests.get(FEED_URL)
    r.encoding = "utf-8"
    root = ET.fromstring(r.text)

    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = entry.find("{http://www.w3.org/2005/Atom}title").text
        link = entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]

        if not any(key in title for key in ["震源", "震度", "津波"]):
            continue

        detail_xml = requests.get(link)
        detail_xml.encoding = "utf-8"
        detail_root = ET.fromstring(detail_xml.text)

        ns = {
            "jmx": "http://xml.kishou.go.jp/jmaxml1/",
            "eb": "http://xml.kishou.go.jp/jmaxml1/body/seismology1/",
            "jmx_eb": "http://xml.kishou.go.jp/jmaxml1/elementBasis1/"
        }

        # 震源地
        hypocenter = root.findtext(".//eb:Hypocenter/eb:Area/eb:Name", namespaces=ns)

        # マグニチュード
        magnitude = root.findtext(".//jmx_eb:Magnitude", namespaces=ns)

        # 深さ（description を読む）
        coord = root.find(".//jmx_eb:Coordinate", namespaces=ns)
        depth = None
        if coord is not None and "description" in coord.attrib:
            desc = coord.attrib["description"]
            # 「深さ　１０ｋｍ」を抜き出す
            import re
            m = re.search(r"深さ　?([０-９0-9]+)ｋｍ", desc)
            if m:
                depth = m.group(1) + "km"

        print("震源地:", hypocenter)
        print("マグニチュード:", magnitude)
        print("深さ:", depth)
        max_intensity = detail_root.findtext(".//eb:MaxInt", namespaces=ns) or "不明"

        # 速報には深さやマグニチュードが無い場合あり
        if not depth and "震度速報" in title:
            depth = "未解析"
        elif not depth:
            depth = "不明"

        if not magnitude and "震度速報" in title:
            magnitude= "未解析"
        elif not magnitude:
            magnitude= "不明"

        # event_key 修正
        event_key = f"{origin_time}-{hypocenter_name}"

        if event_key == last_event:
            print("⚠️ 同じイベントのためスキップ")
            continue

        message = (
            "📢 地震情報\n"
            f"{format_time(origin_time)}、地震がありました。\n"
            f"震源地: {hypocenter_name}\n"
            f"震源の深さ: {depth}\n"
            f"マグニチュード: {magnitude}\n"
            f"最大震度: {max_intensity}\n"
            f"詳細: {link}"
        )

        send_telegram_message(message)

        with open(LAST_EVENT_FILE, "w", encoding="utf-8") as f:
            f.write(event_key)

        break  # 最新の1件だけ処理


if __name__ == "__main__":
    main()

import requests

url = "https://www.data.jma.go.jp/developer/xml/data/20250907065553_0_VXSE53_010000.xml"
r = requests.get(url)
r.encoding = "utf-8"

with open("sample.xml", "w", encoding="utf-8") as f:
    f.write(r.text)

print("Saved as sample.xml")









