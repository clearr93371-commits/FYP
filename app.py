import streamlit as st
import streamlit.components.v1 as components

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

# def create_digit_audio(digit_list, lang='zh-tw'):
#     # Adds spaces between numbers to force slow, 1-second cadence
#     spoken_text = " . ".join(map(str, digit_list))
#     tts = gTTS(text=spoken_text, lang=lang, slow=True)
    
#     fp = io.BytesIO()
#     tts.write_to_fp(fp)
#     fp.seek(0)
#     return fp


# ==========================================
# TAB 1: DIGIT SPAN (FORWARD & BACKWARD)
# ==========================================
with tabs[0]:
    st.header("🎮 數字重複遊戲 (Digit Memory Game)")
    st.write("請聆聽系統朗讀的數字，然後按順序（或倒序）複述。")
    
    mode = st.radio("選擇模式:", ["向前重複 (2 1 8 5 4)", "向後重複 (7 4 2)"])
    
    target_seq = [2, 1, 8, 5, 4] if "向前" in mode else [7, 4, 2]
    target_str = "".join(map(str, target_seq))
    
    col1, col2 = st.columns(2)
    
    with col1:
        # TTS Audio Playback JS Component
        js_speech = f"""
            <script>
            function readNumbers() {{
                const numbers = {target_seq};
                let i = 0;
                function speakNext() {{
                    if (i < numbers.length) {{
                        let msg = new SpeechSynthesisUtterance(numbers[i].toString());
                        msg.lang = 'zh-HK'; // Cantonese voice, change to 'zh-CN' or 'en-US' if needed
                        msg.rate = 0.8;    // 1 digit per second rate
                        window.speechSynthesis.speak(msg);
                        i++;
                        setTimeout(speakNext, 1100);
                
                }}
                speakNext();
            }}
            </script>
            <button onclick="readNumbers()" style="padding: 10px 20px; font-size: 18px; background-color: #4CAF50; color: white; border: none; border-radius: 8px; cursor: pointer;">
                🔊 播放語音數字 (每秒一個)
            </button>
        """
        components.html(js_speech, height=70)
    
    st.subheader("🗣️ 患者回答區 (Speak or Enter Response)")
    
    # Custom Animated Speech Display Component
    speech_component = """
    <style>
        .container { display: flex; gap: 10px; margin-top: 15px; min-height: 80px; }
        .number-bubble {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #FF6B6B, #FF8E53);
            color: white;
            font-size: 32px;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            animation: popup 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        }
        @keyframes popup {
            0% { transform: scale(0) translateY(20px); opacity: 0; }
            100% { transform: scale(1) translateY(0); opacity: 1; }
        }
    </style>
    <div id="speech-bubbles" class="container"></div>

    <script>
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;
    
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.lang = 'zh-HK';
        
        recognition.onresult = (event) => {
            const container = document.getElementById('speech-bubbles');
            container.innerHTML = '';
            const transcript = event.results[event.results.length - 1][0].transcript;
            const digits = transcript.replace(/[^0-9]/g, '');
            
            for (let char of digits) {
                let bubble = document.createElement('div');
                bubble.className = 'number-bubble';
                bubble.innerText = char;
                container.appendChild(bubble);
            }
        };
    }
    
    function startListening() {
        if (recognition) recognition.start();
        else alert("Browser does not support direct Web Speech API");
    }
    </script>
    <button onclick="startListening()" style="padding: 10px 20px; font-size: 16px; background-color: #2196F3; color: white; border: none; border-radius: 8px; cursor: pointer;">
        🎙️ 開始語音識別 (Voice Input)
    </button>
    """
    components.html(speech_component, height=160)
    
    user_input = st.text_input("或直接輸入回答數字 (供測試/人工核對):", key="ds_input")
    
    if st.button("提交並計分"):
        clean_input = user_input.strip()
        if clean_input == target_str:
            st.success("✅ 回答正確！ (+1分)")
            if "向前" in mode:
                st.session_state.ds_forward_score = 1
            else:
                st.session_state.ds_backward_score = 1
        else:
            st.error(f"❌ 回答不正確。目標為: {target_str}")
            if "向前" in mode:
                st.session_state.ds_forward_score = 0
            else:
                st.session_state.ds_backward_score = 0

    st.info(f"**數字記憶得分**: {st.session_state.ds_forward_score + st.session_state.ds_backward_score} / 2")
    
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
