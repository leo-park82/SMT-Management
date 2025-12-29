import streamlit as st
import utils

st.set_page_config(page_title="기준정보", page_icon="⚙", layout="wide")
utils.check_auth_status()
utils.render_sidebar()

if st.session_state.user_info['role'] == 'admin':
    t1, t2, t3 = st.tabs(["📦 품목 기준정보", "🏭 설비 기준정보", "✅ 일일점검 기준정보"])
    with t1:
        st.markdown("#### 품목 마스터 관리")
        df = utils.load_data(utils.SHEET_ITEMS, utils.COLS_ITEMS)
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="item_master")
        if st.button("품목 저장"): 
            utils.save_data(edited, utils.SHEET_ITEMS)
            st.rerun()
    with t2:
        st.markdown("#### 설비 마스터 관리")
        df = utils.load_data(utils.SHEET_EQUIPMENT, utils.COLS_EQUIPMENT)
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="eq_master")
        if st.button("설비 저장"): 
            utils.save_data(edited, utils.SHEET_EQUIPMENT)
            st.rerun()
    with t3:
        st.markdown("#### 일일점검 항목 관리")
        df = utils.load_data(utils.SHEET_CHECK_MASTER, utils.COLS_CHECK_MASTER)
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="check_master")
        if st.button("점검 기준 저장"): 
            utils.save_data(edited, utils.SHEET_CHECK_MASTER)
            st.rerun()
else:
    st.error("🚫 접근 권한이 없습니다. (관리자 전용)")