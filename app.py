import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
import time

st.set_page_config(page_title="MoCA Interactive Assessment", layout="centered")

st.title("🧠 MoCA Digital Assessment - Attention & Memory Games")

# Initialize Session States for Scores
if "ds_forward_score" not in st.session_state:
    st.session_state.ds_forward_score = 0
if "ds_backward_score" not in st.session_state:
    st.session_state.ds_backward_score = 0
if "vigilance_score" not in st.session_state:
    st.session_state.vigilance_score = 0

tabs = st.tabs(["1. 數字重複 (Digit Span)", "2. 聽數反應 (Vigilance Test)", "3. 定向測試 (Orientation)"])

def create_digit_audio(digit_list, lang='zh-tw'):
    # Adds spaces between numbers to force slow, 1-second cadence
    spoken_text = " . ".join(map(str, digit_list))
    tts = gTTS(text=spoken_text, lang=lang, slow=True)
    
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp


# ==========================================
# TAB 1: DIGIT SPAN (FORWARD & BACKWARD)
# ==========================================
with tabs[0]:
    st.header("🎮 1. 數字重複遊戲 (Digit Memory Game)")
st.write("請按下方按鈕播放語音導讀，然後輸入或複述聽到的數字。")

mode = st.radio("選擇測試內容:", ["向前重複 [ 2 1 8 5 4 ]", "向後重複 [ 7 4 2 ]"])

if "向前" in mode:
    digits = [2, 1, 8, 5, 4]
    target_str = "21854"
else:
    digits = [7, 4, 2]
    target_str = "742"

st.subheader("🔊 語音播放 (Voice Audio)")

# 1. Native Streamlit Audio Player
audio_bytes = create_digit_audio(digits, lang='zh-tw')
st.audio(audio_bytes, format='audio/mp3')

st.caption("💡 提示：點擊上方播放按鈕，系統將以每秒一個數字的節奏朗讀。")

st.markdown("---")

# 2. Interactive Animated Display for Spoken/Entered Response
st.subheader("🗣️ 病人回答區 (Patient Response)")

user_input = st.text_input("輸入病人回答的數字 (例如: 21854):", key="digit_input")

# Dynamic Animated Number Pop-up
if user_input:
    st.write("病人的回答 (視覺化顯示):")
    cols = st.columns(len(user_input))
    for idx, char in enumerate(user_input):
        with cols[idx]:
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, #FF6B6B, #FF8E53);
                    color: white;
                    font-size: 36px;
                    font-weight: bold;
                    text-align: center;
                    border-radius: 50%;
                    width: 65px;
                    height: 65px;
                    line-height: 65px;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.2);
                    margin: auto;
                    animation: pop 0.3s ease-out;
                ">
                    {char}
                </div>
                """,
                unsafe_allow_html=True
            )

if st.button("提交並核對分數"):
    if user_input.strip() == target_str:
        st.success("✅ 回答正確！得分: 1分")
    else:
        st.error(f"❌ 回答錯誤。正確答案應為: {target_str}")
    
# ==========================================
# TAB 2: VIGILANCE TEST (TAP ON '1')
# ==========================================
with tabs[1]:
    st.header("🔔 聽數字敲擊遊戲 (Vigilance Test)")
    st.write("規則：當聽到數字 **'1'** 時，請立即按下「敲擊桌面 / TAP!」按鈕！(錯誤 ≥2 次不給分)")
    
    vigilance_seq = [5, 2, 1, 3, 7, 4, 1, 1, 8, 0, 6, 2, 1, 5, 1, 7, 4, 5, 1, 1, 1, 4, 1, 7, 0, 5, 1, 1, 2]
    
    if st.button("▶️ 開始聽數反應遊戲"):
        st.session_state.taps = []
        st.session_state.game_running = True
        
        status_placeholder = st.empty()
        display_placeholder = st.empty()
        
        errors = 0
        correct_taps = 0
        
        for idx, num in enumerate(vigilance_seq):
            # Animated Visual Display
            display_placeholder.markdown(
                f"""
                <div style="display:flex; justify-content:center; align-items:center; height:150px;">
                    <div style="font-size: 80px; font-weight: bold; color: #1E88E5; 
                                border: 4px solid #1E88E5; border-radius: 50%; width: 120px; height: 120px;
                                display: flex; align-items: center; justify-content: center;
                                box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                        {num}
                    </div>
                </div>
                """, 
                unsafe_allow_html=True
            )
            time.sleep(1.0) # 1 digit per second rule
            
        display_placeholder.success("🎉 測驗完成！")
        
    st.number_input("記錄病人錯誤次數 (漏敲 / 誤敲):", min_value=0, max_value=30, value=0, key="vig_errors")
    
    if st.button("計算聽數得分"):
        if st.session_state.vig_errors < 2:
            st.session_state.vigilance_score = 1
            st.success("✅ 得分：1分 (錯誤少於 2 次)")
        else:
            st.session_state.vigilance_score = 0
            st.error("❌ 得分：0分 (錯誤 ≥ 2 次)")

# ==========================================
# TAB 3: ORIENTATION (定向測試)
# ==========================================
with tabs[2]:
    st.header("🧩 定向測試 (Orientation)")
    st.write("請選擇或回答當前的日期與地點資訊（共 6 分）。")
    
    c1, c2 = st.columns(2)
    with c1:
        date_ans = st.number_input("1. 日 (Date):", min_value=1, max_value=31)
        month_ans = st.number_input("2. 月 (Month):", min_value=1, max_value=12)
        year_ans = st.number_input("3. 年 (Year):", min_value=2020, max_value=2030, value=2026)
    with c2:
        day_ans = st.selectbox("4. 星期 (Day of week):", ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"])
        place_ans = st.text_input("5. 地點 (Location/Hospital):")
        city_ans = st.text_input("6. 地區/城市 (City/District):")
        
    if st.button("提交定向測試結果"):
        st.success("定向評估結果已記錄！")
