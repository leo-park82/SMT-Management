import streamlit as st
import utils
import pandas as pd
import time
from datetime import timedelta
import altair as alt
from gspread_dataframe import get_as_dataframe

st.set_page_config(page_title="설비보전", page_icon="🛠", layout="wide")
utils.check_auth_status()
utils.render_sidebar()

t1, t2, t3 = st.tabs(["📝 정비 등록", "📋 이력 조회", "📊 분석 리포트"])

with t1:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        if st.session_state.user_info['role'] in ['admin', 'worker']:
            with st.container(border=True):
                st.markdown("#### 🔧 정비 등록")
                eq_df = utils.load_data(utils.SHEET_EQUIPMENT, utils.COLS_EQUIPMENT)
                eq_map = dict(zip(eq_df['id'], eq_df['name'])) if not eq_df.empty else {}
                f_date = st.date_input("날짜", key="maint_date", value=utils.get_now())
                f_eq = st.selectbox("설비", list(eq_map.keys()), format_func=lambda x: f"[{x}] {eq_map[x]}")
                f_type = st.selectbox("구분", ["PM (예방)", "BM (고장)", "CM (개선)"])
                f_desc = st.text_area("내용")
                
                if 'maint_parts' not in st.session_state: st.session_state.maint_parts = []
                col_p1, col_p2, col_p3 = st.columns([2, 1, 0.8])
                with col_p1: p_in = st.text_input("부품명", key="p_in_val")
                with col_p2: c_in = st.number_input("금액", step=1000, key="c_in_val")
                with col_p3:
                    st.write(""); st.write("")
                    def add_part():
                        if st.session_state.p_in_val:
                            st.session_state.maint_parts.append({"부품명": st.session_state.p_in_val, "금액": st.session_state.c_in_val})
                            st.session_state.p_in_val = ""; st.session_state.c_in_val = 0
                    st.button("추가", on_click=add_part)

                if st.session_state.maint_parts:
                    st.dataframe(pd.DataFrame(st.session_state.maint_parts), use_container_width=True, hide_index=True)
                    if st.button("목록 초기화", type="secondary"):
                        st.session_state.maint_parts = []
                        st.rerun()

                calc_cost = sum([p['금액'] for p in st.session_state.maint_parts])
                f_cost = st.number_input("총 정비 비용", value=calc_cost, step=1000)
                f_down = st.number_input("비가동(분)", step=10)
                
                if st.button("저장", type="primary"):
                    parts_text = ", ".join([f"{item['부품명']}({item['금액']:,})" for item in st.session_state.maint_parts])
                    if not parts_text and p_in:
                        parts_text = f"{p_in}({c_in:,})"
                        if f_cost == 0: f_cost = c_in

                    rec = {"날짜": str(f_date), "설비ID": f_eq, "설비명": eq_map[f_eq], "작업구분": f_type.split()[0], "작업내용": f_desc, "교체부품": parts_text, "비용": f_cost, "비가동시간": f_down, "입력시간": str(utils.get_now()), "작성자": st.session_state.user_info['id']}
                    utils.append_data(rec, utils.SHEET_MAINTENANCE)
                    st.session_state.maint_parts = []
                    st.toast("저장 완료", icon="✅")
                    time.sleep(0.5)
                    st.rerun()
        else: st.info("🔒 뷰어 모드입니다.")
    with c2:
        st.markdown("#### 📋 최근 정비 내역")
        df = utils.load_data(utils.SHEET_MAINTENANCE, utils.COLS_MAINTENANCE)
        if not df.empty:
            if st.session_state.user_info['role'] == 'admin':
                df_display = df.sort_values("입력시간", ascending=False).head(50)
                df_display.insert(0, "삭제", False)
                edited_df = st.data_editor(df_display, hide_index=True, use_container_width=True, column_config={"삭제": st.column_config.CheckboxColumn(required=True), "입력시간": st.column_config.TextColumn(disabled=True)}, disabled=["입력시간"], key="maint_editor")
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button("선택 항목 삭제", type="secondary", key="del_maint"):
                        to_delete = edited_df[edited_df["삭제"] == True]
                        if not to_delete.empty:
                            try:
                                ws = utils.get_worksheet(utils.SHEET_MAINTENANCE)
                                all_data = get_as_dataframe(ws)
                                for t in to_delete['입력시간']:
                                    idx_to_drop = all_data[all_data['입력시간'].astype(str) == str(t)].index
                                    all_data = all_data.drop(idx_to_drop)
                                utils.save_data(all_data, utils.SHEET_MAINTENANCE)
                                st.success("삭제 완료")
                                st.rerun()
                            except Exception as e: st.error(f"오류: {e}")
                with c_btn2:
                    if st.button("수정사항 저장", type="primary", key="save_maint"):
                        try:
                            ws = utils.get_worksheet(utils.SHEET_MAINTENANCE)
                            all_data = get_as_dataframe(ws)
                            all_data['입력시간'] = all_data['입력시간'].astype(str)
                            for index, row in edited_df.iterrows():
                                if row['삭제']: continue
                                match_idx = all_data[all_data['입력시간'] == str(row['입력시간'])].index
                                if not match_idx.empty:
                                    for col in utils.COLS_MAINTENANCE:
                                        if col != '입력시간': all_data.at[match_idx[0], col] = row[col]
                            utils.save_data(all_data, utils.SHEET_MAINTENANCE)
                            st.success("저장 완료")
                            st.rerun()
                        except Exception as e: st.error(f"저장 오류: {e}")
            else: st.dataframe(df.sort_values("입력시간", ascending=False).head(20), hide_index=True, use_container_width=True)

