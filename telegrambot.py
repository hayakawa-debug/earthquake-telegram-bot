import requests
import xml.etree.ElementTree as ET
import os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

ns = {
    "jmx": "http://xml.kishou.go.jp/jmaxml1/",
    "head": "http://xml.kishou.go.jp/jmaxml1/informationBasis1/",
    "body": "http://xml.kishou.go.jp/jmaxml1/body/seismology1/",
    "eb": "http://xml.kishou.go.jp/jmaxml1/elementBasis1/",
}

LAST_FILE = "last_event.txt"

def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})
    print(f"📤 Telegram API Response: {r.status_code} {r.text}")

def fetch_and_parse(url):
    res = requests.get(url)
    res.encoding = "utf-8"
    return ET.fromstring(res.text)

def get_last_event():
    if os.path.exists(LAST_FILE):
        with open(LAST_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_event(event_id):
    with open(LAST_FILE, "w") as f:
        f.write(event_id)

def main():
    feed_url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
    feed = requests.get(feed_url).text
    root = ET.fromstring(feed)

    latest_entry = root.find(".//{http://www.w3.org/2005/Atom}entry")
    if latest_entry is None:
        print("⚠️ entry が見つかりません")
        return

    eq_id = latest_entry.find("{http://www.w3.org/2005/Atom}id").text
    title = latest_entry.find("{http://www.w3.org/2005/Atom}title").text
    link = latest_entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]

    print(f"▶ タイトル: {title}")
    print(f"▶ ID: {eq_id}")
    print(f"▶ リンク: {link}")

    last_id = get_last_event()
    print(f"▶ 最終通知済み: {last_id}")

    if eq_id == last_id:
        print("⏩ すでに通知済みの地震です")
        return

    eq = fetch_and_parse(link)
    origin_time = eq.findtext(".//body:OriginTime", default="不明", namespaces=ns)
    hypocenter = eq.findtext(".//body:Hypocenter/body:Area/body:Name", default="不明", namespaces=ns)
    magnitude = eq.findtext(".//eb:Magnitude", default="不明", namespaces=ns)
    maxint = eq.findtext(".//body:Observation/body:MaxInt", default="不明", namespaces=ns)

    message = f"""📢 地震情報
{origin_time}ころ、地震がありました。
震源地: {hypocenter}
マグニチュード: {magnitude}
最大震度: {maxint}"""

    send_telegram_message(message)
    save_last_event(eq_id)

if __name__ == "__main__":
    main()
