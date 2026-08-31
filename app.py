import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import re

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

# 테마 스타일 적용
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

# 3. Gemini AI 설정 (기존에 작성하셨던 본인 키 복원)
genai.configure(api_key="AQ.Ab8RN6LiTRbzvEqsaYGS7o-RZwm5C2TK1hrrUCd2nVKiCxUi9Q")

# 4. 데이터 저장 세션 초기화
if 'time_records' not in st.session_state:
    st.session_state.time_records = {}
if 'history_stack' not in st.session_state:
    st.session_state.history_stack = []

# 5. UI: 시간 선택 및 파일 업로드
time_options = [f"{i:02d}시" for i in range(24)]
target_time = st.selectbox("🕒 촬영 시간 선택", time_options, index=20)

uploaded_file = st.file_uploader(
    "📸 현장 모니터 사진 업로드 (1장씩 추가)", 
    type=["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]
)

# 6. 데이터 분석 및 저장 로직
if st.button("📥 현재 시간 데이터 추가 및 분석"):
    if not uploaded_file:
        st.error("❌ 모니터 사진을 업로드해주세요.")
    else:
        with st.spinner(f"AI가 {target_time} 데이터를 분석하는 중..."):
            try:
                img = Image.open(uploaded_file).convert('RGB')
                img.thumbnail((1024, 1024))
                
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
                
                # 안전한 JSON 추출
                json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
                if json_match:
                    clean_text = json_match.group(0)
                else:
                    clean_text = response.text.strip()

                parsed_data = json.loads(clean_text)
                
                # 데이터 업데이트
                st.session_state.time_records[target_time] = {
                    item['equipment']: {
                        'qty': int(item['quantity']),
                        'yield': float(item['yield'])
                    } for item in parsed_data
                }
                
                # 히스토리 저장
                if target_time in st.session_state.history_stack:
                    st.session_state.history_stack.remove(target_time)
                st.session_state.history_stack.append(target_time)
                
                st.success(f"✨ {target_time} 데이터가 성공적으로 축적되었습니다!")
            except Exception as e:
                st.error(f"⚠️ 데이터 처리 중 오류 발생: {str(e)}")

# 7. 변동 분석 표 출력 및 취소/초기화 버튼
if st.session_state.time_records and st.session_state.history_stack:
    st.markdown("---")
    st.markdown("### 📈 STK 생산량 및 수율 변동 분석")
    
    recorded_times = st.session_state.history_stack
    
    curr_time = recorded_times[-1]
    prev_time = recorded_times[-2] if len(recorded_times) >= 2 else curr_time
    
    prev_data = st.session_state.time_records.get(prev_time, {})
    curr_data = st.session_state.time_records.get(curr_time, {})
    
    all_equipments = sorted(list(set(list(prev_data.keys()) + list(curr_data.keys()))))
    
    table_rows = []
    for eq in all_equipments:
        p_info = prev_data.get(eq, {'qty': 0, 'yield': 0.0})
        c_info = curr_data.get(eq, {'qty': 0, 'yield': 0.0})
        
        qty_diff = c_info['qty'] - p_info['qty']
        qty_diff_str = f"+{qty_diff}" if qty_diff > 0 else f"{qty_diff}"
        
        yield_diff = c_info['yield'] - p_info['yield']
        if yield_diff > 0:
            yield_diff_str = f"📈 +{yield_diff:.2f}% p"
        elif yield_diff < 0:
            yield_diff_str = f"📉 {yield_diff:.2f}% p"
        else:
            yield_diff_str = "0.00% p"
            
        prev_cell = f"{p_info['qty']} / {p_info['yield']:.2f} %" if p_info['qty'] > 0 else "-"
        curr_cell = f"{c_info['qty']} / {c_info['yield']:.2f} %" if c_info['qty'] > 0 else "-"
        
        table_rows.append({
            "설비명": eq,
            f"{prev_time} 데이터 (수량 / 수율)": prev_cell,
            f"{curr_time} 데이터 (수량 / 수율)": curr_cell,
            "1시간 생산량 변동": qty_diff_str,
            "1시간 대비 수율 변동": yield_diff_str
        })
        
    result_df = pd.DataFrame(table_rows)
    st.dataframe(result_df, use_container_width=True, hide_index=True)

    col_undo, col_reset = st.columns([1, 1])
    
    with col_undo:
        if st.button(f"↩️ 최근 등록({curr_time}) 취소"):
            last_time = st.session_state.history_stack.pop()
            if last_time in st.session_state.time_records:
                del st.session_state.time_records[last_time]
            st.rerun()

    with col_reset:
        if st.button("🗑️ 전체 데이터 초기화"):
            st.session_state.time_records = {}
            st.session_state.history_stack = []
            st.rerun()
