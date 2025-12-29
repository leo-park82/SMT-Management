import streamlit as st
import utils

# 1. 페이지 기본 설정 (가장 먼저 실행)
st.set_page_config(page_title="SMT Smart System", page_icon="🧠", layout="wide")

# 2. 스타일 로드 및 세션 초기화
utils.init_session()
utils.load_style()

# 3. 로그인 체크
if not utils.check_login():
    utils.render_login()
    st.stop()

# 4. 상단 헤더 (로그아웃 버튼 포함)
c1, c2 = st.columns([8, 2])
with c1:
    st.markdown("## 🧠 SMT SMART SYSTEM")
with c2:
    # 우측 상단에 로그인 정보 및 로그아웃 표시
    utils.render_user_header()

# 5. 메인 탭 구성
tab_dashboard, tab_prod, tab_maint, tab_daily = st.tabs([
    "📊 대시보드",
    "🏭 생산관리",
    "🛠 설비보전",
    "📋 일일점검"
])

# 6. 각 탭별 렌더링 함수 호출
with tab_dashboard:
    utils.render_dashboard()

with tab_prod:
    utils.render_production()

with tab_maint:
    utils.render_maintenance()

with tab_daily:
    utils.render_daily_check()