import os
import requests
import xml.etree.ElementTree as ET
import pathlib

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

FEED_URL = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
LAST_EVENT_FILE = "latest_event.txt"

def send_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

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

    for entry in entries[:5]:  # 最新5件をチェック
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

        title = doc.find(".//h:Title", ns_head).text
        time = doc.find(".//h:ReportDateTime", ns_head).text
        headline = doc.find(".//h:Headline/h:Text", ns_head).text

        message = f"【{title}】\n発表: {time}\n{headline}\n\n詳細: {link}"
        send_message(message)

        save_last_event(event_id)
        print(f"通知済み EventID: {event_id}")
        return

if __name__ == "__main__":
    main()
