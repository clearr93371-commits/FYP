"""
MoCA (Attention + Orientation) game  -  run:  streamlit run moca_game.py
Use Chrome or Edge on localhost/https (needed for microphone + speech recognition).
Data is stored in moca_data.db (SQLite); download as CSV from the sidebar.
"""
import json, random, sqlite3, time, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

DB = "moca_data.db"
HK = timezone(timedelta(hours=8))
TAP_SEQ = "52137411806215174511141705112"   # MoCA letter/number-1 tapping sequence (11 ones)
WEEKDAYS = ["星期一 Mon", "星期二 Tue", "星期三 Wed", "星期四 Thu", "星期五 Fri", "星期六 Sat", "星期日 Sun"]
EMOJIS = ["🌞", "🌈", "🐶", "🌸", "🍀", "🐱", "🎈", "🍵", "🦋", "⭐", "🐼", "🌻"]
LANGS = {"廣東話 (Cantonese)": ("zh-HK", ["yue-Hant-HK", "zh-HK", "zh-TW"]), "English": ("en-US", ["en-US"]),
         "普通話 (Mandarin)": ("zh-CN", ["cmn-Hans-CN", "zh-CN"])}   # label -> (speech out, speech-recognition candidates)

# ----------------------------------------------------------------------------
# Front-end widget: text-to-speech, speech-to-text, tapping game, pop effects
# ----------------------------------------------------------------------------
# Cantonese single-syllable digits are often transcribed as same-sounding characters; map them back to digits.
# (Educated guesses - the raw transcript is always stored, so you can review/adjust this table with real data.)
HOMO = {"而": 2, "爾": 2, "耳": 2, "衣": 1, "依": 1, "乙": 1, "山": 3, "衫": 3, "死": 4, "世": 4, "吳": 5, "唔": 5, "吾": 5, "午": 5,
        "綠": 6, "錄": 6, "鹿": 6, "吉": 7, "戚": 7, "漆": 7, "拔": 8, "狗": 9, "夠": 9, "久": 9, "酒": 9, "令": 0, "靈": 0, "凌": 0, "動": 0}

