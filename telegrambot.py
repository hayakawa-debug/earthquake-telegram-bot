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

LAST_EVENT_FILE = "last_event.txt"

def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def fetch_and_parse(url):
    res = requests.get(url)
    res.encoding = "utf-8"
    return ET.fromstring(res.text)

def parse_depth(coord_text: str) -> str:
    if coord_text and "-" in coord_text:
        try:
            depth_val = coord_text.split("-")[-1].replace("/", "")
            km = int(depth_val) // 1000
            return f"{km}km" if km > 0 else "ごく浅い"
        except:
            return "不明"
    return "不明"

def get_last_event():
    if os.path.exists(LAST_EVENT_FILE):
        with open(LAST_EVENT_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_event(event_key):
    with open(LAST_EVENT_FILE, "w") as f:
        f.write(event_key)

def format_time(origin_time: str) -> str:
    """2025-09-03T11:36:00+09:00 → 11時36分"""
    if "T" in origin_time:
        try:
            time_part = origin_time.split("T")[1]
            hm = time_part.split("+")[0].split(":")
            return f"{int(hm[0])}時{hm[1]}分"
        except:
            return origin_time
    return origin_time

def main():
    feed_url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
    feed = requests.get(feed_url).text
    root = ET.fromstring(feed)

    latest_entry = root.find(".//{http://www.w3.org/2005/Atom}entry")
    if latest_entry is None:
        return

    title = latest_entry.find("{http://www.w3.org/2005/Atom}title").text
    link = latest_entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]
    eq = fetch_and_parse(link)

    eq_tag = eq.find(".//body:Earthquake", ns)
    if eq_tag is None:
        return

    # 発生時刻
    origin_time = eq.findtext(".//body:OriginTime", default="不明", namespaces=ns)
    display_time = format_time(origin_time)

    # 震源地
    hypocenter = eq.findtext(".//body:Hypocenter/body:Area/body:Name", default="不明", namespaces=ns)

    # イベント識別キー（速報・詳細共通）
    event_key = f"{origin_time}_{hypocenter}"

    last_event = get_last_event()

    # ✅ 速報なら通知（ただし同じ速報はスキップ）
    if "震度速報" in title:
        if event_key == last_event:
            print("⏩ 速報はすでに通知済み")
            return
        maxint = eq.findtext(".//body:Observation/body:MaxInt", default="不明", namespaces=ns)
        message = f"""📢 震度速報

{display_time}ころ、震度{maxint}の地震がありました。"""
        send_telegram_message(message)
        save_last_event(event_key)
        print("✅ 速報を通知:", event_key)
        return

    # ✅ 詳細なら速報を上書き（すでに詳細を送っていたらスキップ）
    if "地震情報" in title:
        if event_key == last_event:
            print("⏩ この地震の詳細はすでに通知済み")
            return

        coord = eq.findtext(".//body:Hypocenter/body:Area/eb:Coordinate", default="", namespaces=ns)
        depth = parse_depth(coord)
        mag_tag = eq.find(".//eb:Magnitude", ns)
        magnitude = mag_tag.get("description") if mag_tag is not None else "不明"
        maxint = eq.findtext(".//body:Observation/body:MaxInt", default="不明", namespaces=ns)

        message = f"""📢 地震情報（詳細）

{display_time}ころ、震度{maxint}の地震がありました。
震源地: {hypocenter}
深さ: {depth}
マグニチュード: {magnitude}"""
        send_telegram_message(message)
        save_last_event(event_key)
        print("✅ 詳細を通知:", event_key)
        return

if __name__ == "__main__":
    main()
