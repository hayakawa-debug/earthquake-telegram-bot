import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import re

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
            "eb": "http://xml.kishou.go.jp/jmaxml1/body/seismology1/",
            "jmx_eb": "http://xml.kishou.go.jp/jmaxml1/elementBasis1/"
        }

        # 発生時刻
        origin_time = detail_root.findtext(".//eb:OriginTime", namespaces=ns)

        # 震源地
        hypocenter = detail_root.findtext(".//eb:Hypocenter/eb:Area/eb:Name", namespaces=ns) or "不明"

        # マグニチュード
        magnitude = detail_root.findtext(".//jmx_eb:Magnitude", namespaces=ns)

                # 深さ
        depth = "不明"
        coord = detail_root.find(".//jmx_eb:Coordinate", namespaces=ns)
        if coord is not None and "description" in coord.attrib:
            desc = coord.attrib["description"]

            # 「深さ 10km」パターン
            m = re.search(r"深さ　?([０-９0-9]+)ｋｍ", desc)
            if m:
                depth = m.group(1) + "km"
            else:
                # 「ごく浅い」「深さ不明」など文字だけの場合
                if "ごく浅い" in desc:
                    depth = "ごく浅い"
                elif "不明" in desc:
                    depth = "不明"
                else:
                    depth = desc  # そのまま残す
            
        # 最大震度
        max_intensity = detail_root.findtext(".//eb:MaxInt", namespaces=ns) or "不明"

        # イベントキー = 発生時刻+震源地
        event_key = f"{origin_time}-{hypocenter}"

        # 前回と同じイベントならスキップ
        if event_key == last_event:
            print("⚠️ 前回と同じ地震なので通知しません")
            return

        # メッセージ作成
        msg = f"📢 地震情報\n{format_time(origin_time)}、地震がありました。\n震源地: {hypocenter}\n震源の深さ: {depth}\nマグニチュード: {magnitude or '不明'}\n最大震度: {max_intensity}\n詳細: {link}"

        send_telegram_message(msg)

        # 今回のイベントを保存
        with open(LAST_EVENT_FILE, "w", encoding="utf-8") as f:
            f.write(event_key)

        break  # 最新の1件だけ処理


if __name__ == "__main__":
    main()