WIDGET_HTML = r"""<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;font-family:system-ui,"Noto Sans TC",sans-serif;text-align:center;color:#333}
.row{display:flex;gap:20px;justify-content:center;align-items:center;margin:14px}
.btn{border:0;border-radius:50%;width:110px;height:110px;font-size:48px;cursor:pointer;background:#e8f0fe;box-shadow:0 5px 0 #b6c8f0;touch-action:manipulation}
.btn:active{transform:translateY(5px);box-shadow:none}
.btn:disabled{opacity:.4}
.rec{background:#ffd9d9;animation:pulse .8s infinite}
@keyframes pulse{50%{transform:scale(1.1)}}
#tap{width:200px;height:200px;font-size:70px;background:#ffe9a8;box-shadow:0 8px 0 #e0b84c}
.go{border:0;border-radius:14px;padding:12px 30px;font-size:22px;background:#4caf50;color:#fff;cursor:pointer}
.go:disabled{opacity:.4}
#txt{width:80%;font-size:34px;text-align:center;letter-spacing:8px;padding:8px;border:3px dashed #b6c8f0;border-radius:14px}
.bars{height:30px}.bars i{display:inline-block;width:8px;height:8px;margin:0 3px;background:#4c8bf5;border-radius:4px}
.on i{animation:bar .5s infinite alternate}.on i:nth-child(2){animation-delay:.1s}.on i:nth-child(3){animation-delay:.2s}.on i:nth-child(4){animation-delay:.3s}
@keyframes bar{to{height:28px}}
.fly{position:fixed;font-size:30px;pointer-events:none;animation:fly .9s ease-out forwards}
@keyframes fly{to{transform:translate(var(--dx),var(--dy)) scale(.4) rotate(120deg);opacity:0}}
</style></head><body><div id="app"></div><script>
const $=id=>document.getElementById(id);
const send=v=>parent.postMessage({isStreamlitMessage:true,type:"streamlit:setComponentValue",value:v,dataType:"json"},"*");
const frame=h=>parent.postMessage({isStreamlitMessage:true,type:"streamlit:setFrameHeight",height:h},"*");
function say(t,lang){speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(t);u.lang=lang;u.rate=1;speechSynthesis.speak(u)}
function burst(el,em){const r=el.getBoundingClientRect();for(let i=0;i<10;i++){const s=document.createElement("span");s.className="fly";s.textContent=em[i%em.length];
 s.style.left=(r.left+r.width/2)+"px";s.style.top=(r.top+r.height/2)+"px";s.style.setProperty("--dx",(Math.random()*240-120)+"px");s.style.setProperty("--dy",(-60-Math.random()*120)+"px");
 document.body.appendChild(s);setTimeout(()=>s.remove(),950)}}
function beep(){try{const c=new (window.AudioContext||window.webkitAudioContext)(),o=c.createOscillator(),g=c.createGain();o.frequency.value=660+Math.random()*300;g.gain.value=.15;o.connect(g);g.connect(c.destination);o.start();o.stop(c.currentTime+.08)}catch(e){}}

const D={"零":0,"〇":0,"洞":0,"一":1,"壹":1,"幺":1,"二":2,"貳":2,"兩":2,"两":2,"三":3,"叁":3,"參":3,"四":4,"肆":4,"五":5,"伍":5,"六":6,"陸":6,"陆":6,"七":7,"柒":7,"八":8,"捌":8,"九":9,"玖":9},
 U={"十":10,"拾":10,"百":100,"佰":100,"千":1000,"仟":1000,"萬":1e4,"万":1e4},
 EW={zero:0,one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9};
Object.assign(D,__HOMO__);
const CNRE=new RegExp("["+Object.keys(D).join("")+Object.keys(U).join("")+"]+","g");
function toDigits(s){s=s.normalize("NFKC").toLowerCase();
 for(const k in EW)s=s.split(k).join(EW[k]);
 s=s.replace(CNRE,r=>{
  if(![...r].some(c=>c in U))return [...r].map(c=>D[c]).join("");
  let tot=0,sec=0,n=0;for(const c of r){if(c in D)n=D[c];else if(U[c]===1e4){tot+=(sec+n)*1e4;sec=0;n=0}else{sec+=(n||1)*U[c];n=0}}
  return String(tot+sec+n)});
 return s.replace(/\D/g,"")}
function digits(a){
 $("app").innerHTML=`<div class="row"><button class="btn" id="sp">🔊</button><button class="btn" id="mic">🎤</button></div>
 <div class="bars" id="bars"><i></i><i></i><i></i><i></i></div>
 <input id="txt" placeholder="…" readonly><div id="heard" style="color:#999;font-size:14px;margin-top:4px"></div><div class="row"><button class="go" id="ok">✔ 完成 Done</button></div><div id="msg"></div>`;
 frame(340);
 let plays=0,rec=null,typed=false,raw="",t0=performance.now();
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SR){$("txt").readOnly=false;typed=true;$("msg").textContent="⚠ Speech recognition not supported - use Chrome/Edge (typing fallback enabled)"}
 $("sp").onclick=()=>{if(plays>=a.max_plays)return;plays++;$("sp").disabled=true;$("bars").className="bars on";
  a.digits.split("").forEach((d,i)=>setTimeout(()=>{say(d,a.lang);burst($("sp"),["🎵","✨"])},i*1000));
  setTimeout(()=>{$("bars").className="bars";$("sp").disabled=plays>=a.max_plays},a.digits.length*1000+400)};
 const ERR={"not-allowed":"🎤 麥克風被封鎖 - 請在網址列允許麥克風 / Microphone blocked: allow mic access in the address bar",
  "service-not-allowed":"🎤 瀏覽器不允許語音辨識 / Speech service not allowed","no-speech":"聽不到聲音，請再試 / No speech detected, try again",
  "audio-capture":"找不到麥克風 / No microphone found","network":"語音服務連線失敗（需要網絡）/ Speech service unreachable (needs internet)",
  "language-not-supported":"此瀏覽器不支援所選語言 / Language not supported by this browser"};
 let li=0,retry=false,quiet=null,used="";
 function listen(){
  rec=new SR();used=a.stt[li];rec.lang=used;rec.interimResults=true;rec.continuous=true;
  $("mic").classList.add("rec");$("msg").textContent="🎤 聆聽中… 說完再按一次 🎤 / Listening… press 🎤 again when done ("+used+")";
  rec.onresult=e=>{raw=[...e.results].map(r=>r[0].transcript).join("");$("txt").value=toDigits(raw);$("heard").textContent="辨識原文 Heard: "+raw;
   clearTimeout(quiet);quiet=setTimeout(()=>rec&&rec.stop(),3000)};
  rec.onerror=e=>{if(e.error==="language-not-supported"&&li<a.stt.length-1){li++;retry=true;return}
   if(e.error!=="aborted")$("msg").textContent=(ERR[e.error]||"mic error: "+e.error)+" ["+used+"]"};
  rec.onend=()=>{clearTimeout(quiet);rec=null;if(retry){retry=false;listen();return}
   $("mic").classList.remove("rec");if(raw)burst($("txt"),["⭐","✨"])};
  try{rec.start()}catch(err){$("msg").textContent="mic error: "+err.message}}
 $("mic").onclick=()=>{if(!SR)return;if(rec){rec.stop();return}raw="";$("txt").value="";li=0;listen()};
 $("ok").onclick=()=>send({transcript:typed?$("txt").value:raw,plays,typed,stt_lang:used,elapsed_ms:Math.round(performance.now()-t0)});
}
function tap(a){
 $("app").innerHTML=`<div class="row"><button class="go" id="st">▶ 開始 Start</button></div>
 <div class="row"><button class="btn" id="tap" disabled>👆</button></div><div id="msg"></div>`;
 frame(360);
 let cur=-1,log=[],t0=0;
 $("st").onclick=()=>{$("st").disabled=true;$("tap").disabled=false;
  a.seq.split("").forEach((d,i)=>setTimeout(()=>{cur=i;t0=performance.now();say(d,a.lang)},i*1000+500));
  setTimeout(()=>{$("tap").disabled=true;send({log,n:a.seq.length})},a.seq.length*1000+1500)};
 $("tap").onpointerdown=()=>{if(cur<0)return;log.push([cur,Math.round(performance.now()-t0)]);burst($("tap"),["⭐","✨","💥","🎉"]);beep()};
}
let built=false;
addEventListener("message",e=>{if(e.data.type!=="streamlit:render"||built)return;built=true;const a=e.data.args;a.mode==="tap"?tap(a):digits(a)});
parent.postMessage({isStreamlitMessage:true,type:"streamlit:componentReady",apiVersion:1},"*");
</script></body></html>"""

