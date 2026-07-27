"""
讀取 API 資料，解析教師評語，產生互動式複習網頁
輸出兩個檔案：data.js（資料）+ index.html（網頁）
"""
import requests
import json
import re
from datetime import datetime
from urllib.parse import unquote


# ============================================================
# 1. 抓取資料
# ============================================================
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

resp = requests.get(api_url, headers=headers, params=params, timeout=15)
resp.raise_for_status()
data = resp.json()
items = data.get("data", [])
print("[資訊] 抓到 {} 筆課程".format(len(items)))


# ============================================================
# 2. 解析教師評語
# ============================================================
def parse_comments(raw):
    if not raw:
        return {"grammar": [], "vocabulary": [], "pronunciation": [], "feedback": "", "raw": ""}

    result = {"grammar": [], "vocabulary": [], "pronunciation": [], "feedback": "", "raw": raw}

    feedback_match = re.search(r'\[B\.?\]\s*FEEDBACK[:\s]*\n(.*)', raw, re.DOTALL | re.IGNORECASE)
    if feedback_match:
        result["feedback"] = feedback_match.group(1).strip()
        raw_corrections = raw[:feedback_match.start()]
    else:
        hello_match = re.search(r'\n((?:Hello|Hi|Hey|Dear|Good)[^\n]*(?:\n(?!(?:[❌✔✅🛑🟢📣📌👉]))[^\n]*)*)', raw, re.DOTALL)
        if hello_match and len(hello_match.group(1)) > 100:
            result["feedback"] = hello_match.group(1).strip()
        raw_corrections = raw

    lines = raw_corrections.split('\n')
    current_section = ""
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if re.match(r'(?:📌|🛑|🔴|👉)?\s*(?:Sentences?|Grammar|Suggested)', line, re.IGNORECASE):
            current_section = "grammar"
            i += 1
            continue
        elif re.match(r'(?:📌|🛑|🔴|👉)?\s*(?:Words?|Vocab)', line, re.IGNORECASE):
            current_section = "vocabulary"
            i += 1
            continue
        elif re.match(r'(?:📌|🛑|🔴|👉)?\s*(?:Pronunci)', line, re.IGNORECASE):
            current_section = "pronunciation"
            i += 1
            continue
        elif re.match(r'\[A\.?\]', line, re.IGNORECASE):
            current_section = "corrections_header"
            i += 1
            continue
        elif re.match(r'\[B\.?\]', line, re.IGNORECASE):
            break

        wrong_match = re.match(r'[❌✖️\u274c]\s*(.+)', line)
        if wrong_match:
            wrong = wrong_match.group(1).strip()
            correct_sentences = []
            explanation = ""
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                correct_match = re.match(r'[✔✔️✅\u2714\u2705]\s*(.+)', next_line)
                explain_match = re.match(r'📌\s*(.+)', next_line)
                if correct_match:
                    correct_sentences.append(correct_match.group(1).strip())
                    j += 1
                elif explain_match:
                    explanation = explain_match.group(1).strip()
                    j += 1
                    break
                else:
                    break
            if correct_sentences:
                entry = {"wrong": wrong, "correct": correct_sentences[0], "explanation": explanation}
                if len(correct_sentences) > 1:
                    entry["alt_correct"] = correct_sentences[1]
                result["grammar"].append(entry)
            i = j
            continue

        if current_section == "grammar":
            alt_wrong = re.match(r'[✅👉]\s*(.+)', line)
            if alt_wrong:
                wrong = alt_wrong.group(1).strip()
                correct = ""
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    correct_match = re.match(r'^[-–—]\s*(.+)', next_line)
                    if correct_match:
                        correct = correct_match.group(1).strip()
                        i += 1
                if wrong and correct:
                    result["grammar"].append({"wrong": wrong, "correct": correct, "explanation": ""})
                i += 1
                continue

        vocab_match = re.match(r'🟢\s*(.+?)\s*[–—-]\s*(.+)', line)
        if vocab_match:
            result["vocabulary"].append({"word": vocab_match.group(1).strip(), "definition": vocab_match.group(2).strip()})
            i += 1
            continue

        if current_section == "vocabulary":
            vocab_alt = re.match(r'[👉🟢]\s*(.+?)(?:\s*[–—:]\s*(.+))?$', line)
            if vocab_alt and vocab_alt.group(1).strip() and len(vocab_alt.group(1).strip()) < 50:
                word = vocab_alt.group(1).strip()
                definition = vocab_alt.group(2).strip() if vocab_alt.group(2) else ""
                result["vocabulary"].append({"word": word, "definition": definition})
                i += 1
                continue

        pron_match = re.match(r'📣\s*(.+?)\s*(\/[^\/]+\/)', line)
        if pron_match:
            result["pronunciation"].append({"word": pron_match.group(1).strip(), "phonetics": pron_match.group(2).strip()})
            i += 1
            continue

        if current_section == "pronunciation":
            pron_alt = re.match(r'[👉📣]?\s*(.+?)\s*[:/]?\s*(\/[^\/]+\/)', line)
            if pron_alt:
                result["pronunciation"].append({"word": pron_alt.group(1).strip().rstrip(':'), "phonetics": pron_alt.group(2).strip()})
                i += 1
                continue

        i += 1

    return result


