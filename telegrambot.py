import os
import feedparser
import requests

# Telegramの情報（GitHub Secretsから読み込む予定）
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 気象庁公式の地震情報フィード
url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
feed = feedparser.parse(url)

# 最新の地震情報を取得
entry = feed.entries[0]
title = entry.title
link = entry.link
eq_id = entry.id  # 地震ごとに固有のID

# 前回通知した地震のIDを保存するファイル
last_file = "last_earthquake.txt"

last_id = None
if os.path.exists(last_file):
    with open(last_file, "r", encoding="utf-8") as f:
        last_id = f.read().strip()

# 新しい地震なら通知
if eq_id != last_id:
    message = f"【気象庁 地震情報】\n{title}\n{link}"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)
    print("✅ 通知しました:", message)

    # IDを更新して保存
    with open(last_file, "w", encoding="utf-8") as f:
        f.write(eq_id)
else:
    print("⏸ 新しい地震はありません")
