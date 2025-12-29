import streamlit as st
import utils

# 1. 페이지 설정 (레이아웃 와이드, 아이콘 설정)
st.set_page_config(page_title="SMT Smart System", layout="wide", page_icon="🏭")

# 2. 사이드바 완전 제거를 위한 CSS 적용
# Streamlit의 기본 사이드바 영역과 햄버거 메뉴 등을 숨깁니다.
hide_sidebar_style = """
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="stSidebarCollapsedControl"] {display: none;}
        section[data-testid="stSidebar"] {display: none;}
    </style>
"""
st.markdown(hide_sidebar_style, unsafe_allow_html=True)

# 3. 로그인 체크
# 세션 상태를 확인하여 로그인이 안 되어 있으면 로그인 화면만 표시하고 중단합니다.
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    utils.render_login()
    st.stop() # 로그인 전에는 아래 코드를 실행하지 않음

# 4. 메인 헤더 (로고 및 타이틀)
c1, c2 = st.columns([0.1, 0.9])
with c1:
    # 로고 파일이 있다면 표시, 없으면 텍스트
    st.markdown("## 🏭") 
with c2:
    st.markdown("## SMT SMART SYSTEM")
    st.caption(f"접속자: {st.session_state.get('user_name', 'Unknown')} | 권한: {st.session_state.get('role', 'User')}")

st.divider()

# 5. 상단 탭 구성 (메인 네비게이션)
tab_dashboard, tab_prod, tab_maint, tab_daily = st.tabs([
    "📊 대시보드",
    "🏭 생산관리",
    "🛠 설비보전",
    "📋 일일점검"
])

# 각 탭별 내용 렌더링 (utils.py에 구현)
with tab_dashboard:
    utils.render_dashboard()

with tab_prod:
    utils.render_production()

with tab_maint:
    utils.render_maintenance()

with tab_daily:
    utils.render_daily_check()