"""
第二階段測試：直接打 API 拿課程列表的真實資料
"""
import requests
import json
from urllib.parse import unquote

with open("token.txt", "r") as f:
    raw_token = f.read().strip()

token = unquote(raw_token)

headers = {
    "Authorization": token,
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

api_url = "https://lms-api.winningenglishschool.com/appointments"
params = {
    "append": "tutor,overall_score",
    "filter[status]": "2",
    "include": "student,schedule,schedule.course,schedule.tutor,schedule.course_topic,schedule.assignment,student.agency,student_feedback",
    "page": "1",
    "withoutPagination": "1",
    "sort": "-schedule_start",
}

print(f"[測試] 呼叫 API: {api_url}")
try:
    resp = requests.get(api_url, headers=headers, params=params, timeout=15)
    print(f"[結果] HTTP 狀態碼: {resp.status_code}")
    print(f"[結果] Content-Type: {resp.headers.get('Content-Type', '未知')}")

    if "application/json" in resp.headers.get("Content-Type", ""):
        data = resp.json()
        with open("sample_response.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("[成功] 已將完整回應存到 sample_response.json")

        if isinstance(data, dict) and "data" in data:
            items = data["data"]
            print(f"[預覽] 總共抓到 {len(items)} 筆課程記錄")
            if items:
                first = items[0]
                print(f"[預覽] 第一筆資料的欄位有: {list(first.keys())}")
        else:
            print(f"[預覽] 回應結構的最上層欄位: {list(data.keys()) if isinstance(data, dict) else type(data)}")
    else:
        print(f"[結果] 非 JSON 回應，前 500 字:\n{resp.text[:500]}")
except Exception as e:
    print(f"[錯誤] {e}")
