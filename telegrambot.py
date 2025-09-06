import requests
import xml.etree.ElementTree as ET
import os
from datetime import datetime

# ====== 設定 ======
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

ns = {
    "jmx": "http://xml.kishou.go.jp/jmaxml1/",
    "head": "http://xml.kishou.go.jp/jmaxml1/informationBasis1/",
    "body": "http://xml.kishou.go.jp/jmaxml1/body/seismology1/",
    "eb": "http://xml.kishou.go.jp/jmaxml1/elementBasis1/",
}

LAST_EVENT_FILE = "last_event.txt"

# ====== 共通処理 ======
def send_telegram_message(text: str):
    """Telegramへ送信"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    res = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})
    print("📤 Telegram API Response:", res.status_code, res.text)

def format_time(timestr: str) -> str:
    """ISO8601形式を 日本語の '18時13分ころ' に変換"""
    try:
        dt = datetime.fromisoformat(timestr.replace("Z", "+00:00"))
        return dt.strftime("%H時%M分ころ")
    except Exception:
        return "不明"

def fetch_and_parse(url: str):
    """XMLを取得してパース"""
    res = requests.get(url)
    res.encoding = "utf-8"
    return ET.fromstring(res.text)

def load_last_event() -> str:
    """最後に通知したイベントキーを読み込み"""
    if os.path.exists(LAST_EVENT_FILE):
        with open(LAST_EVENT_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_last_event(event_key: str):
    """最後に通知したイベントキーを保存"""
    with open(LAST_EVENT_FILE, "w", encoding="utf-8") as f:
        f.write(event_key)

# ====== メイン処理 ======
def main():
    feed_url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
    root = fetch_and_parse(feed_url)

    last_event = load_last_event()

    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = entry.find("{http://www.w3.org/2005/Atom}title").text
        link = entry.find("{http://www.w3.org/2005/Atom}link").attrib["href"]

        eq = fetch_and_parse(link)

        # 発生時刻
        origin_time = eq.findtext(".//body:OriginTime", default="不明", namespaces=ns)

        # イベントキー = 発生時刻 + タイトル
        event_key = f"{origin_time}-{title}"
        print("▶ タイトル:", title)
        print("▶ 発生時刻:", origin_time)
        print("▶ イベントキー:", event_key)
        print("▶ 最終通知済み:", last_event)

        if event_key == last_event:
            continue  # 同じ地震/津波はスキップ

        # ========= 地震情報 =========
        if "地震" in title:
            hypocenter = eq.findtext(".//body:Hypocenter/body:Area/body:Name", default="不明", namespaces=ns)
            coord = eq.findtext(".//body:Hypocenter/body:Area/eb:Coordinate", default="", namespaces=ns)

            # 深さ
            depth = "不明"
            if coord and "-" in coord:
                try:
                    depth_val = coord.split("-")[-1].replace("/", "")
                    depth = f"{int(depth_val) // 1000} km"
                except Exception:
                    pass

            # マグニチュード
            mag_tag = eq.find(".//eb:Magnitude", ns)
            magnitude = "不明"
            if mag_tag is not None:
                magnitude = mag_tag.get("description") or mag_tag.text or "不明"

            # 最大震度
            maxint = eq.findtext(".//body:Observation/body:MaxInt", default="不明", namespaces=ns)

            # 時刻を整形
            jptime = format_time(origin_time)

            message = f"""📢 地震情報
{jptime}、地震がありました。
震源地: {hypocenter}
深さ: {depth}
マグニチュード: {magnitude}
最大震度: {maxint}"""
            send_telegram_message(message)
            save_last_event(event_key)

        # ========= 津波情報 =========
        elif "津波" in title:
            tsunami_tags = eq.findall(".//body:Forecast/body:Item/body:Area/body:Name", ns)
            areas = [t.text for t in tsunami_tags if t is not None]

            if areas:
                message = "🌊 津波情報\n津波警報・注意報が発表されました。\n\n対象地域:\n" + "\n".join(f"・{a}" for a in areas)
            else:
                message = "🌊 津波情報\n津波警報・注意報が発表されましたが、地域は不明です。"

            send_telegram_message(message)
            save_last_event(event_key)

if __name__ == "__main__":
    main()
