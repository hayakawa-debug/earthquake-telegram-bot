import os
import feedparser
import requests
from bs4 import BeautifulSoup

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HISTORY_FILE = "history.txt"

# RSSを取得
url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
feed = feedparser.parse(url)

# 履歴を読み込み（id + updated）
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        notified = set(f.read().splitlines())
else:
    notified = set()

for entry in feed.entries:
    eq_key = f"{entry.id}_{entry.updated}"

    if eq_key in notified:
        continue

    # ---- 区別ラベル ----
    label = ""
    if "震度速報" in entry.title:
        label = "[速報]"
    elif "震源に関する情報" in entry.title:
        label = "[震源情報]"
    elif "震度に関する情報" in entry.title:
        label = "[震度情報]"
    elif "震源・震度に関する情報" in entry.title:
        label = "[確定報]"
    else:
        label = "[更新]"

    # ---- summaryを解析 ----
    soup = BeautifulSoup(entry.summary, "html.parser")

    epicenter, time, max_shindo, magnitude = "不明", "不明", "不明", "不明"
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                header = cells[0].get_text().strip()
                value = cells[1].get_text().strip()
                if "震源地" in header:
                    epicenter = value
                elif "発生" in header:
                    time = value
                elif "最大震度" in header:
                    max_shindo = value
                elif "マグニチュード" in header:
                    magnitude = value

    # ---- 通知メッセージ ----
    text = (
        f"{label} 気象庁 地震情報\n"
        f"発生時刻: {time}\n"
        f"震源地: {epicenter}\n"
        f"最大震度: {max_shindo}\n"
        f"マグニチュード: {magnitude}\n"
        f"{entry.link}"
    )

    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": text})

    print(f"✅ 通知しました: {label} {eq_key}")

    notified.add(eq_key)

# 履歴を保存
with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    for eq in list(notified)[-200:]:
        f.write(eq + "\n")
