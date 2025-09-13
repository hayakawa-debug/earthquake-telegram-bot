import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import re

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GIST_ID = os.getenv("GIST_ID")
GIST_TOKEN = os.getenv("GIST_TOKEN")

FEED_URL = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"


# --- Gist操作 ---
def get_last_event():
    url = f"https://api.github.com/gists/{GIST_ID}"
    r = requests.get(url, headers={"Authorization": f"token {GIST_TOKEN}"})
    r.raise_for_status()
    gist = r.json()
    return gist["files"]["last_event.txt"]["content"].strip()


def update_last_event(event_key):
    url = f"https://api.github.com/gists/{GIST_ID}"
    data = {
        "files": {
            "last_event.txt": {
                "content": event_key
            }
        }
    }
    r = requests.patch(url, headers={"Authorization": f"token {GIST_TOKEN}"}, json=data)
    r.raise_for_status()
    print(f"✅ Gist updated: {event_key}")


# --- Telegram送信 ---
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


# --- メイン処理 ---
def main():
    try:
        last_event = get_last_event()
    except Exception as e:
        print("⚠️ Gist取得失敗:", e)
        last_event = "NO_EVENT"

    r = requests.get(FEED_URL)
    r.encoding = "utf-8"
    root = ET.fromstring(r.text)

    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = entry.find("{http://www.w3.org/2005/Atom}title").text
        link = entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]

        if not any(key in title for key in ["震源", "震度", "津波"]):
            continue

        # 詳細XML取得
        detail_xml = requests.get(link)
        detail_xml.encoding = "utf-8"
        detail_root = ET.fromstring(detail_xml.text)

        ns = {
            "eb": "http://xml.kishou.go.jp/jmaxml1/body/seismology1/",
            "jmx_eb": "http://xml.kishou.go.jp/jmaxml1/elementBasis1/"
        }

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
            elif "ごく浅い" in desc:
                depth = "ごく浅い"
            elif "不明" in desc:
                depth = "不明"
            else:
                depth = desc

        max_intensity = detail_root.findtext(".//eb:MaxInt", namespaces=ns) or "不明"

        event_key = f"{origin_time}-{hypocenter}"

        # 同じイベントならスキップ
        if event_key == last_event:
            print("⚠️ 前回と同じ地震なので通知しません")
            return

        # 通知メッセージ
        msg = (
            f"📢 地震情報\n"
            f"{format_time(origin_time)}、地震がありました。\n"
            f"震源地: {hypocenter}\n"
            f"震源の深さ: {depth}\n"
            f"マグニチュード: {magnitude or '不明'}\n"
            f"最大震度: {max_intensity}\n"
            f"詳細: {link}"
        )

        send_telegram_message(msg)
        update_last_event(event_key)
        break  # 最新1件だけ処理


if __name__ == "__main__":
    main()
