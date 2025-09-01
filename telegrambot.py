import os
import requests
import feedparser
import xml.etree.ElementTree as ET

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FEED_URL = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"

SENT_FILE = "sent_event_ids.txt"

def load_sent_ids():
    if not os.path.exists(SENT_FILE):
        return set()
    with open(SENT_FILE, "r") as f:
        return set(f.read().splitlines())

def save_sent_ids(sent_ids):
    with open(SENT_FILE, "w") as f:
        f.write("\n".join(sent_ids))

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def main():
    sent_ids = load_sent_ids()
    new_sent_ids = set(sent_ids)

    feed = feedparser.parse(FEED_URL)

    for entry in feed.entries:
        if "震源・震度に関する情報" not in entry.title:
            continue

        xml_url = entry.id
        res = requests.get(xml_url)
        root = ET.fromstring(res.content)

        ns = {
            "jmx": "http://xml.kishou.go.jp/jmaxml1/",
            "head": "http://xml.kishou.go.jp/jmaxml1/informationBasis1/",
            "body": "http://xml.kishou.go.jp/jmaxml1/body/seismology1/",
            "eb": "http://xml.kishou.go.jp/jmaxml1/elementBasis1/"
        }

        event_id = root.find(".//head:EventID", ns).text
        if event_id in sent_ids:
            continue  # 送信済みはスキップ

        info_type = root.find(".//head:InfoType", ns).text  # 速報/続報/最終報

        # 各種データを抽出
        origin_time = root.find(".//body:Earthquake/body:OriginTime", ns).text
        hypocenter = root.find(".//body:Hypocenter/body:Area/body:Name", ns).text
        magnitude = root.find(".//body:Magnitude", ns).get("description")
        depth_desc = root.find(".//body:Hypocenter/body:Area/eb:Coordinate", ns).get("description")
        max_int_tag = root.find(".//body:Intensity/body:Observation/body:MaxInt", ns)
        max_int = max_int_tag.text if max_int_tag is not None else "不明"

        # 深さだけを抽出
        depth = "不明"
        if "深さ" in depth_desc:
            depth = depth_desc.split("深さ")[-1].replace("　", "").replace("km", "km")

        # Telegram送信用メッセージ
        message = (
            f"【地震情報 {info_type}】\n"
            f"発生時刻: {origin_time}\n"
            f"震央: {hypocenter}\n"
            f"深さ: {depth}\n"
            f"規模: {magnitude}\n"
            f"最大震度: 震度{max_int}\n\n"
            f"出典: 気象庁"
        )

        send_telegram_message(message)
        new_sent_ids.add(event_id)

    save_sent_ids(new_sent_ids)

if __name__ == "__main__":
    main()
