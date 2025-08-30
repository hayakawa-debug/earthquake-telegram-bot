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

# 地震情報のURL
earthquake_url = "https://www.data.jma.go.jp/developer/xml/data/20250830050128_0_VXSE53_270000.xml"

# 地震情報を取得
res = requests.get(earthquake_url)
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
    depth_match = re.search(r"深さ\s*(\d+)km", coord_tag["description"])
    if depth_match:
        depth = f"{depth_match.group(1)} km"

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
    f"{earthquake_url}"
)

# メッセージを送信
send_telegram_message(message)
