import feedparser
import requests
from bs4 import BeautifulSoup
import os

# Telegram Bot の設定
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=payload)

# 前回通知した EventID を保存するファイル
last_id_file = "last_id.txt"
if os.path.exists(last_id_file):
    with open(last_id_file, "r", encoding="utf-8") as f:
        last_id = f.read().strip()
else:
    last_id = ""

# 全国地震速報フィード
feed_url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
feed = feedparser.parse(feed_url)

# フィードを逆順にして古い順→新しい順に処理
for entry in reversed(feed.entries):
    # 最終報だけ対象
    if "最終報" not in entry.title:
        continue

    # 新しい地震か確認
    if entry.id == last_id:
        continue

    # 詳細 XML を取得
    detail_url = entry.link
    res = requests.get(detail_url)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "lxml-xml")

    # 震源地・日時・マグニチュード・最大震度・深さを取得
    origin_time_tag = soup.find("OriginTime")
    hypocenter_tag = soup.find("Hypocenter")
    magnitude_tag = soup.find("jmx_eb:Magnitude")
    max_int_tag = soup.find("MaxInt")
    depth_tag = soup.find("jmx_eb:Depth")

    origin_time = origin_time_tag.text if origin_time_tag else "不明"
    hypocenter = (
        hypocenter_tag.Area.Name.text
        if hypocenter_tag and hypocenter_tag.Area and hypocenter_tag.Area.Name
        else "不明"
    )
    magnitude = magnitude_tag.text if magnitude_tag else "不明"
    max_intensity = max_int_tag.text if max_int_tag else "不明"
    depth = depth_tag.text if depth_tag else "不明"

    # Telegram メッセージ作成
    message = (
        f"【地震情報（最終報）】\n"
        f"震源地: {hypocenter}\n"
        f"深さ: {depth}\n"
        f"日時: {origin_time}\n"
        f"マグニチュード: {magnitude}\n"
        f"最大震度: {max_intensity}\n\n"
        f"{detail_url}"
    )

    send_telegram_message(message)

    # 最後に通知した EventID を保存
    with open(last_id_file, "w", encoding="utf-8") as f:
        f.write(entry.id)

    break  # 最新の最終報のみ通知
