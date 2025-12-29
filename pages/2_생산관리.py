import streamlit as st
import utils
import pandas as pd
from datetime import timedelta
import time
import altair as alt

st.set_page_config(page_title="생산관리", page_icon="🏭", layout="wide")
utils.check_auth_status()
utils.render_sidebar()

t1, t2, t3, t4 = st.tabs(["📝 실적 등록", "📦 재고 현황", "📊 생산분석", "📑 일일 보고서"])

with t1:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        if st.session_state.user_info['role'] in ['admin', 'worker']:
            with st.container(border=True):
                st.markdown("#### ✏️ 신규 생산 등록")
                item_df = utils.load_data(utils.SHEET_ITEMS, utils.COLS_ITEMS)
                date = st.date_input("작업 일자", value=utils.get_now())
                cat = st.selectbox("공정 구분", ["PC", "CM1", "CM3", "배전", "샘플", "후공정", "후공정 외주"])
                item_map = dict(zip(item_df['품목코드'], item_df['제품명'])) if not item_df.empty else {}
                
                def on_code():
                    c = st.session_state.code_in.upper().strip()
                    if c in item_map: st.session_state.name_in = item_map[c]
                
                code = st.text_input("품목 코드", key="code_in", on_change=on_code)
                name = st.text_input("제품명", key="name_in")
                qty = st.number_input("생산 수량", min_value=1, value=100, key="prod_qty")
                auto_deduct = st.checkbox("재고 차감 적용", value=True) if cat in ["후공정", "후공정 외주"] else False
                
                def save_production():
                    c_code = st.session_state.code_in; c_name = st.session_state.name_in; c_qty = st.session_state.prod_qty
                    if c_name:
                        rec = {"날짜":str(date), "구분":cat, "품목코드":c_code, "제품명":c_name, "수량":c_qty, "입력시간":str(utils.get_now()), "작성자": st.session_state.user_info['id']}
                        if utils.append_data(rec, utils.SHEET_RECORDS):
                            if cat == "배전":
                                pass
                            elif cat in ["후공정", "후공정 외주"] and auto_deduct: 
                                utils.update_inventory(c_code, c_name, -c_qty, f"생산출고({cat})", st.session_state.user_info['id'])
                            else: 
                                utils.update_inventory(c_code, c_name, c_qty, f"생산입고({cat})", st.session_state.user_info['id'])
                            
                            st.session_state.code_in = ""; st.session_state.name_in = ""; st.session_state.prod_qty = 100
                            st.toast("저장되었습니다.", icon="✅")
                    else: st.toast("제품명을 입력하세요.", icon="⚠️")
                st.button("실적 저장", type="primary", use_container_width=True, on_click=save_production)
        else: st.info("🔒 뷰어 모드입니다.")
    with c2:
        st.markdown("#### 📋 최근 등록 내역")
        df = utils.load_data(utils.SHEET_RECORDS, utils.COLS_RECORDS)
        if not df.empty:
            if st.session_state.user_info['role'] == 'admin':
                df_display = df.sort_values("입력시간", ascending=False).head(50)
                df_display.insert(0, "삭제", False)
                edited_df = st.data_editor(df_display, hide_index=True, use_container_width=True, column_config={"삭제": st.column_config.CheckboxColumn(required=True)}, disabled=utils.COLS_RECORDS, key="recent_records_editor")
                if st.button("선택 항목 삭제", type="secondary"):
                    to_delete = edited_df[edited_df["삭제"] == True]
                    if not to_delete.empty:
                        try:
                            ws = utils.get_worksheet(utils.SHEET_RECORDS)
                            all_records = get_as_dataframe(ws)
                            all_records = all_records.dropna(how='all')
                            all_records['입력시간'] = all_records['입력시간'].astype(str)
                            
                            for t in to_delete['입력시간']:
                                idx_to_drop = all_records[all_records['입력시간'] == str(t)].index
                                all_records = all_records.drop(idx_to_drop)
                            
                            utils.save_data(all_records, utils.SHEET_RECORDS)
                            st.success("삭제 완료")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e: st.error(f"삭제 실패: {e}")
            else: st.dataframe(df.sort_values("입력시간", ascending=False).head(50), hide_index=True, use_container_width=True)

with t2:
    df_inv = utils.load_data(utils.SHEET_INVENTORY, utils.COLS_INVENTORY)
    if not df_inv.empty:
        df_inv = df_inv[df_inv['현재고'] != 0]
        if st.session_state.user_info['role'] == 'admin':
            df_inv.insert(0, "삭제", False)
            edited_inv = st.data_editor(df_inv, hide_index=True, use_container_width=True, column_config={"삭제": st.column_config.CheckboxColumn(required=True)}, disabled=utils.COLS_INVENTORY, key="inventory_editor")
            if st.button("선택 항목 삭제", type="primary", key="del_inv"):
                to_delete = edited_inv[edited_inv["삭제"] == True]
                if not to_delete.empty:
                    try:
                        ws = utils.get_worksheet(utils.SHEET_INVENTORY)
                        all_inv = get_as_dataframe(ws)
                        all_inv = all_inv.dropna(how='all')
                        all_inv['품목코드'] = all_inv['품목코드'].astype(str)
                        for code in to_delete['품목코드']:
                            idx = all_inv[all_inv['품목코드'] == str(code)].index
                            all_inv = all_inv.drop(idx)
                        utils.save_data(all_inv, utils.SHEET_INVENTORY)
                        st.success("삭제 완료")
                        st.rerun()
                    except Exception as e: st.error(f"오류: {e}")
        else: st.dataframe(df_inv, use_container_width=True)
    else: st.info("재고 데이터가 없습니다.")

