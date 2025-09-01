import requests
import xml.etree.ElementTree as ET
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# XMLの名前空間
ns = {
    "jmx": "http://xml.kishou.go.jp/jmaxml1/",
    "eb": "http://xml.kishou.go.jp/jmaxml1/elementBasis1/",
    "body": "http://xml.kishou.go.jp/jmaxml1/body/seismology1/"
}

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=payload)

def main():
    # 気象庁の地震情報フィード
    feed_url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
    res = requests.get(feed_url)
    res.encoding = "utf-8"

    root = ET.fromstring(res.text)

    # 最新の地震情報のリンクを取得
    entry = root.find(".//{http://www.w3.org/2005/Atom}entry/{http://www.w3.org/2005/Atom}link")
    if entry is None:
        print("地震情報が見つかりませんでした")
        return

    eq_url = entry.get("href")
    res = requests.get(eq_url)
    res.encoding = "utf-8"
    eq_root = ET.fromstring(res.text)

    # 発表時刻
    time_tag = eq_root.find(".//jmx:Report/jmx:Head/jmx:ReportDateTime", ns)
    time = time_tag.text if time_tag is not None else "不明"

    # マグニチュード
    magnitude_tag = eq_root.find(".//body:Magnitude", ns)
    magnitude = magnitude_tag.get("description") if magnitude_tag is not None else "不明"

    # 深さ
    coord_tag = eq_root.find(".//body:Hypocenter/body:Area/eb:Coordinate", ns)
    depth = "不明"
    if coord_tag is not None and "深さ" in coord_tag.get("description", ""):
        depth = coord_tag.get("description").split("深さ")[-1].replace("　", "").replace("km", "km")

    # 最大震度
    maxint_tag = eq_root.find(".//body:Observation/body:MaxInt", ns)
    maxint = maxint_tag.text if maxint_tag is not None else "不明"

    # 震源地
    hypocenter_tag = eq_root.find(".//body:Hypocenter/body:Area/body:Name", ns)
    hypocenter = hypocenter_tag.text if hypocenter_tag is not None else "不明"

    # 通知メッセージ
    message = (
        f"📢 地震情報\n"
        f"発表時刻: {time}\n"
        f"震源地: {hypocenter}\n"
        f"深さ: {depth}\n"
        f"マグニチュード: {magnitude}\n"
        f"最大震度: {maxint}"
    )

    send_telegram_message(message)

if __name__ == "__main__":
    main()
