import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import hashlib
import os
import tempfile
import urllib.request
from fpdf import FPDF
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe, get_as_dataframe
import altair as alt

# ------------------------------------------------------------------
# 상수 및 설정 (구글 시트 정보)
# ------------------------------------------------------------------
GOOGLE_SHEET_NAME = "SMT_Database" 

SHEET_RECORDS = "production_data"
SHEET_ITEMS = "item_codes"
SHEET_INVENTORY = "inventory_data"
SHEET_INV_HISTORY = "inventory_history"
SHEET_MAINTENANCE = "maintenance_data"
SHEET_EQUIPMENT = "equipment_list"
SHEET_CHECK_MASTER = "daily_check_master"
SHEET_CHECK_RESULT = "daily_check_result"

COLS_RECORDS = ["날짜", "구분", "품목코드", "제품명", "수량", "입력시간", "작성자", "수정자", "수정시간"]
COLS_ITEMS = ["품목코드", "제품명"]
COLS_INVENTORY = ["품목코드", "제품명", "현재고"]
COLS_INV_HISTORY = ["날짜", "품목코드", "구분", "수량", "비고", "작성자", "입력시간"]
COLS_MAINTENANCE = ["날짜", "설비ID", "설비명", "작업구분", "작업내용", "교체부품", "비용", "작업자", "비가동시간", "입력시간", "작성자", "수정자", "수정시간"]
COLS_EQUIPMENT = ["id", "name", "func"]
COLS_CHECK_MASTER = ["line", "equip_id", "equip_name", "item_name", "check_content", "standard", "check_type", "min_val", "max_val", "unit"]
COLS_CHECK_RESULT = ["date", "line", "equip_id", "item_name", "value", "ox", "checker", "timestamp", "비고"]

# ------------------------------------------------------------------
# 헬퍼 함수 (Helper Functions)
# ------------------------------------------------------------------
def make_hash(password): 
    return hashlib.sha256(str.encode(password)).hexdigest()

def get_now():
    """시스템 시간이 UTC일 경우를 대비해 강제로 한국 시간(UTC+9)을 반환"""
    return datetime.now(timezone(timedelta(hours=9)))

def safe_float(value, default_val=None):
    try:
        if value is None or value == "" or pd.isna(value): return default_val
        return float(value)
    except: return default_val

# ------------------------------------------------------------------
# DB 연결 및 데이터 핸들링 (Google Sheets)
# ------------------------------------------------------------------
@st.cache_resource
def get_gs_connection():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        if "gcp_service_account" not in st.secrets: return None
        creds_dict = dict(st.secrets["gcp_service_account"])
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(credentials)
    except: return None

def get_worksheet(sheet_name, create_cols=None):
    client = get_gs_connection()
    if not client: return None
    try:
        sh = client.open(GOOGLE_SHEET_NAME)
        return sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        if create_cols:
            ws = sh.add_worksheet(title=sheet_name, rows=100, cols=20)
            ws.append_row(create_cols)
            return ws
        return None
    except: return None

@st.cache_data(ttl=60)
def load_data(sheet_name, cols=None):
    try:
        ws = get_worksheet(sheet_name, create_cols=cols)
        if not ws: return pd.DataFrame(columns=cols) if cols else pd.DataFrame()
        
        df = get_as_dataframe(ws, evaluate_formulas=True)
        if df.empty: return pd.DataFrame(columns=cols) if cols else pd.DataFrame()

        df = df.dropna(how='all').dropna(axis=1, how='all')
        df = df.fillna("") 
        
        if cols:
            for c in cols: 
                if c not in df.columns: df[c] = ""
        return df
    except Exception as e:
        return pd.DataFrame(columns=cols) if cols else pd.DataFrame()

def clear_cache():
    load_data.clear()

def save_data(df, sheet_name):
    try:
        ws = get_worksheet(sheet_name)
        if ws:
            df = df.fillna("")
            ws.clear()
            set_with_dataframe(ws, df)
            clear_cache()
            return True
        return False
    except: return False

