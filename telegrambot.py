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

# メモリ内で通知済みIDを保持
sent_ids = set()

def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def fetch_and_parse(url):
    res = requests.get(url)
    res.encoding = "utf-8"
    return ET.fromstring(res.text)

def parse_depth(coord_text: str, coord_desc: str) -> str:
    # description に「深さ 20km」などが含まれる場合
    if coord_desc and "深さ" in coord_desc:
        try:
            return coord_desc.split("深さ")[-1].strip()
        except:
            pass

    # 数値部分（例: +29.4+129.4-20000/ → 20km）
    if coord_text and "-" in coord_text:
        try:
            depth_val = coord_text.split("-")[-1].replace("/", "")
            return f"{int(depth_val) // 1000} km"
        except:
            return "不明"

    return "不明"

def format_time(origin_time: str) -> str:
    try:
        dt = datetime.fromisoformat(origin_time.replace("Z", "+00:00"))
        return dt.strftime("%-d日%H時%M分")
    except:
        return origin_time

def main():
    feed_url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
    feed = requests.get(feed_url).text
    root = ET.fromstring(feed)

    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        eq_id = entry.find("{http://www.w3.org/2005/Atom}id").text
        title = entry.find("{http://www.w3.org/2005/Atom}title").text
        link = entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]

        # すでに送ったIDはスキップ
        if eq_id in sent_ids:
            continue

        eq = fetch_and_parse(link)
        eq_tag = eq.find(".//body:Earthquake", ns)
        if eq_tag is None:
            continue

        # 発生時刻
        origin_time = eq.findtext(".//body:OriginTime", default="不明", namespaces=ns)
        origin_time_fmt = format_time(origin_time)

        # 震源地
        hypocenter = eq.findtext(".//body:Hypocenter/body:Area/body:Name", default="不明", namespaces=ns)

        # 座標 → 深さ
        coord_elem = eq.find(".//body:Hypocenter/body:Area/eb:Coordinate", ns)
        coord_text = coord_elem.text if coord_elem is not None else ""
        coord_desc = coord_elem.get("description") if coord_elem is not None else ""
        depth = parse_depth(coord_text, coord_desc)

        # マグニチュード
        mag_tag = eq.find(".//eb:Magnitude", ns)
        magnitude = mag_tag.get("description") if mag_tag is not None else "不明"

        # 最大震度
        maxint = eq.findtext(".//body:Observation/body:MaxInt", default="不明", namespaces=ns)

        # メッセージ生成
        message = f"""📢 地震情報

{origin_time_fmt}ころ、地震がありました。
震源地: {hypocenter}
深さ: {depth}
マグニチュード: {magnitude}
最大震度: {maxint}"""

        send_telegram_message(message)
        sent_ids.add(eq_id)  # 通知済みとして登録

if __name__ == "__main__":
    main()
