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

LAST_ID_FILE = "last_id.txt"

def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def fetch_and_parse(url):
    res = requests.get(url)
    res.encoding = "utf-8"
    return ET.fromstring(res.text)

def get_last_id():
    if os.path.exists(LAST_ID_FILE):
        with open(LAST_ID_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_id(eq_id):
    with open(LAST_ID_FILE, "w") as f:
        f.write(eq_id)

def main():
    feed_url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
    feed = requests.get(feed_url).text
    root = ET.fromstring(feed)

    # 最新 entry を取得
    latest_entry = root.find(".//{http://www.w3.org/2005/Atom}entry")
    if latest_entry is None:
        return

    eq_id = latest_entry.find("{http://www.w3.org/2005/Atom}id").text
    title = latest_entry.find("{http://www.w3.org/2005/Atom}title").text

    last_id = get_last_id()
    if eq_id == last_id:
        print("⏩ すでに通知済みの地震です")
        return

    link = latest_entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]
    eq = fetch_and_parse(link)

    # 共通データ
    origin_time = eq.findtext(".//body:OriginTime", default="不明", namespaces=ns)
    hypocenter = eq.findtext(".//body:Hypocenter/body:Area/body:Name", default="不明", namespaces=ns)
    maxint = eq.findtext(".//body:Observation/body:MaxInt", default="不明", namespaces=ns)
    magnitude = eq.findtext(".//eb:Magnitude", default="不明", namespaces=ns)

    # ✅ 震度速報か通常かでメッセージ切り替え
    if "震度速報" in title:
        message = f"""📢 震度速報
{origin_time}ころ、地震がありました。
震源地: {hypocenter}
最大震度: {maxint}"""
    else:
        coord = eq.findtext(".//body:Hypocenter/body:Area/eb:Coordinate", default="", namespaces=ns)
        depth = "不明"
        if coord and "-" in coord:
            try:
                depth_val = coord.split("-")[-1].replace("/", "")
                depth = f"{int(depth_val) // 1000} km"
            except:
                pass

        message = f"""📢 地震情報
発生時刻: {origin_time}
震源地: {hypocenter}
深さ: {depth}
マグニチュード: {magnitude}
最大震度: {maxint}"""

    send_telegram_message(message)
    save_last_id(eq_id)  # ✅ 通知済みに保存

if __name__ == "__main__":
    main()
