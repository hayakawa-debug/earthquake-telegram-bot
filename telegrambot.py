import feedparser
import requests
from bs4 import BeautifulSoup
import os

# Telegram Bot API の設定
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=payload)

# 前回通知したIDを保持
last_id_file = "last_id.txt"
if os.path.exists(last_id_file):
    with open(last_id_file, "r", encoding="utf-8") as f:
        last_id = f.read().strip()
else:
    last_id = ""

# 気象庁の地震フィード
url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
feed = feedparser.parse(url)

for entry in feed.entries:
    # 「最終報」だけ対象にする
    if "最終報" not in entry.title:
        continue

    # 新しい地震かチェック
    if entry.id == last_id:
        break

    detail_url = entry.link
    res = requests.get(detail_url)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "lxml-xml")

    # 各種情報を取得
    origin_time = soup.find("OriginTime")
    hypocenter = soup.find("Hypocenter")
    magnitude = soup.find("jmx_eb:Magnitude")
    max_intensity = soup.find("MaxInt")
    depth = soup.find("jmx_eb:Depth")

    origin_time = origin_time.text if origin_time else "不明"
    hypocenter = (
        hypocenter.Area.Name.text
        if hypocenter and hypocenter.Area and hypocenter.Area.Name
        else "不明"
    )
    magnitude = magnitude.text if magnitude else "不明"
    max_intensity = max_intensity.text if max_intensity else "不明"
    depth = depth.text if depth else "不明"

    # 通知メッセージ
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

    # 最後に通知したIDを保存
    with open(last_id_file, "w", encoding="utf-8") as f:
        f.write(entry.id)

    break  # 最新の最終報のみ通知