# ============================================================
# 3. 整理所有課程資料
# ============================================================
lessons = []
for item in items:
    schedule = item.get("schedule") or {}
    start_str = schedule.get("start")
    if not start_str:
        continue
    start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00")).replace(tzinfo=None)
    tutor = item.get("tutor") or {}
    tutor_name = tutor.get("name", "未知老師") if isinstance(tutor, dict) else "未知老師"
    comment = item.get("comments") or ""
    zoom_link = schedule.get("video_link") or schedule.get("zoom_join_url") or item.get("zoom_join_url") or ""

    parsed = parse_comments(comment)

    lessons.append({
        "date": start_time.strftime("%Y-%m-%d"),
        "time": start_time.strftime("%H:%M"),
        "timestamp": start_time.isoformat(),
        "tutor": tutor_name,
        "zoom_link": zoom_link,
        "parsed": parsed,
        "grammar_count": len(parsed["grammar"]),
        "vocabulary_count": len(parsed["vocabulary"]),
        "pronunciation_count": len(parsed["pronunciation"]),
    })

lessons.sort(key=lambda x: x["timestamp"], reverse=True)

total_grammar = sum(l["grammar_count"] for l in lessons)
total_vocab = sum(l["vocabulary_count"] for l in lessons)
total_pron = sum(l["pronunciation_count"] for l in lessons)
print("[解析] 文法糾正: {} 筆, 單字: {} 筆, 發音: {} 筆".format(total_grammar, total_vocab, total_pron))


# ============================================================
# 4. 輸出 data.js（純資料，用 ensure_ascii 確保安全）
# ============================================================
with open("data.js", "w", encoding="utf-8") as f:
    f.write("var ALL_LESSONS = ")
    json.dump(lessons, f, ensure_ascii=True)
    f.write(";\n")
    f.write("var SITE_INFO = ")
    json.dump({
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "count": len(lessons),
        "grammar": total_grammar,
        "vocab": total_vocab,
        "pron": total_pron,
    }, f, ensure_ascii=True)
    f.write(";\n")

print("[完成] 已產生 data.js")


