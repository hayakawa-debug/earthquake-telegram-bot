import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import re

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FEED_URL = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
LAST_EVENT_FILE = "last_event.txt"


def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    r = requests.post(url, data=data)
    print("📤 Telegram API Response:", r.status_code, r.text)


def format_time(iso_time: str):
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        dt_jst = dt.astimezone(timezone(timedelta(hours=9)))
        return dt_jst.strftime("%H時%M分ごろ")
    except Exception:
        return "不明"


def load_last_event_id():
    if os.path.exists(LAST_EVENT_FILE):
        with open(LAST_EVENT_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


def save_last_event_id(event_id: str):
    with open(LAST_EVENT_FILE, "w", encoding="utf-8") as f:
        f.write(event_id)


def main():
    last_event_id = load_last_event_id()
    print("📂 前回イベントID:", last_event_id)

    response = requests.get(FEED_URL)
    response.encoding = "utf-8"
    root = ET.fromstring(response.text)

    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        # ID
        entry_id_elem = entry.find("{http://www.w3.org/2005/Atom}id")
        if entry_id_elem is None:
            print("⚠️ entry に <id> が見つかりません")
            continue
        entry_id = entry_id_elem.text.strip()
        print("🆔 今回の entry_id:", entry_id)

        # タイトル
        title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
        title = title_elem.text if title_elem is not None else ""

        # リンク
        link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
        link = link_elem.attrib.get("href") if link_elem is not None else ""

        # 地震以外はスキップ
        if not any(key in title for key in ["震源", "震度", "津波"]):
            continue

        # 前回と同じならスキップ
        if entry_id == last_event_id:
            print("⚠️ このイベントは前回通知済み → スキップ:", entry_id)
            return

        # 詳細XMLを取得
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

        # 深さ
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

        # メッセージ作成
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

        # イベントIDを保存
        save_last_event_id(entry_id)
        print("✅ 保存した entry_id:", entry_id)

        break  # 最新1件だけ通知


if __name__ == "__main__":
    main()
