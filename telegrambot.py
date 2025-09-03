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
    if coord_text and "-" in coord_text:
        try:
            depth_val = coord_text.split("-")[-1].replace("/", "")
            return f"{int(depth_val) // 1000} km"
        except:
            return "不明"
    return "不明"

def main():
    feed_url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
    res = requests.get(feed_url)
    res.encoding = "utf-8"  # ✅ 文字化け防止
    feed = res.text
    root = ET.fromstring(feed)

    速報データ = {}  # ✅ インデントを修正

    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        eq_id = entry.find("{http://www.w3.org/2005/Atom}id").text
        title = entry.find("{http://www.w3.org/2005/Atom}title").text
        link = entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]

        eq = fetch_and_parse(link)
        eq_tag = eq.find(".//body:Earthquake", ns)
        if eq_tag is None:
            continue

        origin_time = eq.findtext(".//body:OriginTime", default="不明", namespaces=ns)
        hypocenter = eq.findtext(".//body:Hypocenter/body:Area/body:Name", default="不明", namespaces=ns)
        coord = eq.findtext(".//body:Hypocenter/body:Area/eb:Coordinate", default="", namespaces=ns)
        depth = parse_depth(coord)

        mag_tag = eq.find(".//eb:Magnitude", ns)
        magnitude = mag_tag.get("description") if mag_tag is not None else "不明"

        maxint = eq.findtext(".//body:Observation/body:MaxInt", default="不明", namespaces=ns)

        if "震度速報" in title:
            速報データ[eq_id] = {
                "time": origin_time,
                "maxint": maxint,
            }

        elif "地震情報" in title or "震源・震度に関する情報" in title:
            if eq_id in 速報データ:
                速報 = 速報データ[eq_id]
                message = f"""📢 地震情報（速報＋詳細）

【速報】
{速報['time']}ころ、震度{速報['maxint']}の地震がありました。

【詳細】
震源地: {hypocenter}
深さ: {depth}
マグニチュード: {magnitude}
最大震度: {maxint}"""
            else:
                message = f"""📢 地震情報

{origin_time}ころ、地震がありました。
震源地: {hypocenter}
深さ: {depth}
マグニチュード: {magnitude}
最大震度: {maxint}"""

            send_telegram_message(message)

if __name__ == "__main__":
    main()