def append_data(data_dict, sheet_name):
    try:
        ws = get_worksheet(sheet_name)
        if ws:
            try: headers = ws.row_values(1)
            except: headers = list(data_dict.keys())
            ws.append_row([str(data_dict.get(h, "")) if not pd.isna(data_dict.get(h, "")) else "" for h in headers])
            clear_cache()
            return True
        return False
    except: return False

def append_rows(rows, sheet_name, cols):
    try:
        ws = get_worksheet(sheet_name, create_cols=cols)
        if ws:
            safe_rows = [[str(cell) if cell is not None else "" for cell in row] for row in rows]
            ws.append_rows(safe_rows)
            clear_cache()
            return True
        return False
    except: return False

def update_inventory(code, name, change, reason, user):
    df = load_data(SHEET_INVENTORY, COLS_INVENTORY)
    if not df.empty:
        df['현재고'] = pd.to_numeric(df['현재고'], errors='coerce').fillna(0).astype(int)
    
    if not df.empty and code in df['품목코드'].values:
        idx = df[df['품목코드'] == code].index[0]
        df.at[idx, '현재고'] = df.at[idx, '현재고'] + change
    else:
        new_row = pd.DataFrame([{"품목코드": code, "제품명": name, "현재고": change}])
        df = pd.concat([df, new_row], ignore_index=True)
    
    df = df[df['현재고'] != 0]
    save_data(df, SHEET_INVENTORY)
    
    now_kst = get_now()
    hist = {"날짜": now_kst.strftime("%Y-%m-%d"), "품목코드": code, "구분": "입고" if change > 0 else "출고", "수량": change, "비고": reason, "작성자": user, "입력시간": str(now_kst)}
    append_data(hist, SHEET_INV_HISTORY)

# ------------------------------------------------------------------
# 인증 및 UI 관련 함수
# ------------------------------------------------------------------
def check_auth_status():
    """페이지별 권한 체크 - 로그인 안되어 있으면 중단"""
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("로그인이 필요합니다. 메인 화면으로 이동해주세요.")
        st.stop()

def render_sidebar():
    """공통 사이드바 렌더링"""
    with st.sidebar:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=180)
        st.title("SMT")
        
        if "user_info" in st.session_state:
            u = st.session_state.user_info
            role_badge = "👑 Admin" if u["role"] == "admin" else "👤 User"
            st.markdown(f"<div style='padding:10px; background:#f1f5f9; border-radius:8px; margin-bottom:10px;'><b>{u['name']}</b>님 ({role_badge})</div>", unsafe_allow_html=True)
            
            if st.button("로그아웃", use_container_width=True): 
                st.session_state.logged_in = False
                st.session_state.user_info = None
                try: st.query_params.clear()
                except: pass
                st.rerun()