with t2:
    df = utils.load_data(utils.SHEET_MAINTENANCE, utils.COLS_MAINTENANCE)
    st.dataframe(df, use_container_width=True)

with t3:
    st.markdown("#### 📊 보전 분석 리포트")
    # [수정] 버튼 트리거
    if st.button("보전 분석 실행"):
        df = utils.load_data(utils.SHEET_MAINTENANCE, utils.COLS_MAINTENANCE)
        if not df.empty:
            df['비가동시간'] = pd.to_numeric(df['비가동시간'], errors='coerce').fillna(0)
            
            top_down = df.groupby('설비명')['비가동시간'].sum().sort_values(ascending=False).head(3)
            top_down_display = top_down.astype(int).reset_index()
            top_down_display.columns = ['설비명', '비가동시간(분)']
            
            bm_count = len(df[df['작업구분'] == 'BM'])
            bm_rate = (bm_count / len(df)) * 100 if len(df) > 0 else 0
            
            repeat_fail = df[df['작업구분'] == 'BM']['설비명'].value_counts().head(3)

            c_a1, c_a2 = st.columns(2)
            with c_a1:
                st.error("🚨 비가동시간 상위 설비 (TOP 3)")
                st.table(top_down_display)
            with c_a2:
                if bm_rate > 40: st.error(f"⚠️ BM 비율 {bm_rate:.1f}% → 예방정비 강화 필요")
                else: st.success(f"✅ BM 비율 {bm_rate:.1f}% (양호)")
                st.warning("🔁 반복 고장 설비")
                if not repeat_fail.empty: st.table(repeat_fail.reset_index(name="고장횟수"))
                else: st.info("데이터 없음")

            st.markdown("---")
            st.subheader("💰 유형별 정비 비용 분석")
            df['비용'] = pd.to_numeric(df['비용'], errors='coerce').fillna(0)
            cost_agg = df.groupby('작업구분')['비용'].sum().reset_index()
            
            base = alt.Chart(cost_agg).encode(x=alt.X('작업구분', sort='-y'), y='비용', color='작업구분')
            bars = base.mark_bar(cornerRadiusTopLeft=10, cornerRadiusTopRight=10).encode(tooltip=['비용'])
            text = base.mark_text(dy=-5).encode(text=alt.Text('비용', format=',d'))
            st.altair_chart((bars + text).properties(height=400), use_container_width=True)
        else: st.info("데이터 없음")