import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import re

# 環境変数
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LAST_EVENT_FILE = "last_event.txt"

# 気象庁 XML フィード
FEED_URL = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    r = requests.post(url, data=data)
    print("📤 Telegram API Response:", r.status_code, r.text)


def format_time(iso_time):
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        dt_jst = dt.astimezone(timezone(timedelta(hours=9)))
        return dt_jst.strftime("%H時%M分ごろ")
    except:
        return "不明"


def main():
    # 前回のイベント
    last_event = None
    if os.path.exists(LAST_EVENT_FILE):
        with open(LAST_EVENT_FILE, "r", encoding="utf-8") as f:
            last_event = f.read().strip()

    # フィード取得
    r = requests.get(FEED_URL)
    r.encoding = "utf-8"
    root = ET.fromstring(r.text)

    ns_feed = {"atom": "http://www.w3.org/2005/Atom"}

    for entry in root.findall("atom:entry", namespaces=ns_feed):
        title = entry.find("atom:title", namespaces=ns_feed).text
        link = entry.find("atom:link", namespaces=ns_feed).attrib["href"]

        # 震源・震度・津波情報だけ処理
        if not any(key in title for key in ["震源", "震度", "津波"]):
            continue

        # 詳細 XML 取得
        detail_xml = requests.get(link)
        detail_xml.encoding = "utf-8"
        detail_root = ET.fromstring(detail_xml.text)

        # 名前空間
        ns = {
            "jmx": "http://xml.kishou.go.jp/jmaxml1/",
            "eb": "http://xml.kishou.go.jp/jmaxml1/body/seismology1/",
            "jmx_eb": "http://xml.kishou.go.jp/jmaxml1/elementBasis1/"
        }

        # --- 詳細 XML から取得 ---
        origin_time = detail_root.findtext(".//eb:OriginTime", namespaces=ns) or "不明"
        hypocenter = detail_root.findtext(".//eb:Hypocenter/eb:Area/eb:Name", namespaces=ns) or "不明"
        magnitude = detail_root.findtext(".//jmx_eb:Magnitude", namespaces=ns) or "不明"

        # 深さは Coordinate description から抜き出す
        coord = detail_root.find(".//jmx_eb:Coordinate", namespaces=ns)
        depth = "不明"
        if coord is not None and "description" in coord.attrib:
            desc = coord.attrib["description"]

            # 数値(km)を探す
            m = re.search(r"深さ　?([０-９0-9]+)ｋｍ", desc)
            if m:
                depth = m.group(1) + "km"
            else:
                # 「ごく浅い」「やや深い」などの文字列をそのまま反映
                if "深さ" in desc:
                    depth = desc.replace("　", "").replace("ｋｍ", "km")
        max_intensity = detail_root.findtext(".//eb:MaxInt", namespaces=ns) or "不明"

        # 同じイベントはスキップ
        event_key = f"{origin_time}-{hypocenter}"
        if event_key == last_event:
            print("⚠️ 同じイベントのためスキップ")
            continue

        # Telegram メッセージ作成
        message = (
            "📢 地震情報\n"
            f"{format_time(origin_time)}、地震がありました。\n"
            f"震源地: {hypocenter}\n"
            f"震源の深さ: {depth}\n"
            f"マグニチュード: {magnitude}\n"
            f"最大震度: {max_intensity}\n"
            f"詳細: {link}"
        )

        send_telegram_message(message)

        # イベントを保存
        with open(LAST_EVENT_FILE, "w", encoding="utf-8") as f:
            f.write(event_key)

        break  # 最新の1件だけ処理


if __name__ == "__main__":
    main()


