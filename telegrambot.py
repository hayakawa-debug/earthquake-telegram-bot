import feedparser
import requests
import os

# Telegram設定
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

# 履歴ファイル
HISTORY_FILE = "history.txt"
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        history = f.read().splitlines()
else:
    history = []

# 気象庁の地震情報フィード
url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
feed = feedparser.parse(url)

for entry in feed.entries:
    eq_id = entry.id + entry.updated

    # ✅ 最終確定報だけに限定
    if "震源・震度に関する情報" not in entry.title:
        continue

    if eq_id not in history:
        message = f"【最終確定報】\n{entry.title}\n{entry.link}"
        send_telegram(message)

        history.append(eq_id)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(eq_id + "\n")

        break  # 最新1件だけ通知
