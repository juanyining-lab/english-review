"""
抓取「上次檢查之後」新完成的課程，整理成一份待複習文字檔
"""
import requests
import json
from datetime import datetime
from urllib.parse import unquote

# === 1. 讀取 token ===
with open("token.txt", "r") as f:
    raw_token = f.read().strip()
token = unquote(raw_token)

headers = {
    "Authorization": token,
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

# === 2. 讀取上次檢查到哪個時間點 ===
with open("last_checked.txt", "r") as f:
    last_checked_str = f.read().strip()
last_checked = datetime.fromisoformat(last_checked_str)
print(f"[資訊] 上次檢查時間: {last_checked}")

# === 3. 呼叫 API 抓所有已完成的課 ===
api_url = "https://lms-api.winningenglishschool.com/appointments"
params = {
    "append": "tutor,overall_score",
    "filter[status]": "2",
    "include": "student,schedule,schedule.course,schedule.tutor,schedule.course_topic,schedule.assignment,student.agency,student_feedback",
    "page": "1",
    "withoutPagination": "1",
    "sort": "-schedule_start",
}

"""
抓取「上次檢查之後」新完成的課程，整理成一份待複習文字檔
"""
import requests
import json
from datetime import datetime
from urllib.parse import unquote

# === 1. 讀取 token ===
with open("token.txt", "r") as f:
    raw_token = f.read().strip()
token = unquote(raw_token)

headers = {
    "Authorization": token,
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

# === 2. 讀取上次檢查到哪個時間點 ===
with open("last_checked.txt", "r") as f:
    last_checked_str = f.read().strip()
last_checked = datetime.fromisoformat(last_checked_str)
print(f"[資訊] 上次檢查時間: {last_checked}")

# === 3. 呼叫 API 抓所有已完成的課 ===
api_url = "https://lms-api.winningenglishschool.com/appointments"
params = {
    "append": "tutor,overall_score",
    "filter[status]": "2",
    "include": "student,schedule,schedule.course,schedule.tutor,schedule.course_topic,schedule.assignment,student.agency,student_feedback",
    "page": "1",
    "withoutPagination": "1",
    "sort": "-schedule_start",
}

resp = requests.get(api_url, headers=headers, params=params, timeout=15)
if resp.status_code != 200:
    print(f"[錯誤] API 回應失敗，狀態碼: {resp.status_code}")
    exit(1)

data = resp.json()
items = data.get("data", [])
print(f"[資訊] 總共抓到 {len(items)} 筆已完成課程")

# === 4. 篩選出比 last_checked 更新的課 ===
new_items = []
latest_time = last_checked

for item in items:
    schedule = item.get("schedule") or {}
    start_str = schedule.get("start")
    if not start_str:
        continue
    # API 回的時間格式類似 2026-06-24T13:00:00.000000Z
    start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00")).replace(tzinfo=None)

    if start_time > last_checked:
        new_items.append((start_time, item))
        if start_time > latest_time:
            latest_time = start_time

print(f"[資訊] 找到 {len(new_items)} 筆新課程")

# 依時間排序（舊到新）
new_items.sort(key=lambda x: x[0], reverse=True)

# === 5. 整理成待複習文字檔 ===
if new_items:
    output_lines = []
    for start_time, item in new_items:
        tutor = item.get("tutor") or {}
        tutor_name = tutor.get("name", "未知老師") if isinstance(tutor, dict) else "未知老師"
        comment = item.get("comments") or "[沒有評語內容]"
        schedule = item.get("schedule") or {}
        zoom_link = schedule.get("zoom_join_url") or item.get("zoom_join_url") or "[沒有連結]"

        output_lines.append("=" * 70)
        output_lines.append(f"課程時間: {start_time.strftime('%Y-%m-%d %H:%M')}")
        output_lines.append(f"老師: {tutor_name}")
        output_lines.append(f"影片連結: {zoom_link}")
        output_lines.append("-" * 70)
        output_lines.append(comment)
        output_lines.append("")

    filename = f"待複習_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"[完成] 已產生待複習檔案: {filename}")

    # === 6. 更新 last_checked.txt ===
    with open("last_checked.txt", "w") as f:
        f.write(latest_time.isoformat())
    print(f"[完成] 已更新 last_checked.txt 為 {latest_time.isoformat()}")
else:
    print("[完成] 沒有新課程，不需要產生檔案")
