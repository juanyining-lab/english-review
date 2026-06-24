"""
抽取所有課程的 comments 欄位，存成一個方便閱讀的文字檔
"""
import json

with open("sample_response.json", "r", encoding="utf-8") as f:
    data = json.load(f)

items = data["data"]

output_lines = []
count_with_comment = 0

for item in items:
    comment = item.get("comments")
    schedule = item.get("schedule") or {}
    tutor = item.get("tutor") or {}
    start_time = schedule.get("start", "未知時間")
    tutor_name = tutor.get("name", "未知老師") if isinstance(tutor, dict) else "未知老師"

    output_lines.append("=" * 70)
    output_lines.append(f"課程時間: {start_time}")
    output_lines.append(f"老師: {tutor_name}")
    output_lines.append(f"appointment_id: {item.get('id')}")
    output_lines.append("-" * 70)

    if comment:
        count_with_comment += 1
        output_lines.append(comment)
    else:
        output_lines.append("[此堂課沒有 comments 內容]")

    output_lines.append("")

with open("all_comments.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"總共 {len(items)} 筆課程，其中 {count_with_comment} 筆有 comments 內容")
print("已存到 all_comments.txt")
