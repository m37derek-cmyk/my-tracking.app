import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import os
import random
import time

# ==========================================
# 1. CONFIGURATION DE LA PAGE
# ==========================================
st.set_page_config(
    page_title="مجموعة الهدى | سباق الصالحين",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. DESIGN & CSS
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
    }
    
    .stApp { background-color: #f8f9fa; }
    
    .metric-card {
        background-color: white;
        border-radius: 15px;
        padding: 15px;
        border-right: 5px solid #009688;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
    }
    .metric-card h3 { margin: 0; font-size: 0.9rem; color: #666; }
    .metric-card h1 { margin: 0; font-size: 2rem; color: #009688; font-weight: bold; }

    .stButton>button {
        background: linear-gradient(135deg, #009688 0%, #00796b 100%);
        color: white !important;
        border-radius: 12px;
        border: none;
        padding: 10px 20px;
        font-weight: bold;
        width: 100%;
        margin-top: 10px;
    }
    
    .task-header {
        color: #00796b;
        font-weight: bold;
        font-size: 1.1em;
        margin-bottom: 5px;
        border-bottom: 2px solid #e0f2f1;
        padding-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. DONNÉES & CONFIGURATION
# ==========================================
MOTIVATIONAL_QUOTES = [
    "أحب الأعمال إلى الله أدومها وإن قل",
    "ركعتا الفجر خير من الدنيا وما فيها",
    "والذاكرين الله كثيرا والذاكرات",
    "الصيام جنة",
    "أقرب ما يكون العبد من ربه وهو ساجد"
]

GROUPS_CONFIG = {
    "مجموعة الهدى": "Huda@Guide77",
    "الإدارة": "Admin@MasterKey99!"
}

EXPECTED_HEADERS = [
    "التاريخ", "الاسم", "الرمز_الشخصي", "المجموعة",
    "الفجر", "الظهر", "العصر", "المغرب", "العشاء",
    "الورد_القرآني", "قيام_الليل", "الصيام"
]

# ==========================================
# 4. CONNEXION GOOGLE SHEETS
# ==========================================
def get_client():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        if "google_credentials" in st.secrets:
            creds_dict = dict(st.secrets["google_credentials"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        elif os.path.exists("credentials.json"):
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        else:
            st.error("❌ مفاتيح الاتصال مفقودة.")
            st.stop()
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"خطأ في الاتصال: {e}")
        st.stop()

client = get_client()
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1XqSb4DmiUEd-mt9WMlVPTow7VdeYUI2O870fsgrZx-0/edit?gid=0#gid=0"

try:
    sh = client.open_by_url(spreadsheet_url)
    sheet_data = sh.get_worksheet(0)
except Exception as e:
    st.error(f"Erreur d'ouverture du fichier Sheet : {e}")
    st.stop()

# ==========================================
# 5. SYSTÈME DE LOGIN
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def check_login():
    input_user = st.session_state.login_user.strip()
    input_pin = st.session_state.login_pin.strip()
    input_pass = st.session_state.login_pass.strip()
    
    found_group = None
    for group_name, group_pass in GROUPS_CONFIG.items():
        if input_pass == group_pass:
            found_group = group_name
            break
            
    if found_group and input_user and input_pin:
        st.session_state["authenticated"] = True
        st.session_state["user_name"] = input_user
        st.session_state["user_pin"] = input_pin
        st.session_state["user_group"] = found_group
    else:
        st.error("⛔ البيانات غير صحيحة")

if not st.session_state["authenticated"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align:center; color:#009688;'>🕌 مجموعة الهدى</h1>", unsafe_allow_html=True)
        st.text_input("👤 الاسم الكريم:", key="login_user")
        st.text_input("🔢 الرمز الشخصي:", type="password", key="login_pin")
        st.text_input("🔑 كلمة مرور المجموعة:", type="password", key="login_pass")
        st.button("دخول", on_click=check_login)
    st.stop()

# ==========================================
# 6. LOGIQUE DE CALCUL
# ==========================================
def safe_str(val):
    return str(val).strip() if val else ""

def calculate_score(row):
    score = 0
    fajr = safe_str(row.get('الفجر'))
    if fajr == 'جماعة (مسجد)': score += 20
    elif fajr == 'في الوقت (بيت)': score += 15
    
    prayers = ['الظهر', 'العصر', 'المغرب', 'العشاء']
    for p in prayers:
        stat = safe_str(row.get(p))
        if stat == 'جماعة (مسجد)': score += 10
        elif stat == 'في الوقت (بيت)': score += 8

    if safe_str(row.get('الورد_القرآني')) != 'لم أقرأ': score += 15
    if safe_str(row.get('قيام_الليل')) == 'نعم': score += 20
    if safe_str(row.get('الصيام')) == 'نعم': score += 30
    
    return score

# ==========================================
# 7. TRAITEMENT DES DONNÉES (CORRIGÉ)
# ==========================================
current_user = st.session_state["user_name"]
current_pin = st.session_state["user_pin"]
current_group = st.session_state["user_group"]

# --- CORRECTION DE L'ERREUR : INITIALISATION PAR DÉFAUT ---
# On initialise ces variables ICI pour qu'elles existent même si le fichier est vide
my_total_xp = 0
my_rank = "-"
group_df = pd.DataFrame()

try:
    data = sheet_data.get_all_records()
    full_df = pd.DataFrame(data)
except:
    full_df = pd.DataFrame()

if not full_df.empty:
    # Mise à jour structure
    current_cols = full_df.columns.tolist()
    if not set(EXPECTED_HEADERS).issubset(current_cols):
        try: sheet_data.update('A1', [EXPECTED_HEADERS])
        except: pass

    for col in EXPECTED_HEADERS:
        if col not in full_df.columns: full_df[col] = ""

    full_df['Score'] = full_df.apply(calculate_score, axis=1)
    full_df['DateObj'] = pd.to_datetime(full_df['التاريخ'], errors='coerce')
    
    if current_group == "الإدارة":
        group_df = full_df.copy()
    else:
        group_df = full_df[full_df['المجموعة'] == current_group].copy()

    if not group_df.empty:
        # Calcul du classement
        leaderboard = group_df.groupby(['الاسم', 'الرمز_الشخصي'])['Score'].sum().reset_index().sort_values('Score', ascending=False)
        leaderboard['Rank'] = range(1, len(leaderboard) + 1)
        
        # Récupération de mes stats
        my_stats = leaderboard[(leaderboard['الاسم'] == current_user) & (leaderboard['الرمز_الشخصي'].astype(str) == str(current_pin))]
        if not my_stats.empty:
            my_total_xp = my_stats.iloc[0]['Score']
            my_rank = my_stats.iloc[0]['Rank']

# ==========================================
# 8. INTERFACE UTILISATEUR
# ==========================================
col_h1, col_h2 = st.columns([6, 1])
with col_h1:
    st.markdown(f"### 🚩 {current_group}")
    st.markdown(f"أهلاً بك يا **{current_user}**")
with col_h2:
    if st.button("خروج"):
        st.session_state["authenticated"] = False
        st.rerun()

# Les variables my_rank et my_total_xp existent maintenant quoi qu'il arrive
k1, k2 = st.columns(2)
with k1: st.markdown(f"""<div class="metric-card"><h3>الترتيب</h3><h1>#{my_rank}</h1></div>""", unsafe_allow_html=True)
with k2: st.markdown(f"""<div class="metric-card"><h3>مجموع النقاط</h3><h1>{my_total_xp}</h1></div>""", unsafe_allow_html=True)

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📝 تسجيل اليوم", "🏆 المتصدرون", "📈 سجلي"])

# --- TAB 1: FORMULAIRE ---
with tab1:
    st.markdown("### 🤲 متابعة مجموعة الهدى")
    st.info(random.choice(MOTIVATIONAL_QUOTES))
    
    with st.form("huda_form"):
        st.markdown("<div class='task-header'>🕌 صلاة الفجر</div>", unsafe_allow_html=True)
        fajr = st.selectbox("حالة الفجر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], label_visibility="collapsed")
        
        st.markdown("<br><div class='task-header'>⏰ الصلوات المفروضة</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.caption("الظهر")
            dhuhr = st.selectbox("الظهر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], label_visibility="collapsed")
        with c2:
            st.caption("العصر")
            asr = st.selectbox("العصر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], label_visibility="collapsed")
        with c3:
            st.caption("المغرب")
            maghrib = st.selectbox("المغرب", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], label_visibility="collapsed")
        with c4:
            st.caption("العشاء")
            isha = st.selectbox("العشاء", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], label_visibility="collapsed")
        
        st.markdown("<hr style='margin:15px 0;'>", unsafe_allow_html=True)
        
        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            st.markdown("<div class='task-header'>📖 الورد اليومي</div>", unsafe_allow_html=True)
            quran = st.selectbox("الكمية", ["لم أقرأ", "وجه", "ربع حزب", "حزب", "جزء"], label_visibility="collapsed")
        with col_q2:
            st.markdown("<div class='task-header'>🌙 قيام الليل</div>", unsafe_allow_html=True)
            st.caption("(3 ركعات)")
            qiyam = st.checkbox("أديت 3 ركعات")
        with col_q3:
            st.markdown("<div class='task-header'>🍽️ الصيام</div>", unsafe_allow_html=True)
            st.caption("(يوم في الأسبوع)")
            fasting = st.checkbox("صمت هذا اليوم")

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("✅ حفظ")
        
        if submitted:
            day_date = datetime.now().strftime("%Y-%m-%d")
            is_dup = False
            if not group_df.empty:
                check = group_df[(group_df['الاسم']==current_user) & (group_df['الرمز_الشخصي'].astype(str)==str(current_pin))]
                if day_date in check['التاريخ'].astype(str).values: is_dup = True
            
            if is_dup:
                st.error(f"⛔ تم التسجيل ليوم {day_date} سابقاً.")
            else:
                row = [
                    day_date, current_user, current_pin, current_group,
                    fajr, dhuhr, asr, maghrib, isha,
                    quran, "نعم" if qiyam else "لا", "نعم" if fasting else "لا"
                ]
                try:
                    with st.spinner("جاري الحفظ..."):
                        sheet_data.append_row(row)
                        st.balloons()
                        st.success("تم الحفظ!")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"خطأ: {e}")

# --- TAB 2: CLASSEMENT ---
with tab2:
    if not group_df.empty:
        st.markdown("### 🏆 المتنافسون")
        leaderboard = group_df.groupby(['الاسم', 'الرمز_الشخصي'])['Score'].sum().reset_index().sort_values('Score', ascending=False)
        leaderboard['الترتيب'] = range(1, len(leaderboard) + 1)
        st.dataframe(leaderboard[['الترتيب', 'الرمز_الشخصي', 'Score']].rename(columns={'الرمز_الشخصي': 'الرمز'}), use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد بيانات.")

# --- TAB 3: HISTORIQUE ---
with tab3:
    if not group_df.empty:
        st.markdown("### 📈 سجلي")
        my_data = group_df[(group_df['الاسم'] == current_user) & (group_df['الرمز_الشخصي'].astype(str) == str(current_pin))].copy()
        if not my_data.empty:
            my_data = my_data.sort_values('DateObj')
            st.line_chart(my_data.set_index('DateObj')['Score'])
            cols_to_show = [c for c in ['التاريخ', 'الفجر', 'الورد_القرآني', 'Score'] if c in my_data.columns]
            st.dataframe(my_data[cols_to_show], use_container_width=True)
        else:
            st.info("لم تقم بأي تسجيل بعد.")
    else:
        st.info("قاعدة البيانات فارغة.")