import tempfile
WIDGET_HTML = WIDGET_HTML.replace("__HOMO__", json.dumps(HOMO, ensure_ascii=False))
_dir = Path(tempfile.gettempdir()) / "moca_widget_files"   # independent of the script location
_dir.mkdir(exist_ok=True)
_f = _dir / "index.html"
try:   # write only when changed, and atomically, so a rerun never serves a half-written file
    if not _f.exists() or _f.read_text(encoding="utf-8") != WIDGET_HTML:
        _tmp = _dir / "index.html.tmp"
        _tmp.write_text(WIDGET_HTML, encoding="utf-8")
        _tmp.replace(_f)
except OSError:
    pass
# Streamlit prefixes the component name with the calling module's name. If this script is called
# e.g. "moca_game (1).py" that name breaks the widget URL, so declare it from a tiny helper module instead.
_loader = _dir / "moca_widget_loader.py"
_src = "import streamlit.components.v1 as c\n\ndef make(path):\n    return c.declare_component('moca_widget', path=path)\n"
if not _loader.exists() or _loader.read_text() != _src:
    _loader.write_text(_src)
import sys
if str(_dir) not in sys.path:
    sys.path.insert(0, str(_dir))
import moca_widget_loader
widget = moca_widget_loader.make(str(_dir))

