import os
import requests
import xml.etree.ElementTree as ET
import pathlib

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

FEED_URL = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
LAST_EVENT_FILE = "latest_event.txt"  # 最新の EventID 保存用

def send_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    res = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})
    print("Telegram送信結果:", res.status_code, res.text)  # 送信結果を確認

def load_last_event():
    if pathlib.Path(LAST_EVENT_FILE).exists():
        return pathlib.Path(LAST_EVENT_FILE).read_text().strip()
    return None

def save_last_event(event_id):
    pathlib.Path(LAST_EVENT_FILE).write_text(event_id)

def main():
    last_event = load_last_event()

    r = requests.get(FEED_URL)
    r.raise_for_status()
    root = ET.fromstring(r.content)

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("atom:entry", ns)

    for entry in entries:
        link = entry.find("atom:link", ns).attrib["href"]

        # 詳細XML取得
        detail = requests.get(link).content
        doc = ET.fromstring(detail)

        ns_head = {"h": "http://xml.kishou.go.jp/jmaxml1/informationBasis1/"}

        # InfoType が「最終報」のみ
        info_type = doc.find(".//h:InfoType", ns_head)
        if info_type is None or "最終報" not in info_type.text:
            continue

        event_id = doc.find(".//h:EventID", ns_head).text
        if last_event == event_id:
            print("同じ地震なので通知しません")
            return

        # 震源地
        hypocenter = doc.find(".//h:Title", ns_head).text or "不明"
        # 発表日時
        time = doc.find(".//h:ReportDateTime", ns_head).text or "不明"
        # 最大震度
        max_int = doc.find(".//h:MaxInt", ns_head)
        max_int = max_int.text if max_int is not None else "不明"
        # マグニチュード
        magnitude = doc.find(".//{http://xml.kishou.go.jp/jmaxml1/elementBasis1/}Magnitude")
        magnitude = magnitude.text if magnitude is not None else "不明"
        # 深さ
        depth_tag = doc.find(".//{http://xml.kishou.go.jp/jmaxml1/elementBasis1/}Coordinate")
        depth = "不明"
        if depth_tag is not None and "深さ" in depth_tag.attrib.get("description",""):
            desc = depth_tag.attrib["description"]
            import re
            m = re.search(r"深さ\s*(\d+)ｋｍ", desc)
            if m:
                depth = m.group(1) + "km"

        message = (
            f"【地震情報（最終報）】\n"
            f"震源地: {hypocenter}\n"
            f"深さ: {depth}\n"
            f"日時: {time}\n"
            f"マグニチュード: {magnitude}\n"
            f"最大震度: {max_int}\n\n"
            f"{link}"
        )

        send_message(message)
        save_last_event(event_id)
        print(f"通知済み EventID: {event_id}")
        return  # 最新の最終報のみ通知

if __name__ == "__main__":
    main()
