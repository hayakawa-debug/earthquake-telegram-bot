import feedparser
import requests
import os
import json

# 環境変数から読み込む
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 保存するファイル
LAST_ID_FILE = "last_id.json"

# 気象庁の地震フィード
url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
feed = feedparser.parse(url)

# 最新の地震
entry = feed.entries[0]
title = entry.title
link = entry.link
entry_id = entry.id  # 一意のIDがある

# 前回送信したIDを読み込み
if os.path.exists(LAST_ID_FILE):
    with open(LAST_ID_FILE, "r", encoding="utf-8") as f:
        last_id = json.load(f).get("last_id")
else:
    last_id = None

# 新しい地震なら通知
if entry_id != last_id:
    message = f"【気象庁 地震情報】\n{title}\n{link}"
    url_send = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url_send, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

    # 今回のIDを保存
    with open(LAST_ID_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_id": entry_id}, f)
    print("✅ 新しい地震を通知しました")
else:
    print("⏩ 新しい地震はありません")