# ----------------------------------------------------------------------------
# Backend: SQLite logging
# ----------------------------------------------------------------------------
def log(task, item, expected, response, parsed, correct, score=None, extra=None):
    ss = st.session_state
    con = sqlite3.connect(DB)
    con.execute("""create table if not exists trials(id integer primary key, ts text, session text,
        participant text, lang text, task text, item text, expected text, response text, parsed text,
        correct integer, score real, extra text)""")
    con.execute("insert into trials(ts,session,participant,lang,task,item,expected,response,parsed,correct,score,extra) values(?,?,?,?,?,?,?,?,?,?,?,?)",
                (datetime.now(HK).isoformat(timespec="seconds"), ss.sid, ss.pid, ss.lang, task, item,
                 str(expected), None if response is None else str(response), None if parsed is None else str(parsed),
                 None if correct is None else int(correct), score, json.dumps(extra, ensure_ascii=False) if extra else None))
    con.commit(); con.close()

def load(session_only=False):
    con = sqlite3.connect(DB)
    try:
        q = "select * from trials" + (" where session=?" if session_only else "")
        return pd.read_sql(q, con, params=(st.session_state.sid,) if session_only else None)
    except Exception:
        return pd.DataFrame()
    finally:
        con.close()

import re, unicodedata
DIG = {"零": 0, "〇": 0, "洞": 0, "一": 1, "壹": 1, "幺": 1, "二": 2, "貳": 2, "兩": 2, "两": 2, "三": 3, "叁": 3, "參": 3,
       "四": 4, "肆": 4, "五": 5, "伍": 5, "六": 6, "陸": 6, "陆": 6, "七": 7, "柒": 7, "八": 8, "捌": 8, "九": 9, "玖": 9}
DIG.update(HOMO)
UNIT = {"十": 10, "拾": 10, "百": 100, "佰": 100, "千": 1000, "仟": 1000, "萬": 10000, "万": 10000}
EN = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
CN_RUN = re.compile("[" + "".join(DIG) + "".join(UNIT) + "]+")

def _cn_run(m):
    r = m.group()
    if not any(c in UNIT for c in r):            # e.g. 二一八五四 -> 21854
        return "".join(str(DIG[c]) for c in r)
    tot = sec = n = 0                            # e.g. 二萬一千八百五十四 -> 21854
    for c in r:
        if c in DIG:
            n = DIG[c]
        elif UNIT[c] == 10000:
            tot += (sec + n) * 10000; sec = n = 0
        else:
            sec += (n or 1) * UNIT[c]; n = 0
    return str(tot + sec + n)

def parse_digits(t):
    t = unicodedata.normalize("NFKC", t or "").lower()
    for k, v in EN.items():
        t = t.replace(k, str(v))
    return re.sub(r"\D", "", CN_RUN.sub(_cn_run, t))

