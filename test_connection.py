"""
第一階段測試腳本：驗證 token 能不能用來登入並拿到課程資料
"""
import requests
from urllib.parse import unquote

# 讀取 token.txt，並做 URL 解碼（把 %20 還原成空白、%7C 還原成 |）
with open("token.txt", "r") as f:
    raw_token = f.read().strip()

token = unquote(raw_token)  # 解碼成真正的 "Bearer 1545941|xxxx" 格式
print(f"[除錯] 解碼後 token 開頭: {token[:15]}... (長度: {len(token)})")

headers = {
    "Authorization": token,
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

test_url = "https://lms-student.winningenglishschool.com/student_v2/course_information"

print(f"\n[測試] 嘗試連線到: {test_url}")
try:
    resp = requests.get(test_url, headers=headers, timeout=15)
    print(f"[結果] HTTP 狀態碼: {resp.status_code}")
    print(f"[結果] 回應內容類型: {resp.headers.get('Content-Type', '未知')}")
    print(f"[結果] 回應內容前 500 字:\n{resp.text[:500]}")
except Exception as e:
    print(f"[錯誤] 連線失敗: {e}")