with t3:
    st.markdown("#### 📊 생산분석")
    df = utils.load_data(utils.SHEET_RECORDS, utils.COLS_RECORDS)
    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df['수량'] = pd.to_numeric(df['수량'], errors='coerce').fillna(0)
        df = df.dropna(subset=['날짜']) 
        
        min_date = df['날짜'].min().date()
        max_date_val = df['날짜'].max().date()
        
        c1, c2 = st.columns([1, 1])
        with c1:
            default_start = max_date_val - timedelta(days=29)
            if default_start < min_date: default_start = min_date
            date_range = st.date_input("기간 선택", value=(default_start, max_date_val), min_value=min_date, max_value=max_date_val)
        
        # [수정] 버튼 트리거 및 안전장치
        if st.button("분석 실행"):
            if df.empty:
                st.info("데이터 없음")
            else:
                max_date = df['날짜'].max()
                recent_start = max_date - timedelta(days=6)
                recent = df[df['날짜'] >= recent_start]
                prev_start = recent_start - timedelta(days=7)
                prev_end = recent_start - timedelta(days=1)
                prev = df[(df['날짜'] >= prev_start) & (df['날짜'] <= prev_end)]

                recent_avg = recent['수량'].mean()
                prev_avg = prev['수량'].mean() if not prev.empty else 0

                if prev_avg > 0:
                    diff_rate = (recent_avg - prev_avg) / prev_avg * 100
                    if diff_rate < -10:
                        st.error(f"⚠️ 최근 생산량이 전주 대비 {abs(diff_rate):.1f}% 감소했습니다.")
                    elif diff_rate > 10:
                        st.success(f"📈 최근 생산량이 전주 대비 {diff_rate:.1f}% 증가했습니다.")

                if isinstance(date_range, tuple) and len(date_range) == 2:
                    mask = (df['날짜'].dt.date >= date_range[0]) & (df['날짜'].dt.date <= date_range[1])
                    df_filtered = df[mask]
                    if not df_filtered.empty:
                        total = df_filtered['수량'].sum()
                        avg = total / len(df_filtered['날짜'].unique())
                        m1, m2 = st.columns(2)
                        m1.metric("총 생산", f"{total:,.0f}")
                        m2.metric("일 평균", f"{avg:,.0f}")
                        
                        chart_data = df_filtered.groupby(['날짜', '구분'])['수량'].sum().reset_index()
                        bar = alt.Chart(chart_data).mark_bar().encode(
                            x=alt.X('날짜:T', axis=alt.Axis(format="%y-%m-%d")),
                            y=alt.Y('수량:Q'), color='구분', tooltip=['날짜', '구분', '수량']
                        ).properties(height=350)
                        st.altair_chart(bar, use_container_width=True)

                        st.markdown("---")
                        st.subheader("🧩 SMT 생산 모델별 분석")
                        smt_cats = ["PC", "CM1", "CM3", "배전"]
                        df_smt = df_filtered[df_filtered['구분'].isin(smt_cats)]
                        if not df_smt.empty:
                            smt_agg = df_smt.groupby('제품명')['수량'].sum().reset_index().sort_values('수량', ascending=False)
                            smt_total = smt_agg['수량'].sum()
                            c_s1, c_s2 = st.columns([1, 2])
                            with c_s1:
                                st.metric("SMT 총 생산량", f"{smt_total:,.0f} EA")
                                st.dataframe(smt_agg, hide_index=True, use_container_width=True, height=400)
                            with c_s2:
                                top_n = st.slider("Top N", 5, 50, 15)
                                chart_data_smt = smt_agg.head(top_n)
                                smt_chart = alt.Chart(chart_data_smt).mark_bar().encode(
                                    x=alt.X('제품명', sort='-y'), y='수량', color=alt.value("#3b82f6"), tooltip=['제품명', '수량']
                                )
                                st.altair_chart(smt_chart, use_container_width=True)
                        else: st.info("SMT 생산 데이터 없음")
                    else: st.info("선택된 기간 데이터 없음")
    else: st.info("생산 데이터 없음")

with t4:
    st.markdown("#### 📑 일일 보고서")
    c1, c2 = st.columns([1,2])
    r_date = c1.date_input("날짜", utils.get_now(), key="rep_date")
    if c2.button("📄 PDF 다운로드"):
        df = utils.load_data(utils.SHEET_RECORDS, utils.COLS_RECORDS)
        df_inv = utils.load_data(utils.SHEET_INVENTORY, utils.COLS_INVENTORY)
        if not df_inv.empty:
            df_inv['현재고'] = pd.to_numeric(df_inv['현재고'], errors='coerce').fillna(0)
            df_inv = df_inv[df_inv['현재고'] != 0]
        if not df.empty:
            df['날짜'] = pd.to_datetime(df['날짜']).dt.date
            daily = df[df['날짜'] == r_date]
            if not daily.empty:
                pdf_bytes = utils.generate_production_report_pdf(daily, df_inv, str(r_date))
                if pdf_bytes:
                    st.download_button("다운로드", pdf_bytes, file_name=f"Report_{r_date}.pdf", mime='application/pdf')
            else: st.warning("데이터 없음")