# ------------------------------------------------------------------
# PDF 생성 함수
# ------------------------------------------------------------------
def generate_production_report_pdf(df_prod, df_inv, date_str):
    try:
        font_filename = 'NanumGothic.ttf'
        if not os.path.exists(font_filename):
            try:
                url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
                urllib.request.urlretrieve(url, font_filename)
            except: pass

        pdf = FPDF()
        font_name = 'Arial'
        try:
            pdf.add_font('Korean', '', font_filename, uni=True)
            font_name = 'Korean'
        except: pass
        
        pdf.add_page()
        pdf.set_fill_color(50, 50, 50) 
        pdf.rect(0, 0, 210, 25, 'F')
        pdf.set_font(font_name, '', 20)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, 5)
        pdf.cell(0, 15, "Production Daily Report", 0, 0, 'L')
        pdf.set_font(font_name, '', 10)
        pdf.set_xy(10, 5)
        pdf.cell(0, 15, f"Date: {date_str}", 0, 0, 'R')
        pdf.ln(25)
        
        # 1. 생산 실적
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(font_name, '', 14)
        pdf.cell(0, 10, "1. Daily Production Result", 0, 1, 'L')
        
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font(font_name, '', 10)
        headers = ["구분", "품목코드", "제품명", "수량", "작성자"]
        widths = [25, 35, 80, 25, 25]
        for i, h in enumerate(headers): pdf.cell(widths[i], 10, h, 1, 0, 'C', 1)
        pdf.ln()
        
        fill = False
        pdf.set_fill_color(250, 250, 250)
        total_qty = 0
        if not df_prod.empty:
            for _, row in df_prod.iterrows():
                pdf.cell(widths[0], 8, str(row['구분']), 1, 0, 'C', fill)
                pdf.cell(widths[1], 8, str(row['품목코드']), 1, 0, 'C', fill)
                p_name = str(row['제품명'])
                if len(p_name) > 25: p_name = p_name[:24] + ".."
                pdf.cell(widths[2], 8, p_name, 1, 0, 'L', fill)
                qty = int(float(str(row['수량']).replace(',','')))
                total_qty += qty
                pdf.cell(widths[3], 8, f"{qty:,}", 1, 0, 'R', fill)
                pdf.cell(widths[4], 8, str(row['작성자']), 1, 1, 'C', fill)
                fill = not fill
        else:
            pdf.cell(sum(widths), 10, "No Production Data", 1, 1, 'C', fill)
            
        pdf.ln(2)
        pdf.set_font(font_name, '', 12)
        pdf.cell(0, 10, f"Total Quantity: {total_qty:,} EA", 0, 1, 'R')
        
        # 2. 재고 현황
        if df_inv is not None and not df_inv.empty:
            pdf.ln(10)
            pdf.set_font(font_name, '', 14)
            pdf.cell(0, 10, "2. Current Inventory Status", 0, 1, 'L')
            
            pdf.set_font(font_name, '', 10)
            pdf.set_fill_color(240, 240, 240)
            
            inv_headers = ["품목코드", "제품명", "현재고"]
            inv_widths = [40, 100, 50]
            
            for i, h in enumerate(inv_headers):
                pdf.cell(inv_widths[i], 10, h, 1, 0, 'C', 1)
            pdf.ln()
            
            fill = False
            pdf.set_fill_color(250, 250, 250)
            
            for _, row in df_inv.iterrows():
                pdf.cell(inv_widths[0], 8, str(row['품목코드']), 1, 0, 'C', fill)
                
                p_name = str(row['제품명'])
                if len(p_name) > 35: p_name = p_name[:34] + ".."
                pdf.cell(inv_widths[1], 8, p_name, 1, 0, 'L', fill)
                
                curr_stock = int(float(str(row['현재고']).replace(',', '')))
                pdf.cell(inv_widths[2], 8, f"{curr_stock:,}", 1, 1, 'R', fill)
                fill = not fill

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf.output(tmp_file.name)
            with open(tmp_file.name, "rb") as f: pdf_bytes = f.read()
        os.unlink(tmp_file.name)
        return pdf_bytes
    except: return None

