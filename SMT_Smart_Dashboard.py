import streamlit as st
import utils

# 1. 페이지 기본 설정 (가장 먼저 실행)
st.set_page_config(
    page_title="SMT Smart System", 
    page_icon="🧠", 
    layout="wide"
)

# 2. 세션 초기화
utils.init_session()

# 3. 로그인 체크 (핵심: 로그인 안 되어 있으면 여기서 멈춤 - 잔상 제거)
if not utils.check_login():
    utils.render_login()
    st.stop()  # ⛔ 여기서 코드 실행 중단

# ------------------------------------------------------------------
# 4. 로그인 성공 시에만 실행되는 영역
# ------------------------------------------------------------------

# 스타일 로드 (사이드바 제거 CSS 포함)
utils.load_style()

# 5. 스마트 헤더 렌더링 (타이틀 + 유저정보 + 로그아웃)
utils.render_header()

# 6. 메인 탭 구성
tab_dashboard, tab_prod, tab_maint, tab_daily = st.tabs([
    "📊 대시보드",
    "🏭 생산관리",
    "🛠 설비보전",
    "📋 일일점검"
])

# 7. 각 탭별 화면 렌더링 (utils에 있는 함수 호출)
with tab_dashboard:
    utils.render_dashboard()

with tab_prod:
    utils.render_production()

with tab_maint:
    utils.render_maintenance()

with tab_daily:
    utils.render_daily_check()