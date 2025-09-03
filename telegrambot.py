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

def parse_depth(coord_text: str) -> str:
    if coord_text and "-" in coord_text:
        try:
            depth_val = coord_text.split("-")[-1].replace("/", "")
            km = int(depth_val) // 1000
            return f"{km}km" if km > 0 else "ごく浅い"
        except:
            return "不明"
    return "不明"

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

    latest_entry = root.find(".//{http://www.w3.org/2005/Atom}entry")
    if latest_entry is None:
        return

    eq_id = latest_entry.find("{http://www.w3.org/2005/Atom}id").text
    title = latest_entry.find("{http://www.w3.org/2005/Atom}title").text
    link = latest_entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]

    # 🔹 すでに通知済みなら終了
    last_id = get_last_id()
    if eq_id == last_id:
        print("⏩ すでに通知済みの地震です。")
        return

    eq = fetch_and_parse(link)

    eq_tag = eq.find(".//body:Earthquake", ns)
    if eq_tag is None:
        return

    # 発生時刻
    origin_time = eq.findtext(".//body:OriginTime", default="不明", namespaces=ns)
    # JMA形式 → YYYY-MM-DDTHH:MM:SS+09:00 → HH時MM分
    if "T" in origin_time:
        try:
            time_part = origin_time.split("T")[1]
            hm = time_part.split("+")[0].split(":")
            origin_time = f"{int(hm[0])}時{hm[1]}分"
        except:
            pass

    hypocenter = eq.findtext(".//body:Hypocenter/body:Area/body:Name", default="不明", namespaces=ns)
    coord = eq.findtext(".//body:Hypocenter/body:Area/eb:Coordinate", default="", namespaces=ns)
    depth = parse_depth(coord)

    mag_tag = eq.find(".//eb:Magnitude", ns)
    magnitude = mag_tag.get("description") if mag_tag is not None else "不明"

    maxint = eq.findtext(".//body:Observation/body:MaxInt", default="不明", namespaces=ns)

    # ✅ 速報＋詳細まとめて通知
    message = f"""📢 地震情報

{origin_time}ころ、震度{maxint}の地震がありました。
震源地: {hypocenter}
深さ: {depth}
マグニチュード: {magnitude}"""

    send_telegram_message(message)
    save_last_id(eq_id)
    print("✅ 通知送信:", eq_id)

if __name__ == "__main__":
    main()
