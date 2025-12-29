import streamlit as st
import utils
import os

# ------------------------------------------------------------------
# 1. 기본 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="SMT", page_icon="🏭", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; color: #1e293b; }
    .stApp { background-color: #f8fafc; }
    </style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# 2. 사용자 인증 정보 (ID/PW 설정)
# ------------------------------------------------------------------
USERS = {
    "cimon": {"name": "관리자", "password_hash": utils.make_hash("7801083"), "role": "admin"},
    "박종선": {"name": "박종선", "password_hash": utils.make_hash("1083"), "role": "worker"},
    "김윤석": {"name": "김윤석", "password_hash": utils.make_hash("1734"), "role": "worker"},
    "김명숙": {"name": "김명숙", "password_hash": utils.make_hash("8943"), "role": "worker"}
}

def check_login():
    if "logged_in" not in st.session_state: 
        st.session_state.logged_in = False
    
    # 이미 로그인 된 경우
    if st.session_state.logged_in:
        return True
    
    # URL 파라미터 자동 로그인 처리 (선택 사항)
    try:
        qp = st.query_params
        if "session" in qp:
            saved_id = qp["session"]
            if saved_id in USERS:
                st.session_state.logged_in = True
                st.session_state.user_info = USERS[saved_id]
                st.session_state.user_info['id'] = saved_id
                return True
            elif saved_id == "guest":
                st.session_state.logged_in = True
                st.session_state.user_info = {"name": "게스트", "role": "viewer", "id": "guest"}
                return True
    except: pass

    # --- 로그인 UI ---
    col1, col2, col3 = st.columns([4, 3, 4])
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        st.title("SMT Smart System")
        
        with st.form("login"):
            id = st.text_input("ID")
            pw = st.text_input("PW", type="password")
            
            if st.form_submit_button("로그인", use_container_width=True):
                if id in USERS and utils.make_hash(pw) == USERS[id]["password_hash"]:
                    st.session_state.logged_in = True
                    st.session_state.user_info = USERS[id]
                    st.session_state.user_info['id'] = id
                    # 세션 파라미터 저장 (선택)
                    try: st.query_params["session"] = id
                    except: pass
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 잘못되었습니다.")
        
        if st.button("👀 게스트(뷰어)로 입장", use_container_width=True):
            st.session_state.logged_in = True
            st.session_state.user_info = {"name": "게스트", "role": "viewer", "id": "guest"}
            try: st.query_params["session"] = "guest"
            except: pass
            st.rerun()
            
    return False

# ------------------------------------------------------------------
# 메인 실행 로직
# ------------------------------------------------------------------
if check_login():
    # 로그인 성공 시 공통 사이드바 렌더링
    utils.render_sidebar()
    
    st.info("👈 왼쪽 사이드바에서 원하는 메뉴를 선택하세요.")
    
    st.markdown("### 🏠 SMT 생산현황 대시보드")
    
    if "user_info" in st.session_state:
        u = st.session_state.user_info
        role_text = "관리자" if u['role'] == 'admin' else "사용자"
        st.success(f"환영합니다! **{u['name']}**님 ({role_text} 모드)")
    
    st.markdown("""
    ---
    **📌 주요 기능 안내**
    - **📊 대시보드**: 실시간 생산량, 설비 가동 현황, 이슈 사항을 한눈에 확인합니다.
    - **🏭 생산관리**: 생산 실적을 등록하고 재고를 관리합니다.
    - **🛠 설비보전**: 설비 고장/수리 내역을 기록하고 분석합니다.
    - **✅ 일일점검**: 매일 설비 점검표를 작성하고 리포트를 출력합니다.
    """)

    # 캐시 초기화 버튼 (데이터 갱신용)
    if st.button("🔄 데이터 새로고침 (캐시 삭제)"):
        utils.clear_cache()
        st.toast("데이터를 최신 상태로 갱신했습니다.", icon="✅")