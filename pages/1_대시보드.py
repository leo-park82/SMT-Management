import streamlit as st
import utils
import pandas as pd
from datetime import timedelta
import altair as alt

st.set_page_config(page_title="대시보드", page_icon="📊", layout="wide")
utils.check_auth_status()
utils.render_sidebar()

st.title("📊 대시보드")

# 데이터 로딩
try:
    with st.spinner("데이터 분석 중..."):
        df_prod = utils.load_data(utils.SHEET_RECORDS, utils.COLS_RECORDS)
        df_check = utils.load_data(utils.SHEET_CHECK_RESULT, utils.COLS_CHECK_RESULT)
        df_maint = utils.load_data(utils.SHEET_MAINTENANCE, utils.COLS_MAINTENANCE)
        
        today = utils.get_now().replace(tzinfo=None)
        today_str = today.strftime("%Y-%m-%d")
        yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        month_start = today.replace(day=1)
        
        # 생산량 계산
        prod_today = 0
        prod_yesterday = 0
        if not df_prod.empty:
            df_prod['날짜'] = pd.to_datetime(df_prod['날짜'], errors='coerce')
            df_prod['수량'] = pd.to_numeric(df_prod['수량'], errors='coerce').fillna(0)
            
            prod_today = df_prod[df_prod['날짜'].dt.strftime("%Y-%m-%d") == today_str]['수량'].sum()
            prod_yesterday = df_prod[df_prod['날짜'].dt.strftime("%Y-%m-%d") == yesterday_str]['수량'].sum()
        
        delta_prod = prod_today - prod_yesterday

        # 점검 현황
        check_today_cnt = 0
        ng_today_cnt = 0
        ng_rate = 0.0
        df_today_unique = pd.DataFrame()
        
        if not df_check.empty:
            df_check['date_only'] = df_check['date'].astype(str).str.split().str[0]
            df_check['timestamp'] = pd.to_datetime(df_check['timestamp'], errors='coerce')
            
            df_today_chk = df_check[df_check['date_only'] == today_str]
            if not df_today_chk.empty:
                df_today_unique = df_today_chk.sort_values('timestamp').drop_duplicates(['line', 'equip_id', 'item_name'], keep='last')
                check_today_cnt = len(df_today_unique)
                ng_today_cnt = len(df_today_unique[df_today_unique['ox'] == 'NG'])
                if check_today_cnt > 0:
                    ng_rate = (ng_today_cnt / check_today_cnt) * 100

        # 정비 건수
        maint_today_cnt = 0
        if not df_maint.empty:
            maint_today_cnt = len(df_maint[df_maint['날짜'].astype(str) == today_str])

        # --- UI 렌더링 ---
        c1, c2, c3 = st.columns(3)
        c1.metric("오늘 생산량", f"{prod_today:,.0f} EA", f"{delta_prod:,.0f} (전일비)")
        c2.metric("금일 설비 정비", f"{maint_today_cnt} 건", "확인 필요" if maint_today_cnt > 0 else "특이사항 없음", delta_color="inverse")
        c3.metric("일일점검 (완료/NG)", f"{check_today_cnt} 건 / {ng_today_cnt} 건", f"불량률: {ng_rate:.1f}%", delta_color="inverse")

        st.markdown("---")

        col_g1, col_g2 = st.columns([2, 1])

        with col_g1:
            st.subheader("📈 주간 생산 추이 & 유형")
            if not df_prod.empty:
                last_7_days = today - timedelta(days=7)
                chart_data = df_prod[df_prod['날짜'] >= last_7_days]
                if not chart_data.empty:
                    chart_agg = chart_data.groupby(['날짜', '구분'])['수량'].sum().reset_index()
                    chart = alt.Chart(chart_agg).mark_line(point=True).encode(
                        x=alt.X('날짜:T', axis=alt.Axis(format="%m-%d", labelAngle=0, title="날짜")),
                        y=alt.Y('수량:Q', axis=alt.Axis(labelAngle=0, title="생\n산\n량", titleAngle=0, titlePadding=20, titleFontWeight="bold", titleFontSize=14)),
                        color=alt.Color('구분', legend=alt.Legend(title="공정 구분")),
                        tooltip=['날짜', '구분', '수량']
                    ).properties(height=300)
                    st.altair_chart(chart, use_container_width=True)
                else: st.info("최근 데이터가 없습니다.")
            else: st.info("생산 데이터가 없습니다.")

        with col_g2:
            st.subheader("🏭 월간 생산 품목 비율")
            if not df_prod.empty:
                df_month_prod = df_prod[(df_prod['날짜'] >= month_start) & (df_prod['날짜'] <= today)]
                if not df_month_prod.empty:
                    pie_data = df_month_prod.groupby('구분')['수량'].sum().reset_index()
                    total_q = pie_data['수량'].sum()
                    pie_data['비율'] = (pie_data['수량'] / total_q * 100).round(1)
                    pie_data['Label'] = pie_data['수량'].astype(str) + " (" + pie_data['비율'].astype(str) + "%)"
                    pie_data['DisplayLabel'] = pie_data.apply(lambda x: x['Label'] if x['비율'] > 3 else "", axis=1)

                    base = alt.Chart(pie_data).encode(theta=alt.Theta("수량", stack=True), color=alt.Color("구분", legend=alt.Legend(title="공정", orient="bottom")))
                    pie = base.mark_arc(outerRadius=120, innerRadius=60).encode(tooltip=["구분", "수량", "비율"])
                    text = base.mark_text(radius=140).encode(text="DisplayLabel", order=alt.Order("구분"), color=alt.value("black"))
                    st.altair_chart((pie + text).properties(height=400), use_container_width=True)
                else: st.info("이번 달 실적 없음")
            else: st.info("데이터 없음")

        st.markdown("---")
        
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("🚨 실시간 NG 현황 (Today)")
            if not df_today_unique.empty and ng_today_cnt > 0:
                ng_display = df_today_unique[df_today_unique['ox'] == 'NG'][['line', 'equip_id', 'item_name', 'value', 'checker', '비고']]
                st.dataframe(ng_display, hide_index=True, use_container_width=True)
            elif ng_today_cnt == 0:
                st.success("🎉 현재까지 발견된 NG 항목이 없습니다.")
            else:
                st.info("점검 데이터가 없습니다.")

        with c4:
            st.subheader("🛠 최근 설비 정비 이력 (Last 5)")
            if not df_maint.empty:
                recent_maint = df_maint.sort_values("날짜", ascending=False).head(5)[['날짜', '설비명', '작업구분', '작업내용']]
                st.dataframe(recent_maint, hide_index=True, use_container_width=True)
            else:
                st.info("정비 이력이 없습니다.")

except Exception as e:
    st.error(f"대시보드 로딩 오류: {e}")