# ============================================================
# 5. 輸出 index.html（純網頁，不含任何動態資料）
# ============================================================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>English Review</title>
<style>
:root{
  --coral:#FF6F59;--coral-dark:#E85A45;--coral-light:#FFF0EA;
  --purple:#9B7EDE;--purple-dark:#7C5EC7;--purple-light:#F2ECFF;
  --amber:#F5A623;--amber-light:#FFF5E0;
  --green:#3CB878;--green-light:#E8FBF0;
  --red:#FF5A5F;--red-light:#FFEBEC;
  --ink:#3D2E28;--ink-soft:#8A7A70;
  --bg:#FFF9F5;--card:#FFFFFF;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"PingFang TC","Helvetica Neue",Arial,sans-serif;background:var(--bg);color:var(--ink);-webkit-font-smoothing:antialiased;padding-bottom:80px}
.header{background:linear-gradient(135deg,#FFF4ED 0%,#FFF9F5 60%);padding:18px 20px 0;border-bottom:1px solid #FCE8DE;position:sticky;top:0;z-index:100}
.header h1{font-size:21px;font-weight:700;margin-bottom:2px;color:var(--ink)}
.sub{font-size:12px;color:var(--ink-soft);margin-bottom:12px}
.tabs{display:flex;gap:4px;background:#FFF1E8;border-radius:999px;padding:4px;margin-bottom:2px}
.tabs button{flex:1;padding:9px 0;font-size:13px;font-weight:600;border:none;background:none;cursor:pointer;color:var(--ink-soft);border-radius:999px;transition:all .2s}
.tabs button.active{color:#fff;background:linear-gradient(135deg,var(--coral),var(--purple));box-shadow:0 2px 8px rgba(255,111,89,.3)}
.filters{display:flex;gap:8px;padding:14px 20px;overflow-x:auto;-webkit-overflow-scrolling:touch}
.filters::-webkit-scrollbar{display:none}
.fg{display:flex;gap:6px;flex-shrink:0}
.fs{width:1px;background:#F0DFD4;margin:4px}
.fb{padding:7px 14px;font-size:12px;font-weight:500;border:1px solid #F0DFD4;border-radius:999px;background:#fff;cursor:pointer;white-space:nowrap;color:var(--ink-soft);transition:all .15s}
.fb.on{background:var(--coral);color:#fff;border-color:var(--coral)}
.content{padding:12px 16px}
.lc{background:var(--card);border-radius:18px;margin-bottom:12px;overflow:hidden;box-shadow:0 2px 10px rgba(255,111,89,.06)}
.lh{padding:15px 16px;display:flex;justify-content:space-between;align-items:center;cursor:pointer}
.lm{display:flex;flex-direction:column;gap:2px}
.ld{font-weight:700;font-size:15px;color:var(--ink)}
.lt{font-size:12px;color:var(--ink-soft)}
.lbs{display:flex;gap:4px}
.bd{font-size:10px;padding:3px 8px;border-radius:999px;font-weight:600}
.bd-g{background:var(--coral-light);color:var(--coral-dark)}
.bd-v{background:var(--purple-light);color:var(--purple-dark)}
.bd-p{background:var(--amber-light);color:#B87200}
.ar{color:var(--ink-soft);font-size:14px;transition:transform .2s}
.lc.open .ar{transform:rotate(180deg)}
.lb{display:none;padding:0 16px 16px;border-top:1px solid #FBEFE7}
.lc.open .lb{display:block}
.cc{margin-top:12px;padding:14px;border-radius:14px;border-left:4px solid}
.cc-g{background:var(--coral-light);border-color:var(--coral)}
.cc-v{background:var(--purple-light);border-color:var(--purple)}
.cc-p{background:var(--amber-light);border-color:var(--amber)}
.ct{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.ct-g{color:var(--coral-dark)}
.ct-v{color:var(--purple-dark)}
.ct-p{color:#B87200}
.wr{color:var(--red);font-size:14px;line-height:1.6;margin-bottom:4px}
.cr{color:var(--green);font-size:14px;line-height:1.6;margin-bottom:4px}
.ex{font-size:13px;color:var(--ink-soft);background:rgba(255,255,255,.6);padding:9px 11px;border-radius:10px;margin-top:6px;line-height:1.5}
.we{font-size:14px;line-height:1.6}
.we strong{font-weight:700}
.zl{display:inline-block;margin-top:12px;color:var(--purple-dark);text-decoration:none;font-size:13px;font-weight:600}
.rc{white-space:pre-wrap;word-wrap:break-word;font-size:13px;line-height:1.6;color:var(--ink-soft);margin-top:12px;padding:12px;background:#FBF6F2;border-radius:12px}
.fcc{padding:12px 16px}
.fcp{text-align:center;font-size:13px;color:var(--ink-soft);margin-bottom:12px}
.fc{background:linear-gradient(160deg,#fff,#FFF7F2);border-radius:22px;padding:32px 20px;min-height:200px;display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;text-align:center;box-shadow:0 4px 16px rgba(255,111,89,.12);user-select:none}
.fc:active{transform:scale(.98)}
.fc .fl{font-size:11px;color:var(--coral-dark);font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:16px}
.fc .fq{font-size:17px;line-height:1.6}
.fc .fh{font-size:12px;color:#D8B9A8;margin-top:20px}
.fc .fa{display:none}
.fc.flipped .fq,.fc.flipped .fh,.fc.flipped .fl{display:none}
.fc.flipped .fa{display:block}
.ac{font-size:17px;line-height:1.6;color:var(--green);font-weight:600;margin-bottom:12px}
.ae{font-size:13px;color:var(--ink-soft);background:var(--purple-light);padding:10px 12px;border-radius:12px;text-align:left;line-height:1.5}
.rb{display:flex;gap:8px;margin-top:16px}
.rb button{flex:1;padding:12px;font-size:14px;font-weight:600;border:none;border-radius:14px;cursor:pointer}
.rf{background:var(--red-light);color:var(--red)}
.ru{background:var(--amber-light);color:#B87200}
.rg{background:var(--green-light);color:var(--green)}
.empty{text-align:center;padding:40px 20px;color:var(--ink-soft);font-size:14px}
.qc{background:var(--card);border-radius:18px;padding:20px 16px;margin-bottom:12px;box-shadow:0 2px 10px rgba(255,111,89,.06)}
.ql{font-size:12px;color:var(--ink-soft);margin-bottom:8px}
.qq{font-size:15px;line-height:1.6;margin-bottom:16px;font-weight:600}
.qo{padding:13px 14px;border:1.5px solid #F0DFD4;border-radius:14px;margin-bottom:8px;cursor:pointer;font-size:14px;line-height:1.5;transition:all .15s}
.qo:active{transform:scale(.98)}
.qo.ok{background:var(--green-light);border-color:var(--green);color:var(--green)}
.qo.bad{background:var(--red-light);border-color:var(--red);color:var(--red)}
.qo.show{background:var(--green-light);border-color:var(--green);color:var(--green)}
.qo.off{pointer-events:none;opacity:.6}
.qfb{margin-top:10px;padding:11px 12px;border-radius:12px;font-size:13px;line-height:1.5;display:none}
.qnb{display:none;width:100%;padding:13px;font-size:14px;font-weight:700;border:none;border-radius:14px;background:linear-gradient(135deg,var(--coral),var(--purple));color:#fff;cursor:pointer;margin-top:12px}
.qs{text-align:center;padding:32px 20px}
.qs .sn{font-size:48px;font-weight:800;background:linear-gradient(135deg,var(--coral),var(--purple));-webkit-background-clip:text;background-clip:text;color:transparent}
.qs .sl{font-size:14px;color:var(--ink-soft);margin-top:4px}
.qr{margin-top:20px;padding:12px 32px;font-size:14px;font-weight:700;border:none;border-radius:999px;background:linear-gradient(135deg,var(--coral),var(--purple));color:#fff;cursor:pointer}
.pv{display:block;width:100%;padding:10px;font-size:13px;border:1px solid #F0DFD4;border-radius:14px;background:#fff;color:var(--ink-soft);cursor:pointer;margin-top:10px;text-align:center}
.dgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}
.dcard{border-radius:20px;padding:20px 16px;text-align:center;box-shadow:0 2px 10px rgba(255,111,89,.08)}
.dcard .de{font-size:28px;margin-bottom:6px}
.dcard .dn{font-size:26px;font-weight:800;color:var(--ink)}
.dcard .dl{font-size:12px;color:var(--ink-soft);margin-top:2px}
.dc1{background:var(--coral-light)}
.dc2{background:var(--purple-light)}
.dc3{background:var(--amber-light)}
.dc4{background:var(--green-light)}
.dsec{background:var(--card);border-radius:18px;padding:16px;margin-bottom:12px;box-shadow:0 2px 10px rgba(255,111,89,.06)}
.dsh{font-size:14px;font-weight:700;margin-bottom:8px}
.dpl{font-size:12px;color:var(--ink-soft);margin-bottom:8px}
.pbar{height:10px;border-radius:999px;background:#FBEFE7;overflow:hidden}
.pbar-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--coral),#FF9166);transition:width .5s}
.pbar-mastery{background:linear-gradient(90deg,var(--green),#6ED6A0)}
.pbar-g{background:linear-gradient(90deg,var(--coral),#FF9166)}
.pbar-v{background:linear-gradient(90deg,var(--purple),#B79CEE)}
.pbar-p{background:linear-gradient(90deg,var(--amber),#FFC862)}
.dtyperow{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.dtyperow:last-child{margin-bottom:0}
.dtlabel{font-size:12px;color:var(--ink-soft);width:56px;flex-shrink:0}
.dtyperow .pbar{flex:1}
.dtpct{font-size:12px;font-weight:700;color:var(--ink);width:28px;text-align:right;flex-shrink:0}
</style>
</head>
<body>
<div class="header">
  <h1>📚 English Review</h1>
  <div class="sub" id="info"></div>
  <div class="tabs">
    <button class="active" onclick="switchTab('notes',this)">📝 筆記</button>
    <button onclick="switchTab('fc',this)">🔄 翻牌複習</button>
    <button onclick="switchTab('qz',this)">✅ 小測驗</button>
    <button onclick="switchTab('dash',this)">📊 儀表板</button>
  </div>
</div>
<div class="filters" id="filterbar">
  <div class="fg">
    <button class="fb on" onclick="setTF('all',this)">全部</button>
    <button class="fb" onclick="setTF('1',this)">最近 1 堂</button>
    <button class="fb" onclick="setTF('5',this)">近 5 堂</button>
    <button class="fb" onclick="setTF('week',this)">近一週</button>
    <button class="fb" onclick="setTF('month',this)">近一個月</button>
  </div>
  <div class="fs"></div>
  <div class="fg">
    <button class="fb on" onclick="setTyF('all',this)">全部類型</button>
    <button class="fb" onclick="setTyF('grammar',this)">✏️ 文法</button>
    <button class="fb" onclick="setTyF('vocabulary',this)">📖 單字</button>
    <button class="fb" onclick="setTyF('pronunciation',this)">🗣️ 發音</button>
  </div>
  <div class="fs" id="ffs" style="display:none"></div>
  <div class="fg" id="ffg" style="display:none">
    <button class="fb" id="ffb" onclick="toggleFF(this)">🔴 只看忘了的</button>
  </div>
</div>
<div id="np" class="content"></div>
<div id="fp" class="fcc" style="display:none"></div>
<div id="qp" style="padding:12px 16px;display:none"></div>
<div id="dp" class="content" style="display:none"></div>

<script src="data.js"></script>
<script>
var tF='all',tyF='all',fO=false,cT='notes',FK='er-forgot';
function gfi(){try{return JSON.parse(localStorage.getItem(FK)||'{}')}catch(e){return{}}}
function sfi(o){localStorage.setItem(FK,JSON.stringify(o))}
function mid(l,t,i){return l.date+'_'+l.tutor+'_'+t+'_'+i}
function esc(s){if(!s)return'';var d=document.createElement('div');d.textContent=s;return d.innerHTML}

document.getElementById('info').textContent=
  '\u6700\u5f8c\u66f4\u65b0\uff1a'+SITE_INFO.updated+
  '\u3000\u5171 '+SITE_INFO.count+' \u5802\u8ab2\u3000\u6587\u6cd5 '+SITE_INFO.grammar+
  ' / \u55ae\u5b57 '+SITE_INFO.vocab+' / \u767c\u97f3 '+SITE_INFO.pron;

function getFL(){
  var ls=ALL_LESSONS;
  if(tF==='1')ls=ls.slice(0,1);
  else if(tF==='5')ls=ls.slice(0,5);
  else if(tF==='week'){var c=new Date();c.setDate(c.getDate()-7);ls=ls.filter(function(l){return new Date(l.timestamp)>=c})}
  else if(tF==='month'){var c=new Date();c.setDate(c.getDate()-30);ls=ls.filter(function(l){return new Date(l.timestamp)>=c})}
  return ls;
}
function getFC(){
  var ls=getFL(),cs=[],fg=gfi();
  for(var x=0;x<ls.length;x++){
    var l=ls[x];
    if(tyF==='all'||tyF==='grammar'){
      for(var i=0;i<l.parsed.grammar.length;i++){
        var g=l.parsed.grammar[i],id=mid(l,'g',i);
        cs.push({type:'grammar',wrong:g.wrong,correct:g.correct,alt_correct:g.alt_correct||'',explanation:g.explanation||'',word:'',definition:'',phonetics:'',lessonDate:l.date,tutor:l.tutor,id:id});
      }
    }
    if(tyF==='all'||tyF==='vocabulary'){
      for(var i=0;i<l.parsed.vocabulary.length;i++){
        var v=l.parsed.vocabulary[i],id=mid(l,'v',i);
        cs.push({type:'vocabulary',wrong:'',correct:'',alt_correct:'',explanation:'',word:v.word,definition:v.definition||'',phonetics:'',lessonDate:l.date,tutor:l.tutor,id:id});
      }
    }
    if(tyF==='all'||tyF==='pronunciation'){
      for(var i=0;i<l.parsed.pronunciation.length;i++){
        var p=l.parsed.pronunciation[i],id=mid(l,'p',i);
        cs.push({type:'pronunciation',wrong:'',correct:'',alt_correct:'',explanation:'',word:p.word,definition:'',phonetics:p.phonetics||'',lessonDate:l.date,tutor:l.tutor,id:id});
      }
    }
  }
  if(fO){cs=cs.filter(function(c){return gfi()[c.id]==='forgot'})}
  return cs;
}

function switchTab(t,btn){
  cT=t;
  var bs=document.querySelectorAll('.tabs button');
  for(var i=0;i<bs.length;i++)bs[i].className='';
  btn.className='active';
  document.getElementById('np').style.display=t==='notes'?'block':'none';
  document.getElementById('fp').style.display=t==='fc'?'block':'none';
  document.getElementById('qp').style.display=t==='qz'?'block':'none';
  document.getElementById('dp').style.display=t==='dash'?'block':'none';
  document.getElementById('filterbar').style.display=t==='dash'?'none':'flex';
  document.getElementById('ffg').style.display=t==='fc'?'flex':'none';
  document.getElementById('ffs').style.display=t==='fc'?'block':'none';
  doRender();
}
function setTF(v,btn){
  tF=v;var bs=btn.parentElement.querySelectorAll('.fb');
  for(var i=0;i<bs.length;i++)bs[i].className='fb';
  btn.className='fb on';doRender();
}
function setTyF(v,btn){
  tyF=v;var bs=btn.parentElement.querySelectorAll('.fb');
  for(var i=0;i<bs.length;i++)bs[i].className='fb';
  btn.className='fb on';doRender();
}
function toggleFF(btn){fO=!fO;btn.className=fO?'fb on':'fb';doRender()}
function doRender(){if(cT==='notes')renderN();else if(cT==='fc')renderF();else if(cT==='qz')renderQ();else if(cT==='dash')renderD()}
function toggleL(id){var el=document.getElementById(id);if(el)el.classList.toggle('open')}

function renderN(){
  var ls=getFL(),p=document.getElementById('np');
  if(!ls.length){p.innerHTML='<div class="empty">\u6c92\u6709\u7b26\u5408\u7be9\u9078\u689d\u4ef6\u7684\u8ab2\u7a0b</div>';return}
  var h='';
  for(var li=0;li<ls.length;li++){
    var l=ls[li],bd='',badges='';
    if(l.grammar_count)badges+='<span class="bd bd-g">\u6587\u6cd5 '+l.grammar_count+'</span>';
    if(l.vocabulary_count)badges+='<span class="bd bd-v">\u55ae\u5b57 '+l.vocabulary_count+'</span>';
    if(l.pronunciation_count)badges+='<span class="bd bd-p">\u767c\u97f3 '+l.pronunciation_count+'</span>';
    if(tyF==='all'||tyF==='grammar'){
      for(var gi=0;gi<l.parsed.grammar.length;gi++){
        var g=l.parsed.grammar[gi];
        bd+='<div class="cc cc-g"><div class="ct ct-g">\u6587\u6cd5\u7cfe\u6b63</div>';
        bd+='<div class="wr">\u2717 '+esc(g.wrong)+'</div>';
        bd+='<div class="cr">\u2713 '+esc(g.correct)+'</div>';
        if(g.alt_correct)bd+='<div class="cr">\u2713 '+esc(g.alt_correct)+'</div>';
        if(g.explanation)bd+='<div class="ex">'+esc(g.explanation)+'</div>';
        bd+='</div>';
      }
    }
    if(tyF==='all'||tyF==='vocabulary'){
      for(var vi=0;vi<l.parsed.vocabulary.length;vi++){
        var v=l.parsed.vocabulary[vi];
        bd+='<div class="cc cc-v"><div class="ct ct-v">\u55ae\u5b57</div>';
        bd+='<div class="we"><strong>'+esc(v.word)+'</strong>';
        if(v.definition)bd+=' \u2014 '+esc(v.definition);
        bd+='</div></div>';
      }
    }
    if(tyF==='all'||tyF==='pronunciation'){
      for(var pi=0;pi<l.parsed.pronunciation.length;pi++){
        var pr=l.parsed.pronunciation[pi];
        bd+='<div class="cc cc-p"><div class="ct ct-p">\u767c\u97f3</div>';
        bd+='<div class="we"><strong>'+esc(pr.word)+'</strong> '+esc(pr.phonetics)+'</div></div>';
      }
    }
    if(!bd&&l.parsed.raw){bd='<div class="rc">'+esc(l.parsed.raw)+'</div>'}
    if(l.zoom_link){bd+='<a href="'+esc(l.zoom_link)+'" target="_blank" class="zl">\u25b6 \u89c0\u770b\u8ab2\u7a0b\u5f71\u7247</a>'}
    var lid='l-'+li;
    h+='<div class="lc" id="'+lid+'"><div class="lh" onclick="toggleL(\''+lid+'\')">';
    h+='<div class="lm"><span class="ld">'+l.date+'</span><span class="lt">'+esc(l.tutor)+'</span></div>';
    h+='<div style="display:flex;align-items:center;gap:8px"><div class="lbs">'+badges+'</div><span class="ar">\u25be</span></div>';
    h+='</div><div class="lb">'+bd+'</div></div>';
  }
  p.innerHTML=h;
}

var fcI=[],fcX=0;
function renderF(){
  fcI=getFC();fcX=0;
  for(var i=fcI.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=fcI[i];fcI[i]=fcI[j];fcI[j]=t}
  showF();
}
function flipFC(){
  var card=document.getElementById('fcard');
  if(card&&!card.classList.contains('flipped')){
    card.classList.add('flipped');
    document.getElementById('fcbtns').style.display='flex';
  }
}
function showF(){
  var p=document.getElementById('fp');
  if(!fcI.length){p.innerHTML='<div class="empty">\u6c92\u6709\u7b26\u5408\u7be9\u9078\u689d\u4ef6\u7684\u8907\u7fd2\u9805\u76ee</div>';return}
  if(fcX>=fcI.length){p.innerHTML='<div class="empty"><div style="font-size:32px;margin-bottom:8px">\ud83c\udf89</div>\u9019\u4e00\u8f2a\u5168\u90e8\u8907\u7fd2\u5b8c\u4e86\uff01<br><button onclick="renderF()" style="margin-top:16px;padding:10px 24px;border:none;border-radius:10px;background:#0071e3;color:#fff;font-size:14px;cursor:pointer">\u518d\u4f86\u4e00\u8f2a</button></div>';return}
  var it=fcI[fcX],fg=gfi(),tot=fcI.length;
  var fl='',fc='',bc='';
  if(it.type==='grammar'){fl='\u6587\u6cd5 \u2014 \u9019\u53e5\u8a71\u54ea\u88e1\u6709\u932f\uff1f';fc=esc(it.wrong);bc='<div class="ac">\u2713 '+esc(it.correct)+'</div>';if(it.explanation)bc+='<div class="ae">'+esc(it.explanation)+'</div>'}
  else if(it.type==='vocabulary'){fl='\u55ae\u5b57 \u2014 \u9019\u500b\u5b57\u662f\u4ec0\u9ebc\u610f\u601d\uff1f';fc='<strong>'+esc(it.word)+'</strong>';bc='<div class="ac">'+esc(it.definition||'\uff08\u8001\u5e2b\u6c92\u6709\u9644\u5b9a\u7fa9\uff09')+'</div>'}
  else{fl='\u767c\u97f3 \u2014 \u9019\u500b\u5b57\u600e\u9ebc\u553e\uff1f';fc='<strong>'+esc(it.word)+'</strong>';bc='<div class="ac">'+esc(it.phonetics)+'</div>'}
  var st=fg[it.id]||'',dot=st==='forgot'?' \ud83d\udd34':st==='unsure'?' \ud83d\udfe1':st==='got'?' \ud83d\udfe2':'';
  var prevBtn=fcX>0?'<button class="pv" onclick="prevF()">\u2190 \u4e0a\u4e00\u984c</button>':'';
  p.innerHTML='<div class="fcp">'+(fcX+1)+' / '+tot+dot+'<br><span style="font-size:11px;color:#c7c7cc">'+it.lessonDate+' \u00b7 '+esc(it.tutor)+'</span></div>'
    +'<div class="fc" id="fcard" onclick="flipFC()">'
    +'<div class="fl">'+fl+'</div><div class="fq">'+fc+'</div><div class="fh">\u9ede\u64ca\u7ffb\u9762</div><div class="fa">'+bc+'</div></div>'
    +'<div class="rb" id="fcbtns" style="display:none"><button class="rf" onclick="rateC(\'forgot\')">\ud83d\ude35 \u5fd8\u4e86</button>'
    +'<button class="ru" onclick="rateC(\'unsure\')">\ud83e\udd14 \u4e0d\u78ba\u5b9a</button>'
    +'<button class="rg" onclick="rateC(\'got\')">\u2705 \u8a18\u5f97</button></div>'
    +prevBtn;
}
function prevF(){if(fcX>0){fcX--;showF()}}
function rateC(lv){var fg=gfi();fg[fcI[fcX].id]=lv;sfi(fg);fcX++;showF()}

var qI=[],qX=0,qS=0,qH={};
function renderQ(){
  var cs=getFC().filter(function(c){return c.type==='grammar'&&c.correct});
  for(var i=cs.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=cs[i];cs[i]=cs[j];cs[j]=t}
  qI=cs.slice(0,10);qX=0;qS=0;qH={};showQ();
}
function showQ(){
  var p=document.getElementById('qp');
  if(!qI.length){p.innerHTML='<div class="empty">\u6c92\u6709\u8db3\u5920\u7684\u6587\u6cd5\u7cfe\u6b63\u4f86\u7522\u751f\u6e2c\u9a57\u984c<br><span style="font-size:12px;color:#c7c7cc">\uff08\u6e2c\u9a57\u76ee\u524d\u53ea\u652f\u63f4\u6587\u6cd5\u985e\u578b\u7684\u984c\u76ee\uff09</span></div>';return}
  if(qX>=qI.length){var pct=Math.round(qS/qI.length*100);p.innerHTML='<div class="qs"><div class="sn">'+pct+'%</div><div class="sl">'+qS+' / '+qI.length+' \u7b54\u5c0d</div><button class="qr" onclick="renderQ()">\u518d\u6e2c\u4e00\u6b21</button></div>';return}
  if(qH[qX]){p.innerHTML=qH[qX];return}
  var it=qI[qX],opts=[];
  opts.push({text:it.correct,ok:1});
  opts.push({text:it.wrong,ok:0});
  var others=qI.filter(function(q,i){return i!==qX});
  if(others.length){opts.push({text:others[Math.floor(Math.random()*others.length)].wrong,ok:0})}
  for(var i=opts.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=opts[i];opts[i]=opts[j];opts[j]=t}
  var letters=['A','B','C'],oh='';
  for(var i=0;i<opts.length;i++){oh+='<div class="qo" data-ok="'+opts[i].ok+'" onclick="ansQ(this)">'+letters[i]+'. '+esc(opts[i].text)+'</div>'}
  var prevBtn=qX>0?'<button class="pv" onclick="prevQ()">\u2190 \u4e0a\u4e00\u984c</button>':'';
  p.innerHTML='<div class="qc"><div class="ql">\u7b2c '+(qX+1)+' \u984c / \u5171 '+qI.length+' \u984c\u3000<span style="font-size:11px;color:#c7c7cc">'+it.lessonDate+'</span></div>'
    +'<div class="qq">\u9078\u51fa\u6587\u6cd5\u6b63\u78ba\u7684\u53e5\u5b50\uff1a</div><div id="qos">'+oh+'</div>'
    +'<div class="qfb" id="qfb"></div><button class="qnb" id="qnb" onclick="qX++;showQ()">\u4e0b\u4e00\u984c</button>'+prevBtn+'</div>';
}
function prevQ(){if(qX>0){qX--;showQ()}}
function ansQ(el){
  var ok=el.getAttribute('data-ok')==='1';
  var opts=document.querySelectorAll('#qos .qo');
  for(var i=0;i<opts.length;i++){opts[i].classList.add('off');if(opts[i].getAttribute('data-ok')==='1')opts[i].classList.add('show')}
  el.className=ok?'qo ok':'qo bad';
  if(ok)qS++;
  var fb=document.getElementById('qfb'),it=qI[qX];
  fb.style.display='block';
  fb.style.background=ok?'#f0fdf4':'#fef2f2';
  fb.style.color=ok?'#16a34a':'#dc2626';
  if(it.explanation){fb.innerHTML=(ok?'\u2713 \u6b63\u78ba\uff01':'\u2717 \u932f\u4e86\uff01')+'<br><span style="color:#6b7280">'+esc(it.explanation)+'</span>'}
  else{fb.textContent=ok?'\u2713 \u6b63\u78ba\uff01':'\u2717 \u7b54\u932f\u4e86\uff0c\u6b63\u78ba\u7b54\u6848\u5df2\u6a19\u793a\u3002'}
  document.getElementById('qnb').style.display='block';
  qH[qX]=document.getElementById('qp').innerHTML;
}

function renderD(){
  var p=document.getElementById('dp'),fg=gfi();
  var totalItems=SITE_INFO.grammar+SITE_INFO.vocab+SITE_INFO.pron;
  var keys=Object.keys(fg),reviewed=keys.length,got=0,unsure=0,forgot=0;
  for(var i=0;i<keys.length;i++){
    var v=fg[keys[i]];
    if(v==='got')got++;else if(v==='unsure')unsure++;else if(v==='forgot')forgot++;
  }
  var reviewPct=totalItems>0?Math.round(reviewed/totalItems*100):0;
  var masteryPct=reviewed>0?Math.round(got/reviewed*100):0;
  var gPct=totalItems>0?Math.round(SITE_INFO.grammar/totalItems*100):0;
  var vPct=totalItems>0?Math.round(SITE_INFO.vocab/totalItems*100):0;
  var prPct=totalItems>0?Math.round(SITE_INFO.pron/totalItems*100):0;
  var h='';
  h+='<div class="dgrid">';
  h+='<div class="dcard dc1"><div class="de">📚</div><div class="dn">'+SITE_INFO.count+'</div><div class="dl">總課程</div></div>';
  h+='<div class="dcard dc2"><div class="de">✏️</div><div class="dn">'+SITE_INFO.grammar+'</div><div class="dl">文法糾正</div></div>';
  h+='<div class="dcard dc3"><div class="de">📖</div><div class="dn">'+SITE_INFO.vocab+'</div><div class="dl">單字</div></div>';
  h+='<div class="dcard dc4"><div class="de">🗣️</div><div class="dn">'+SITE_INFO.pron+'</div><div class="dl">發音</div></div>';
  h+='</div>';
  h+='<div class="dsec"><div class="dsh">🎯 複習進度</div><div class="dpl">已複習 '+reviewed+' / '+totalItems+' 項（'+reviewPct+'%）</div><div class="pbar"><div class="pbar-fill" style="width:'+reviewPct+'%"></div></div></div>';
  h+='<div class="dsec"><div class="dsh">🌟 熟悉度</div><div class="dpl">✅ '+got+' 記得　🤔 '+unsure+' 不確定　😵 '+forgot+' 忘了</div><div class="pbar"><div class="pbar-fill pbar-mastery" style="width:'+masteryPct+'%"></div></div></div>';
  h+='<div class="dsec"><div class="dsh">📊 內容分布</div>';
  h+='<div class="dtyperow"><span class="dtlabel">✏️ 文法</span><div class="pbar"><div class="pbar-fill pbar-g" style="width:'+gPct+'%"></div></div><span class="dtpct">'+SITE_INFO.grammar+'</span></div>';
  h+='<div class="dtyperow"><span class="dtlabel">📖 單字</span><div class="pbar"><div class="pbar-fill pbar-v" style="width:'+vPct+'%"></div></div><span class="dtpct">'+SITE_INFO.vocab+'</span></div>';
  h+='<div class="dtyperow"><span class="dtlabel">🗣️ 發音</span><div class="pbar"><div class="pbar-fill pbar-p" style="width:'+prPct+'%"></div></div><span class="dtpct">'+SITE_INFO.pron+'</span></div>';
  h+='</div>';
  if(!reviewed){h+='<div class="empty">還沒有複習紀錄，去「翻牌複習」開始累積吧 🚀</div>'}
  p.innerHTML=h;
}

renderN();
</script>
</body>
</html>""")

print("[完成] 已產生 index.html")
