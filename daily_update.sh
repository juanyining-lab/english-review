#!/bin/bash
# 每天自動執行：抓新資料 -> 產生網頁 -> 推送到 GitHub

cd "$(dirname "$0")"
source venv/bin/activate

echo "=== 執行時間: $(date) ===" >> update_log.txt

# 執行抓資料+產生網頁，並記錄是否成功
python3 generate_site.py >> update_log.txt 2>&1
PYTHON_EXIT_CODE=$?

if [ $PYTHON_EXIT_CODE -ne 0 ]; then
  # 失敗了，跳出 Mac 桌面通知
  osascript -e 'display notification "可能是 token 過期了，請重新登入並更新 token.txt" with title "英文課複習網頁更新失敗" sound name "Basso"'
  echo "[失敗] Python 腳本執行錯誤，跳過推送" >> update_log.txt
  echo "=== 結束（失敗） ===" >> update_log.txt
  exit 1
fi

# 成功才推送
git add index.html data.js last_checked.txt
git commit -m "自動更新：$(date '+%Y-%m-%d %H:%M')" >> update_log.txt 2>&1
git push >> update_log.txt 2>&1

echo "=== 完成 ===" >> update_log.txt
