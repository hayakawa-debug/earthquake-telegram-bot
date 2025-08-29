import os
import feedparser
import requests
from bs4 import BeautifulSoup

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LAST_FILE = "last.txt"

# 気象庁RSS
url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
feed = feedparser.parse(url)

entry = feed.entries[0]
eq_id = entry.id

# 前回通知ID読み込み
last_id = ""
if os.path.exists(LAST_FILE):
    with open(LAST_FILE, "r", encoding="utf-8") as f:
        last_id = f.read().strip()

if eq_id != last_id:
    # summaryをHTML解析
    soup = BeautifulSoup(entry.summary, "html.parser")

    # デフォルト値
    epicenter = "不明"
    time = "不明"
    max_shindo = "不明"
    magnitude = "不明"

    # tableタグの中身をすべて確認して情報を取得
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                header = cells[0].get_text().strip()
                value = cells[1].get_text().strip()
                if "震源地" in header:
                    epicenter = value
                elif "発生時刻" in header or "発生日時" in header:
                    time = value
                elif "最大震度" in header:
                    max_shindo = value
                elif "マグニチュード" in header:
                    magnitude = value

    # Telegramメッセージ
    text = (
        f"【気象庁 地震情報】\n"
        f"発生時刻: {time}\n"
        f"震源地: {epicenter}\n"
        f"最大震度: {max_shindo}\n"
        f"マグニチュード: {magnitude}\n"
        f"{entry.link}"
    )

    # 送信
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": text})

    # ID保存
    with open(LAST_FILE, "w", encoding="utf-8") as f:
        f.write(eq_id)

    print("✅ 新しい地震を通知しました")
else:
    print("⏩ 新しい地震はありません")
