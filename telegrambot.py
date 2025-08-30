import feedparser
import requests
from bs4 import BeautifulSoup
import os
import re

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
    # 新しい地震かチェック
    if entry.id == last_id:
        break

    detail_url = entry.link
    res = requests.get(detail_url)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "xml")

    # 発生日時
    origin_time_tag = soup.find("OriginTime")
    origin_time = origin_time_tag.text if origin_time_tag else "不明"

    # 震源地
    hypocenter_tag = soup.find("Hypocenter")
    hypocenter = hypocenter_tag.Area.Name.text if hypocenter_tag and hypocenter_tag.Area else "不明"

    # 深さ
    depth = "不明"
    coord_tag = hypocenter_tag.Area.find("jmx_eb:Coordinate") if hypocenter_tag else None
    if coord_tag and "description" in coord_tag.attrs:
        match = re.search(r"深さ\s*(\d+)km", coord_tag["description"])
        if match:
            depth = f"{match.group(1)} km"

    # マグニチュード
    mag_tag = soup.find("jmx_eb:Magnitude")
    magnitude = mag_tag["description"] if mag_tag and "description" in mag_tag.attrs else "不明"

    # 最大震度
    max_int_tag = soup.find("MaxInt")
    max_intensity = max_int_tag.text if max_int_tag else "不明"

    # 通知メッセージ
    message = (
        f"【地震情報】\n"
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
