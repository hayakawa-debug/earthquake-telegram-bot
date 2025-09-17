import os
import requests
import xml.etree.ElementTree as ET

# Secretsから取得
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GIST_ID = os.environ["GIST_ID"]
GIST_TOKEN = os.environ["GIST_TOKEN"]

FEED_URL = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
GIST_API = f"https://api.github.com/gists/{GIST_ID}"

def get_last_event_from_gist():
    """Gistからlast_event.txtを取得"""
    headers = {"Authorization": f"token {GIST_TOKEN}"}
    res = requests.get(GIST_API, headers=headers)
    res.raise_for_status()
    gist_data = res.json()
    return gist_data["files"]["last_event.txt"]["content"].strip()

def save_last_event_to_gist(event_id):
    """last_event.txtをGistに保存"""
    headers = {"Authorization": f"token {GIST_TOKEN}"}
    payload = {
        "files": {
            "last_event.txt": {
                "content": event_id
            }
        }
    }
    res = requests.patch(GIST_API, headers=headers, json=payload)
    res.raise_for_status()

def fetch_latest_event():
    """地震フィードから最新イベントを取得"""
    res = requests.get(FEED_URL)
    res.raise_for_status()
    root = ET.fromstring(res.content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        return None, None
    event_id = entry.find("atom:id", ns).text
    link = entry.find("atom:link", ns).attrib["href"]
    return event_id, link

def parse_earthquake_detail(url):
    """詳細XMLを解析して通知文を作成"""
    res = requests.get(url)
    res.raise_for_status()
    res.encoding = "utf-8"
    root = ET.fromstring(res.content)

    ns = {"jmx": "http://xml.kishou.go.jp/jmaxml1/"}
    info = root.find(".//jmx:Body//jmx:Earthquake", ns)
    if info is None:
        return None

    hypocenter = info.find(".//jmx:Hypocenter//jmx:Area//jmx:Name", ns).text
    depth = info.find(".//jmx:Hypocenter//jmx:Area//jmx:Coordinate/jmx:Depth", ns)
    depth = depth.text if depth is not None else "不明"
    mag = info.find(".//jmx:jmx_eb:Magnitude", {"jmx_eb": "http://xml.kishou.go.jp/jmaxml1/body/seismology1/"}).text
    origin_time = info.find(".//jmx:OriginTime", ns).text

    text = (
        f"📢 地震情報\n"
        f"{origin_time} ごろ、地震がありました。\n"
        f"震源地: {hypocenter}\n"
        f"震源の深さ: {depth}\n"
        f"マグニチュード: {mag}\n"
        f"詳細: {url}"
    )
    return text

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    res = requests.post(url, data=payload)
    res.raise_for_status()

def main():
    try:
        last_event = get_last_event_from_gist()
    except Exception:
        last_event = "NO_EVENT"

    event_id, link = fetch_latest_event()
    if not event_id or event_id == last_event:
        print("新しい地震はありません")
        return

    message = parse_earthquake_detail(link)
    if message:
        send_telegram(message)
        save_last_event_to_gist(event_id)
        print(f"通知を送信しました: {event_id}")

if __name__ == "__main__":
    main()
