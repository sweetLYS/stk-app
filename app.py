import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json

# 1. 화면 기본 설정
st.set_page_config(
    page_title="STK 누적 수율 분석기",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. 테마 (다크 / 라이트 모드) 세션 관리
if 'theme_mode' not in st.session_state:
    st.session_state.theme_mode = 'Dark'

col_title, col_toggle = st.columns([0.85, 0.15])
with col_title:
    st.markdown('<p style="font-size:24px; font-weight:bold; margin:0; padding-top:5px;">📊 STK 누적 분석</p>', unsafe_allow_html=True)
with col_toggle:
    toggle_icon = "🌕" if st.session_state.theme_mode == 'Dark' else "🌙"
    if st.button(toggle_icon):
        st.session_state.theme_mode = 'White' if st.session_state.theme_mode == 'Dark' else 'Dark'

# 테마에 따른 스타일 정의
bg_color = "#121212" if st.session_state.theme_mode == 'Dark' else "#FFFFFF"
text_color = "#FFFFFF" if st.session_state.theme_mode == 'Dark' else "#000000"
table_bg = "#1E1E1E" if st.session_state.theme_mode == 'Dark' else "#F5F5F5"

st.markdown(f"""
    <style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    div[data-testid="stMarkdownContainer"] table {{
        font-size: 13px !important;
        width: 100% !important;
        background-color: {table_bg};
        color: {text_color};
    }}
    div[data-testid="stMarkdownContainer"] th, div[data-testid="stMarkdownContainer"] td {{
        padding: 8px 10px !important;
        border-bottom: 1px solid #333333;
    }}
    div[data-testid="stHorizontalBlock"] div.stButton > button {{
        background: transparent !important;
        border: none !important;
        font-size: 24px !important;
        padding: 0 !important;
        margin-top: 5px !important;
        cursor: pointer;
    }}
    div.stForm + div.stButton > button, div.main div.stButton > button:first-child {{
        height: 3em !important;
        font-size: 16px !important;
        font-weight: bold !important;
        background-color: #4A90E2 !important;
        color: white !important;
        border-radius: 10px;
        width: 100%;
    }}
    </style>
""", unsafe_allow_html=True)

st.markdown('<p style="font-size:13px; color:#888;">오후 8시 ~ 오전 6시 생산 수율 누적 시스템</p>', unsafe_allow_html=True)

# 3. Gemini AI 설정 (발급받으신 본인의 API Key를 입력하세요)
genai.configure(api_key="YOUR_GEMINI_API_KEY")

# 4. 데이터 저장용 세션 상태 초기화
if 'time_records' not in st.session_state:
    st.session_state.time_records = {}
if 'history_stack' not in st.session_state:
    st.session_state.history_stack = []

# 5. UI: 촬영 시간 선택 및 업로드
time_options = [f"{i:02d}시" for i in range(24)]
target_time = st.selectbox("🕒 촬영 시간 선택", time_options, index=20)

uploaded_file = st.file_uploader(
    "📸 현장 모니터 사진 업로드 (1장씩 추가)", 
    type=["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]
)

# 6. 데이터 분석 및 추가 로직
if st.button("📥 현재 시간 데이터 추가 및 분석"):
    if not uploaded_file:
        st.error("❌ 모니터 사진을 업로드해주세요.")
    else:
        with st.spinner(f"AI가 {target_time} 데이터를 분석하는 중..."):
            try:
                img = Image.open(uploaded_file).convert('RGB')
                img.thumbnail((1024, 1024))
                
                # 수량과 수율을 동시에 파싱하도록 프롬프트 작성
                prompt = """
                제공된 공정 모니터 사진에서 STK 공정 설비별 '생산 수량'과 '수율(%)'을 추출하세요.
                반드시 아래 JSON 형식으로만 응답하세요. 다른 설명은 절대 추가하지 마세요.

                [
                  {"equipment": "STK #02-01", "quantity": 442, "yield": 99.36},
                  {"equipment": "STK #02-02", "quantity": 312, "yield": 99.41}
                ]
                """
                
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content([prompt, img])
                
                clean_text = response.text.strip().replace("```json", "").replace("
