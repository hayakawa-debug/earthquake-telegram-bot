import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GIST_ID = os.getenv("GIST_ID")
GIST_TOKEN = os.getenv("GIST_TOKEN")

FEED_URL = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"

LAST_EVENT_FILE = "last_event.txt"


def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    r = requests.post(url, data=data)
    print("📤 Telegram API Response:", r.status_code, r.text)


def format_time(iso_time):
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        dt_jst = dt.astimezone(timezone(timedelta(hours=9)))
        return dt_jst.strftime("%H時%M分ごろ")
    except Exception:
        return "不明"


def load_last_event():
    """Gist から最後のイベント ID を取得"""
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {"Authorization": f"token {GIST_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        files = r.json().get("files", {})
        if LAST_EVENT_FILE in files:
            return files[LAST_EVENT_FILE]["content"].strip()
    return "NO_EVENT"


def save_last_event(event_id: str):
    """Gist に最後のイベント ID を保存"""
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {"Authorization": f"token {GIST_TOKEN}"}
    data = {
        "files": {
            LAST_EVENT_FILE: {
                "content": event_id
            }
        }
    }
    r = requests.patch(url, headers=headers, json=data)
    print("✅ 保存した entry_id:", event_id)
    print("📂 Gist 更新 Response:", r.status_code, r.text)


def main():
    last_event = load_last_event()
    print("📂 前回イベントID:", last_event)

    r = requests.get(FEED_URL)
    r.encoding = "utf-8"
    root = ET.fromstring(r.text)

    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = entry.find("{http://www.w3.org/2005/Atom}title").text
        link = entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]

        # 🔍 VXSE53（地震情報）のみ通知
        if not link.endswith(".xml") or "VXSE53" not in link:
            continue

        entry_id = link
        print("🆔 今回の entry_id:", entry_id)

        if entry_id == last_event:
            print("⚠️ 前回と同じ地震なので通知しません")
            return

        # 詳細 XML を取得
        detail_xml = requests.get(link)
        detail_xml.encoding = "utf-8"
        detail_root = ET.fromstring(detail_xml.text)

        ns = {
            "eb": "http://xml.kishou.go.jp/jmaxml1/body/seismology1/",
            "jmx_eb": "http://xml.kishou.go.jp/jmaxml1/elementBasis1/"
        }

        origin_time = detail_root.findtext(".//eb:OriginTime", namespaces=ns)
        hypocenter = detail_root.findtext(".//eb:Hypocenter/eb:Area/eb:Name", namespaces=ns) or "不明"
        magnitude = detail_root.findtext(".//jmx_eb:Magnitude", namespaces=ns) or "不明"
        max_intensity = detail_root.findtext(".//eb:MaxInt", namespaces=ns) or "不明"

        # 震源の深さ
        depth = "不明"
        coord = detail_root.find(".//jmx_eb:Coordinate", namespaces=ns)
        if coord is not None and "description" in coord.attrib:
            desc = coord.attrib["description"]
            if "ごく浅い" in desc:
                depth = "ごく浅い"
            elif "不明" in desc:
                depth = "不明"
            else:
                depth = desc.replace("　", "").replace("ｋｍ", "km")

        # メッセージ作成
        msg = (
            f"📢 地震情報\n"
            f"{format_time(origin_time)}、地震がありました。\n"
            f"震源地: {hypocenter}\n"
            f"震源の深さ: {depth}\n"
            f"マグニチュード: {magnitude}\n"
            f"最大震度: {max_intensity}\n"
            f"詳細: {link}"
        )

        send_telegram_message(msg)
        save_last_event(entry_id)
        break  # 最新の1件だけ処理


if __name__ == "__main__":
    main()
