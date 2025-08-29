import feedparser
import requests
import os
from bs4 import BeautifulSoup

# Telegram情報
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 気象庁の地震情報フィード
url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
feed = feedparser.parse(url)

# historyファイル
HISTORY_FILE = "history.txt"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for h in history:
            f.write(h + "\n")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    requests.post(url, data=data)

# 既存の通知済みIDをロード
history = load_history()

for entry in feed.entries:
    if "震源・震度に関する情報" not in entry.title:  # 確定報だけ
        continue

    eq_id = entry.id
    if eq_id in history:
        continue  # 既に通知済みならスキップ

    # 詳細情報XMLを取得
    detail_url = entry.link
    res = requests.get(detail_url)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "xml")

    # 発生日時
    time = soup.find("jmx_eb:OriginTime")
    time_text = time.text if time else "不明"

    # 震源地
    epicenter = soup.find("jmx_eb:Epicenter")
    epicenter_text = epicenter.text if epicenter else "不明"

    # マグニチュード
    magnitude = soup.find("jmx_eb:jmx_magnitude")
    mag_text = magnitude.text if magnitude else "不明"

    # 最大震度
    intensity = soup.find("jmx_eb:MaxInt")
    intensity_text = intensity.text if intensity else "不明"

    # メッセージ作成
    msg = (
        "【地震情報（確定報）】\n"
        f"発生時刻: {time_text}\n"
        f"震源地: {epicenter_text}\n"
        f"マグニチュード: {mag_text}\n"
        f"最大震度: {intensity_text}\n"
        f"詳細: {detail_url}"
    )

    send_telegram(msg)

    # 履歴に保存
    history.add(eq_id)
    save_history(history)

    break  # 最新の1件だけ送信
