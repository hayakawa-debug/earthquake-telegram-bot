import requests
import xml.etree.ElementTree as ET
import os
from datetime import datetime

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
            return f"{int(depth_val) // 1000} km"
        except:
            return "不明"
    return "不明"

def format_time(timestr: str) -> str:
    try:
        dt = datetime.fromisoformat(timestr.replace("Z", "+00:00"))
        return dt.strftime("%-m月%-d日 %H時%M分")
    except:
        return timestr

def get_last_event():
    if os.path.exists(LAST_EVENT_FILE):
        with open(LAST_EVENT_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_event(event_key: str):
    with open(LAST_EVENT_FILE, "w") as f:
        f.write(event_key)

def main():
    feed_url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
    feed = requests.get(feed_url).text
    root = ET.fromstring(feed)

    last_event = get_last_event()
   速報_cache = {}

    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = entry.find("{http://www.w3.org/2005/Atom}title").text
        link = entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]

        eq = fetch_and_parse(link)
        origin_time = eq.findtext(".//body:OriginTime", default="不明", namespaces=ns)
        hypocenter = eq.findtext(".//body:Hypocenter/body:Area/body:Name", default="不明", namespaces=ns)
        coord = eq.findtext(".//body:Hypocenter/body:Area/eb:Coordinate", default="", namespaces=ns)
        depth = parse_depth(coord)
        mag_tag = eq.find(".//eb:Magnitude", ns)
        magnitude = mag_tag.get("description") if mag_tag is not None else "不明"
        maxint = eq.findtext(".//body:Observation/body:MaxInt", default="不明", namespaces=ns)

        event_key = origin_time[:16]  # 分までで一意にする

        if event_key == last_event:
            continue  # すでに通知済み

        if "震度速報" in title:
            message = f"""📢 地震速報
{format_time(origin_time)}ころ、震度{maxint}の地震がありました。"""
            send_telegram_message(message)
            速報_cache[event_key] = {"time": origin_time, "maxint": maxint}

        elif "震源に関する情報" in title or "震源・震度に関する情報" in title:
            if event_key in 速報_cache:
                message = f"""📢 地震情報（速報＋詳細）

【速報】
{format_time(速報_cache[event_key]['time'])}ころ、震度{速報_cache[event_key]['maxint']}の地震。

【詳細】
震源地: {hypocenter}
深さ: {depth}
マグニチュード: {magnitude}
最大震度: {maxint}"""
            else:
                message = f"""📢 地震情報
{format_time(origin_time)}ころ、地震がありました。
震源地: {hypocenter}
深さ: {depth}
マグニチュード: {magnitude}
最大震度: {maxint}"""

            send_telegram_message(message)
            save_last_event(event_key)

if __name__ == "__main__":
    main()