def generate_all_daily_check_pdf(date_str):
    try:
        df_m = load_data(SHEET_CHECK_MASTER, COLS_CHECK_MASTER)
        df_r = load_data(SHEET_CHECK_RESULT, COLS_CHECK_RESULT)
        
        checker_name = ""
        if not df_r.empty:
            df_r['date_only'] = df_r['date'].astype(str).str.split().str[0]
            df_r = df_r[df_r['date_only'] == date_str]
            df_r['timestamp'] = pd.to_datetime(df_r['timestamp'], errors='coerce')
            df_r = df_r.sort_values('timestamp').drop_duplicates(['line', 'equip_id', 'item_name'], keep='last')
            checkers = df_r['checker'].unique()
            if len(checkers) > 0 and checkers[0]:
                checker_name = checkers[0]

        font_filename = 'NanumGothic.ttf'
        if not os.path.exists(font_filename):
            try:
                url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
                urllib.request.urlretrieve(url, font_filename)
            except: pass

        pdf = FPDF()
        font_name = 'Arial'
        try:
            pdf.add_font('Korean', '', font_filename, uni=True)
            font_name = 'Korean'
        except: pass

        lines = df_m['line'].unique()
        first_page = True 

        for line in lines:
            pdf.add_page()
            pdf.set_fill_color(63, 81, 181) 
            pdf.rect(0, 0, 210, 25, 'F')
            pdf.set_font(font_name, '', 20)
            pdf.set_text_color(255, 255, 255)
            pdf.set_xy(10, 5)
            pdf.cell(0, 15, "SMT Daily Check Report", 0, 0, 'L')
            
            pdf.set_font(font_name, '', 10)
            pdf.set_xy(10, 5)
            pdf.cell(0, 15, f"Date: {date_str}", 0, 0, 'R')
            
            if first_page and checker_name:
                pdf.set_xy(10, 12) 
                pdf.cell(0, 15, f"Checker: {checker_name}", 0, 0, 'R')
                first_page = False 

            pdf.ln(25)
            
            line_master = df_m[df_m['line'] == line]
            if not df_r.empty:
                df_final = pd.merge(line_master, df_r, on=['line', 'equip_id', 'item_name'], how='left')
            else:
                df_final = line_master.copy()
                df_final['value'] = '-'
                df_final['ox'] = '-'
                df_final['checker'] = ''
            
            fill_values = {'value': '-', 'ox': '-', 'checker': ''}
            if '비고' in df_final.columns: fill_values['비고'] = ''
            df_final = df_final.fillna(fill_values)
            
            total = len(df_final)
            ok = len(df_final[df_final['ox'] == 'OK'])
            ng = len(df_final[df_final['ox'] == 'NG'])
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font(font_name, '', 16)
            pdf.cell(0, 10, f"{line}", 0, 1, 'L')
            pdf.set_font(font_name, '', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, f"Total: {total}  |  OK: {ok}  |  NG: {ng}", 0, 1, 'L')
            pdf.ln(4)
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_fill_color(240, 242, 245)
            pdf.set_text_color(60, 60, 60)
            pdf.set_draw_color(220, 220, 220)
            pdf.set_line_width(0.3)
            pdf.set_font(font_name, '', 10)
            
            headers = ["설비명", "점검항목", "기준", "측정값", "판정", "점검자"]
            # [수정] PDF 컬럼 너비 조정 (점검항목 축소, 기준 확대)
            widths = [45, 50, 45, 20, 15, 15]
            
            for i, h in enumerate(headers):
                pdf.cell(widths[i], 10, h, 1, 0, 'C', 1)
            pdf.ln()

            fill = False
            pdf.set_fill_color(250, 250, 250) 
            
            for _, row in df_final.iterrows():
                equip_name = str(row['equip_name'])
                if len(equip_name) > 18: equip_name = equip_name[:17] + ".."
                
                pdf.cell(45, 8, equip_name, 1, 0, 'L', fill)
                pdf.cell(50, 8, str(row['item_name']), 1, 0, 'L', fill)
                pdf.cell(45, 8, str(row['standard']), 1, 0, 'C', fill)
                pdf.cell(20, 8, str(row['value']), 1, 0, 'C', fill)
                
                ox = str(row['ox'])
                if ox == 'NG': 
                    pdf.set_text_color(220, 38, 38)
                    pdf.set_font(font_name, 'U', 10)
                elif ox == 'OK':
                    pdf.set_text_color(22, 163, 74)
                    pdf.set_font(font_name, '', 10)
                else:
                    pdf.set_text_color(150, 150, 150)
                    pdf.set_font(font_name, '', 10)
                    
                pdf.cell(15, 8, ox, 1, 0, 'C', fill)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(15, 8, str(row['checker']), 1, 1, 'C', fill)
                pdf.ln()
                
                if ox == 'NG' and '비고' in row and row['비고']:
                    pdf.set_font(font_name, 'I', 9)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(190, 6, f"   └ 조치내역: {row['비고']}", 1, 1, 'L', fill)
                    pdf.set_font(font_name, '', 10)
                    pdf.set_text_color(0, 0, 0)

                fill = not fill
            pdf.ln(10)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf.output(tmp_file.name)
            with open(tmp_file.name, "rb") as f: pdf_bytes = f.read()
        os.unlink(tmp_file.name)
        return pdf_bytes
    except Exception as e:
        return None