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
# last_id_file = "last_id.txt"
#if os.path.exists(last_id_file):
 #   with open(last_id_file, "r", encoding="utf-8") as f:
  #      last_id = f.read().strip()
#else:
 #   last_id = ""

# 気象庁の地震フィードを取得
url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
feed = feedparser.parse(url)

for entry in feed.entries:
    # 「最終報」だけ対象にする
    if "最終報" not in entry.title:
        continue

    # 新しい地震かチェック
    #if entry.id == last_id:
     #   break

    detail_url = entry.link
    res = requests.get(detail_url)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "xml")

    # デバッグ出力
    print("==== DEBUG START ====")
    print(soup.prettify()[:2000])  # 最初の2000文字だけ表示
    print("==== DEBUG END ====")

    break  # まずはデバッグ用なので1件だけ処理
    
    print("feed.entries =", len(feed.entries))
for entry in feed.entries:
    print("entry.title =", entry.title)
