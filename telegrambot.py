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

def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def fetch_and_parse(url):
    res = requests.get(url)
    res.encoding = "utf-8"
    return ET.fromstring(res.text)

def parse_depth(coord_text: str) -> str:
    """
    +緯度+経度-深さ/ の形式を km 表記に直す
    """
    if coord_text and "-" in coord_text:
        try:
            depth_val = coord_text.split("-")[-1].replace("/", "")
            return f"{int(depth_val) // 1000} km"
        except:
            return "不明"
    return "不明"

def main():
    feed_url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
    feed = requests.get(feed_url).text
    root = ET.fromstring(feed)

    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        link = entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]

        eq = fetch_and_parse(link)

        eq_tag = eq.find(".//body:Earthquake", ns)
        if eq_tag is None:
            continue

        origin_time = eq.findtext(".//body:OriginTime", default="不明", namespaces=ns)
        hypocenter = eq.findtext(".//body:Hypocenter/body:Area/body:Name", default="不明", namespaces=ns)

        # 深さ（km単位に整形）
        coord = eq.findtext(".//body:Hypocenter/body:Area/eb:Coordinate", default="", namespaces=ns)
        depth = parse_depth(coord)

        # マグニチュード（タグ description 属性に入っている）
        mag_tag = eq.find(".//body:Magnitude", ns)
        magnitude = mag_tag.get("description") if mag_tag is not None else "不明"

        # 最大震度
        maxint = eq.findtext(".//body:Observation/body:MaxInt", default="不明", namespaces=ns)

        message = f"""📢 地震情報
発生時刻: {origin_time}
震源地: {hypocenter}
深さ: {depth}
マグニチュード: {magnitude}
最大震度: {maxint}"""

        send_telegram_message(message)

if __name__ == "__main__":
    main()