# ----------------------------------------------------------------------------
# App
# ----------------------------------------------------------------------------
st.set_page_config(page_title="MoCA Game", page_icon="🧠", layout="centered")
st.markdown("""<style>
.chip{display:inline-block;margin:6px;padding:14px 26px;border-radius:18px;font-size:38px;font-weight:700;background:#fff3c4;
 animation:pop .55s cubic-bezier(.2,1.7,.4,1) both}
@keyframes pop{0%{transform:scale(0) rotate(-25deg);opacity:0}100%{transform:scale(1) rotate(0);opacity:1}}
.diary{border:3px solid #333;border-radius:14px;padding:18px 24px;background:#fffdf3;font-size:24px}
.diary .em{font-size:90px;text-align:center;animation:pop .8s both}
</style>""", unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("sid", uuid.uuid4().hex[:8]); ss.setdefault("step", 0); ss.setdefault("scores", {})
STEPS = ["intro", "fwd", "bwd", "tap", "serial", "orient", "done"]

def nxt():
    ss.step += 1
    st.rerun()

with st.sidebar:
    st.header("⚙️ Tester panel")
    ss.pid = st.text_input("Participant ID", "P001")
    ss.lang_label = st.selectbox("Language 語言", list(LANGS))
    ss.lang, ss.stt = LANGS[ss.lang_label]
    ss.exp_place = st.text_input("Expected place 地點 (answer key)")
    ss.exp_region = st.text_input("Expected region 地區 (answer key)")
    df_all = load()
    if not df_all.empty:
        st.download_button("⬇ Download all data (CSV)", df_all.to_csv(index=False).encode("utf-8-sig"), "moca_data.csv", "text/csv")
    if st.button("🔄 Restart"):
        ss.clear(); st.rerun()

step = STEPS[ss.step]
st.title("🧠 MoCA Game")

if step == "intro":
    st.write("這是一連串小遊戲。請準備好耳機/喇叭及麥克風。\n\nA few short games. Please have speakers and a microphone ready (use Chrome/Edge).")
    if st.button("▶ 開始 Start", type="primary") and ss.pid.strip():
        nxt()

elif step in ("fwd", "bwd"):
    fwd = step == "fwd"
    digits, expected = ("21854", "21854") if fwd else ("742", "247")
    st.subheader("① 數字重複 " + ("(向前 Forward)" if fwd else "(向後 Backward)"))
    st.caption("按 🔊 聽一次數字，然後按 🎤 說出" + ("相同的數字" if fwd else "倒轉的數字") + "。Listen once, then say the numbers " + ("in the same order." if fwd else "backwards."))
    v = widget(mode="digits", digits=digits, lang=ss.lang, stt=ss.stt, max_plays=1, key=step, default=None)
    if v:
        parsed = parse_digits(v["transcript"]); ok = parsed == expected
        log("digit_" + step, "digit_span", expected, v["transcript"], parsed, ok, int(ok),
            {"plays": v["plays"], "stt_lang": v.get("stt_lang"), "typed_fallback": v["typed"], "elapsed_ms": v["elapsed_ms"]})
        ss.scores[step] = int(ok); nxt()

elif step == "tap":
    st.subheader("② 一出現「1」就㩒掣 Tap when you hear “1”")
    v = widget(mode="tap", seq=TAP_SEQ, lang=ss.lang, key="tap", default=None)
    if v:
        taps = [0] * len(TAP_SEQ)
        for i, _ in v["log"]:
            taps[i] += 1
        hits = sum(1 for i, d in enumerate(TAP_SEQ) if d == "1" and taps[i] > 0)
        omissions = sum(1 for i, d in enumerate(TAP_SEQ) if d == "1" and taps[i] == 0)
        commissions = sum(taps[i] for i, d in enumerate(TAP_SEQ) if d != "1")
        errors = omissions + commissions; ok = errors < 2
        lat = [ms for i, ms in v["log"] if TAP_SEQ[i] == "1"]
        log("tapping", "sequence", TAP_SEQ, None, None, ok, int(ok),
            {"hits": hits, "omissions": omissions, "commissions": commissions, "errors": errors,
             "mean_hit_latency_ms": round(sum(lat) / len(lat)) if lat else None, "tap_log": v["log"]})
        ss.scores["tap"] = int(ok); nxt()

elif step == "serial":
    st.subheader("③ 由 100 開始連續減 7  Count down from 100 by 7")
    if "s7_res" not in ss:
        with st.form("s7_form"):
            cols = st.columns(5)
            raw = [c.text_input(f"第 {i+1} 個", key=f"s7_{i}", max_chars=3) for i, c in enumerate(cols)]
            if st.form_submit_button("✔ 完成 Done"):
                ans = [int(r) if r.strip().lstrip("-").isdigit() else None for r in raw]
                prev, corr = 100, []
                for i, x in enumerate(ans):        # MoCA rule: each answer judged against the previous answer given
                    corr.append(x is not None and x == prev - 7)
                    prev = x if x is not None else prev - 7
                n = sum(corr); score = 3 if n >= 4 else 2 if n >= 2 else 1 if n == 1 else 0
                for i, x in enumerate(ans):
                    log("serial7", f"s7_{i+1}", 100 - 7 * (i + 1), raw[i], x, corr[i], None,
                        {"strict_correct": x == 100 - 7 * (i + 1)})
                log("serial7", "total", "5 items", None, None, None, score, {"n_correct": n})
                ss.scores["serial"] = score; ss.s7_res = ans; st.rerun()
    else:
        for i, x in enumerate(ss.s7_res):
            st.markdown(f'<span class="chip" style="animation-delay:{i*0.45}s">{x if x is not None else "–"}</span>', unsafe_allow_html=True)
        st.balloons()
        if st.button("下一步 Next ➜", type="primary"):
            nxt()

elif step == "orient":
    st.subheader("④ 我的日記 My Diary")
    now = datetime.now(HK)
    if "diary" not in ss:
        with st.form("ori"):
            c = st.columns(4)
            d = c[0].selectbox("日 Day", range(1, 32), index=None)
            m = c[1].selectbox("月 Month", range(1, 13), index=None)
            y = c[2].number_input("年 Year", 1900, 2100, value=None, step=1)
            w = c[3].selectbox("星期 Weekday", WEEKDAYS, index=None)
            place = st.text_input("📍 地點 Place"); region = st.text_input("地區 Region")
            if st.form_submit_button("✔ 完成 Done"):
                def norm(s): return s.strip().lower()
                def match(resp, key):
                    if not norm(key): return None
                    return bool(norm(resp)) and (norm(key) in norm(resp) or norm(resp) in norm(key))
                items = [("day", now.day, d, d == now.day), ("month", now.month, m, m == now.month),
                         ("year", now.year, y, y is not None and int(y) == now.year),
                         ("weekday", WEEKDAYS[now.weekday()], w, w == WEEKDAYS[now.weekday()]),
                         ("place", ss.exp_place, place, match(place, ss.exp_place)),
                         ("region", ss.exp_region, region, match(region, ss.exp_region))]
                for name, exp, resp, ok in items:
                    log("orientation", name, exp, resp, None, ok, None if ok is None else int(ok))
                ss.scores["orient"] = sum(1 for *_, ok in items if ok)
                ss.diary = dict(d=d, m=m, y=y, w=w, place=place, region=region, em=random.choice(EMOJIS)); st.rerun()
    else:
        g = ss.diary
        st.markdown(f'<div class="diary"><b>Date:</b> {g["d"]:02d} / {g["m"]:02d} / {int(g["y"])} ({g["w"]})<hr>'
                    f'<b>📍 Location:</b> {g["place"]} , {g["region"]}<hr><div class="em">{g["em"]}</div></div>', unsafe_allow_html=True)
        st.balloons()
        if st.button("完成 Finish ➜", type="primary"):
            nxt()

else:
    st.success("🎉 多謝你！Thank you!")
    s = ss.scores
    st.write(f"**Attention** {s.get('fwd',0)+s.get('bwd',0)+s.get('tap',0)+s.get('serial',0)}/6 · **Orientation** {s.get('orient',0)}/6 (tester view)")
    st.dataframe(load(session_only=True).drop(columns=["id", "session"]), use_container_width=True)
