import json

with open("sample_response.json", "r", encoding="utf-8") as f:
    data = json.load(f)

first = data["data"][0]

print("=== schedule 內容 ===")
print(json.dumps(first.get("schedule"), ensure_ascii=False, indent=2)[:800])

print("\n=== student_feedback 內容 ===")
print(first.get("student_feedback"))

print("\n=== zoom_join_url ===")
print(first.get("zoom_join_url"))

print("\n=== comments / note ===")
print("comments:", first.get("comments"))
print("note:", first.get("note"))
