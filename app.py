import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd

# 1. 화면 기본 설정
st.set_page_config(
    page_title="STK 누적 수율 분석기",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. 다크 모드 / 화이트 모드 상태 기억하기
if 'theme_mode' not in st.session_state:
    st.session_state.theme_mode = 'Dark'

# 상단 레이아웃 (제목과 달 모양 버튼을 한 줄에 배치)
col_title, col_toggle = st.columns([0.85, 0.15])
with col_title:
    st.markdown('<p style="font-size:24px; font-weight:bold; margin:0; padding-top:5px;">📊 STK 누적 분석</p>', unsafe_allow_html=True)
with col_toggle:
    toggle_icon = "🌕" if st.session_state.theme_mode == 'Dark' else "🌙"
    if st.button(toggle_icon):
        st.session_state.theme_mode = 'White' if st.session_state.theme_mode == 'Dark' else 'Dark'

# 테마에 따른 화면 및 표 색상 실시간 반영 (CSS)
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
        padding: 5px 6px !important;
        border: 1px solid #444444;
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

# 3. Gemini AI 설정
genai.configure(api_key="AQ.Ab8RN6LiTRbzvEqsaYGS7o-RZwm5C2TK1hrrUCd2nVKiCxUi9Q")

# 4. 데이터 축적을 위한 저장소(세션) 생성
if 'yield_data' not in st.session_state:
    st.session_state.yield_data = []

# 5. UI: 00시부터 23시까지 드롭다운 목록 생성 및 업로드
time_options = [f"{i:02d}시" for i in range(24)]  # ['00시', '01시', ..., '23시'] 자동 생성
target_time = st.selectbox("🕒 촬영 시간 선택", time_options, index=20)  # 기본값: 20시

uploaded_file = st.file_uploader(
    "📸 현장 모니터 사진 업로드 (1장씩 추가)", 
    type=["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]
)

# 6. [데이터 추가] 버튼 작동 로직
if st.button("📥 현재 시간 데이터 추가 및 분석"):
    if not uploaded_file:
        st.error("❌ 모니터 사진을 업로드해주세요.")
    else:
        with st.spinner(f"AI가 {target_time} 데이터를 읽어오는 중..."):
            try:
                # 핸드폰 사진 포맷/회전 고려 RGB 변환 및 압축
                img = Image.open(uploaded_file).convert('RGB')
                img.thumbnail((1024, 1024))
                
                prompt = """
                제공된 공정 모니터 사진에서 STK 공정(#02-01 ~ #04-01)의 수율(%) 데이터를 전부 찾으세요.
                오직 항목 이름과 수율 값만 줄바꿈 형태로 출력하세요. 다른 텍스트는 절대 적지 마세요.
                
                예시:
                STK #02-01: 99.44%
                STK #02-02: 99.33%
                """
                
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content([prompt, img])
                
                lines = response.text.strip().split('\n')
                for line in lines:
                    if "STK" in line and ":" in line:
                        parts = line.split(":")
                        item = parts[0].strip()
                        yield_val = parts[1].strip()
                        st.session_state.yield_data.append({
                            "시간": target_time,
                            "항목": item,
                            "수율": yield_val
                        })
                st.success(f"✨ {target_time} 데이터가 성공적으로 축적되었습니다!")
            except Exception as e:
                st.error(f"⚠️ 오류 발생: {str(e)}")

# 7. 실시간 타임라인 누적 표 출력
if st.session_state.yield_data:
    st.markdown("---")
    st.markdown("### 📱 STK 타임라인 누적 요약 표")
    df = pd.DataFrame(st.session_state.yield_data)
    try:
        df_pivot = df.pivot(index='항목', columns='시간', values='수율').fillna("-")
        st.dataframe(df_pivot, use_container_width=True)
    except Exception as e:
        st.warning("데이터 정렬 중 잠시 지연이 발생했습니다. 다음 사진을 등록해 주세요.")

    if st.button("🗑️ 전체 데이터 초기화 (출근 시 새로 시작)"):
        st.session_state.yield_data = []
        st.rerun()
