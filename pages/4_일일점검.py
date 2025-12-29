import streamlit as st
import utils
import pandas as pd
import time
import streamlit.components.v1 as components

st.set_page_config(page_title="일일점검", page_icon="✅", layout="wide")
utils.check_auth_status()
utils.render_sidebar()

t1, t2, t3 = st.tabs(["✍ 점검 입력", "📊 현황", "📄 리포트"])

with t1:
    if st.session_state.get('scroll_to_top'):
        components.html("""<script>window.parent.scrollTo({top: 0, behavior: 'smooth'});</script>""", height=0)
        st.session_state['scroll_to_top'] = False

    c_date, c_line = st.columns([1, 2])
    with c_date:
        sel_date = st.date_input("점검 일자", utils.get_now(), key="check_date_input")
    
    df_res = utils.load_data(utils.SHEET_CHECK_RESULT, utils.COLS_CHECK_RESULT)
    df_master = utils.load_data(utils.SHEET_CHECK_MASTER, utils.COLS_CHECK_MASTER)
    
    if df_master.empty: st.warning("점검 항목이 없습니다.")
    else:
        lines = df_master['line'].unique()
        with c_line: sel_line = st.selectbox("라인 선택", lines)
        
        line_data = df_master[df_master['line'] == sel_line]
        total_items = len(line_data)
        checked_count = 0
        
        if not df_res.empty:
            df_res['date_only'] = df_res['date'].astype(str).str.split().str[0]
            status_df = df_res[(df_res['date_only'] == str(sel_date)) & (df_res['line'] == sel_line)]
            if not status_df.empty:
                checked_count = len(status_df.drop_duplicates(['equip_id', 'item_name']))

        if checked_count == 0: st.error(f"❌ {sel_date} : 점검 미실시 (0/{total_items})")
        elif checked_count < total_items: st.warning(f"⚠️ {sel_date} : 점검 진행 중 ({checked_count}/{total_items})")
        else: st.success(f"✅ {sel_date} : 점검 완료 ({checked_count}/{total_items})")

        prev_data = {}
        if not df_res.empty:
            df_filtered = df_res[(df_res['date_only'] == str(sel_date)) & (df_res['line'] == sel_line)]
            if not df_filtered.empty:
                df_filtered = df_filtered.sort_values('timestamp').drop_duplicates(['equip_id', 'item_name'], keep='last')
                for _, r in df_filtered.iterrows():
                    prev_data[f"{r['equip_id']}_{r['item_name']}"] = {'val': r['value'], 'ox': r['ox'], 'memo': r.get('비고', '')}

        st.markdown(f"##### 📝 {sel_line} 점검 입력")
        is_viewer = st.session_state.user_info['role'] == 'viewer'

        for equip_name, group in line_data.groupby("equip_name", sort=False):
            with st.container(border=True):
                st.markdown(f"**🛠 {equip_name}**")
                for _, row in group.iterrows():
                    uid = f"{row['equip_id']}_{row['item_name']}"
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.markdown(f"**{row['item_name']}**\n<span style='color:gray;font-size:0.9em'>{row['check_content']}</span>", unsafe_allow_html=True)
                    
                    key_val = f"v_{uid}_{sel_date}"
                    key_memo = f"m_{uid}_{sel_date}"
                    prev = prev_data.get(uid, {})
                    
                    is_ng_condition = False
                    with c2:
                        if row['check_type'] == 'OX':
                            curr_val = st.radio("판정", ["OK", "NG"], key=key_val, horizontal=True, label_visibility="collapsed", index=0 if prev.get('ox')=='OK' else 1 if prev.get('ox')=='NG' else 0, disabled=is_viewer)
                            if curr_val == 'NG': is_ng_condition = True
                        else:
                            curr_val = st.number_input("수치", key=key_val, step=0.1, value=float(prev.get('val')) if prev.get('val') and str(prev.get('val')).replace('.','',1).isdigit() else None, disabled=is_viewer)
                            if curr_val is not None:
                                try:
                                    v_f = float(curr_val)
                                    mn = float(row['min_val']) if row['min_val'] != "" else None
                                    mx = float(row['max_val']) if row['max_val'] != "" else None
                                    if mn is not None and v_f < mn: is_ng_condition = True
                                    if mx is not None and v_f > mx: is_ng_condition = True
                                except: pass
                        
                        if is_ng_condition:
                            st.text_input("📝 불량 사유 / 조치 내역", value=prev.get('memo', ''), key=key_memo, placeholder="사유 입력")
                    with c3: st.caption(f"기준: {row['standard']}")
        
        st.markdown("---")
        signer = st.text_input("점검자", value=st.session_state.user_info['name'], disabled=is_viewer)
        
        if not is_viewer and st.button(f"💾 {sel_line} 저장", type="primary", use_container_width=True):
            rows_to_add = []
            now_ts = str(utils.get_now())
            for _, row in line_data.iterrows():
                uid = f"{row['equip_id']}_{row['item_name']}"
                key_val = f"v_{uid}_{sel_date}"
                key_memo = f"m_{uid}_{sel_date}"
                
                val = st.session_state.get(key_val)
                memo = st.session_state.get(key_memo, "")
                
                if val is not None:
                    final_ox = "OK"
                    final_val = str(val)
                    if row['check_type'] == 'OX':
                        final_ox = val
                        final_val = ""
                    else:
                        try:
                            v_num = float(val)
                            mn = float(row['min_val']) if row['min_val'] != '' else None
                            mx = float(row['max_val']) if row['max_val'] != '' else None
                            if mn is not None and v_num < mn: final_ox = "NG"
                            if mx is not None and v_num > mx: final_ox = "NG"
                        except: pass
                    rows_to_add.append([str(sel_date), sel_line, row['equip_id'], row['item_name'], final_val, final_ox, signer, now_ts, memo])
            
            if rows_to_add:
                utils.append_rows(rows_to_add, utils.SHEET_CHECK_RESULT, utils.COLS_CHECK_RESULT)
                st.toast("저장되었습니다.")
                st.session_state['scroll_to_top'] = True
                time.sleep(0.5)
                st.rerun()

with t3:
    st.markdown("#### 📄 일일점검 리포트 출력")
    c_r1, c_r2 = st.columns([1, 2])
    report_date = c_r1.date_input("리포트 날짜", utils.get_now(), key="daily_report_date")
    if c_r2.button("PDF 생성"):
        with st.spinner("생성 중..."):
            pdf_bytes = utils.generate_all_daily_check_pdf(str(report_date))
            if pdf_bytes:
                st.download_button("📥 PDF 다운로드", pdf_bytes, file_name=f"Daily_Check_{report_date}.pdf", mime="application/pdf")
            else: st.error("오류 발생")