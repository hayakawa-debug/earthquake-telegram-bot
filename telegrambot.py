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

        # 地震と津波以外はスキップ
        if not any(key in title for key in ["震源", "震度", "津波"]):
            print(f"⚠️ スキップ: {title}")
            continue

        detail_xml = requests.get(link)
        detail_xml.encoding = "utf-8"
        detail_root = ET.fromstring(detail_xml.text)

        origin_time = detail_root.findtext(".//{http://xml.kishou.go.jp/jmaxml1/body/seismology1/}OriginTime")
        mag = detail_root.findtext(".//{http://xml.kishou.go.jp/jmaxml1/body/seismology1/}jmx_eb:Magnitude")
        depth = detail_root.findtext(".//{http://xml.kishou.go.jp/jmaxml1/body/seismology1/}jmx_eb:Hypocenter//jmx_eb:Depth")
        max_intensity = detail_root.findtext(".//{http://xml.kishou.go.jp/jmaxml1/body/seismology1/}jmx_eb:MaxInt")

        event_key = f"{origin_time}-{title}"

        print(f"▶ タイトル: {title}")
        print(f"▶ 発生時刻: {origin_time}")
        print(f"▶ イベントキー: {event_key}")
        print(f"▶ 最終通知済み: {last_event}")

        if event_key == last_event:
            print("⚠️ 同じイベントのためスキップ")
            continue

        # メッセージ作成
        message = (
            "📢 地震情報\n"
            f"{format_time(origin_time)}ころ、地震がありました。\n"
            f"震源地: {depth or '不明'}\n"
            f"マグニチュード: {mag or '不明'}\n"
            f"最大震度: {max_intensity or '不明'}\n"
            f"詳細: {link}"
        )

        send_telegram_message(message)

        # 最後の通知を保存
        with open(LAST_EVENT_FILE, "w", encoding="utf-8") as f:
            f.write(event_key)

        break  # 最新の1件だけ処理

if __name__ == "__main__":
    main()
