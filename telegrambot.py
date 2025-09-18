import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import re

# Telegram 設定
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# JMA フィード
FEED_URL = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"

# Gist 設定
GIST_ID = os.getenv("GIST_ID")
GIST_TOKEN = os.getenv("GIST_TOKEN")  # repo gist 権限付き PAT

HEADERS = {"Authorization": f"token {GIST_TOKEN}"}


def send_telegram_message(message):
    """Telegramへ通知"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    r = requests.post(url, data=data)
    print("📤 Telegram API Response:", r.status_code, r.text)


def format_time(iso_time):
    """ISO8601 → 日本時間に変換"""
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        dt_jst = dt.astimezone(timezone(timedelta(hours=9)))
        return dt_jst.strftime("%H時%M分")
    except:
        return "不明"


def load_last_event():
    """Gist から最後のイベントIDを取得"""
    url = f"https://api.github.com/gists/{GIST_ID}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    files = r.json().get("files", {})
    if "last_event.txt" in files:
        return files["last_event.txt"]["content"].strip()
    return "NO_EVENT"


def save_last_event(event_id):
    """最後のイベントIDを Gist に保存"""
    url = f"https://api.github.com/gists/{GIST_ID}"
    payload = {"files": {"last_event.txt": {"content": event_id}}}
    r = requests.patch(url, headers=HEADERS, json=payload)
    r.raise_for_status()
    print("✅ 保存した entry_id:", event_id)


def main():
    last_event = load_last_event()
    print("📂 前回イベントID:", last_event)

    # フィード取得
    r = requests.get(FEED_URL)
    r.encoding = "utf-8"
    root = ET.fromstring(r.text)

    entries = []
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        link = entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]
        if "VXSE53" in link:  # ✅ 地震情報のみ
            entries.append(link)

    if not entries:
        print("⚠️ 地震情報は見つかりませんでした")
        return

    # 新しいものを古い順に通知
    entries.reverse()

    new_events = []
    found_last = (last_event == "NO_EVENT")

    for entry_id in entries:
        if not found_last:
            if entry_id == last_event:
                found_last = True
            continue

        # 新しい地震を通知
        print("🆔 新規 entry_id:", entry_id)
        new_events.append(entry_id)

    if not new_events:
        print("⚠️ 新しい地震はありません")
        return

    for entry_id in new_events:
        detail_xml = requests.get(entry_id)
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
            else:
                if "ごく浅い" in desc:
                    depth = "ごく浅い"
                elif "不明" in desc:
                    depth = "不明"
                else:
                    depth = desc
        max_intensity = detail_root.findtext(".//eb:MaxInt", namespaces=ns) or "不明"

        msg = (
            f"📢 地震情報\n"
            f"{format_time(origin_time)}ごろ、地震がありました。\n"
            f"最大震度: {max_intensity}\n"
            f"震源地: {hypocenter}\n"
            f"マグニチュード: {magnitude or '不明'}\n"
            f"震源の深さ: {depth}\n"
            f"詳細: {entry_id}"
        )

        send_telegram_message(msg)

    # 最後の地震を保存
    save_last_event(new_events[-1])


if __name__ == "__main__":
    main()



