import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import altair as alt

# ==========================================
# 1. CONFIGURATION & DESIGN
# ==========================================
st.set_page_config(
    page_title="سباق الصالحين",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constantes Couleurs
COLOR_PRIMARY = "#009688"
COLOR_GOLD = "#FFD700"
COLOR_RED = "#FF5252"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Cairo', sans-serif; direction: rtl; }}
    .stApp {{ background-color: #f8f9fa; }}
    
    /* CARDS */
    .game-card {{
        background: white; border-radius: 15px; padding: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); text-align: center;
        border-bottom: 5px solid {COLOR_PRIMARY}; transition: transform 0.2s;
    }}
    .game-card:hover {{ transform: translateY(-5px); }}
    .game-card h3 {{ color: #7f8c8d; font-size: 0.9em; margin: 0; }}
    .game-card .value {{ color: {COLOR_PRIMARY}; font-size: 1.8em; font-weight: bold; }}
    
    /* MESSAGES */
    .locked-box {{
        background-color: #ffebee; border: 2px solid {COLOR_RED}; color: #c62828;
        padding: 20px; border-radius: 15px; text-align: center; font-weight: bold;
        margin: 20px 0;
    }}
    
    /* BOUTONS */
    .stButton>button {{
        background: linear-gradient(135deg, {COLOR_PRIMARY} 0%, #00796b 100%);
        color: white !important; border-radius: 12px; font-weight: bold;
        border: none; height: 50px; width: 100%; font-size: 1.1em;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. RÈGLES DU JEU
# ==========================================
SCORE_RULES = {
    "Fajr": {"جماعة (مسجد)": 50, "في الوقت (بيت)": 30, "قضاء (متأخر)": 5, "فاتتني": -20},
    "Prayers": {"جماعة (مسجد)": 20, "في الوقت (بيت)": 15, "قضاء (متأخر)": 5, "فاتتني": -10},
    "Quran": {"جزء أو أكثر": 40, "حزبين": 30, "حزب": 20, "أقل من حزب": 10, "0": 0},
    "Qiyam": 50,
    "Fasting": 100
}

GROUPS_CONFIG = {
    "مجموعة السائرين": "Saerin@2025",
    "الإدارة": "Admin@MasterKey99!"
}

HEADERS = [
    "التاريخ", "الاسم", "الرمز", "المجموعة",
    "الفجر", "الظهر", "العصر", "المغرب", "العشاء",
    "القرآن", "قيام_الليل", "الصيام",
    "نقاط_اليوم", "ملاحظات"
]

# ==========================================
# 3. CONNEXION ROBUSTE (AVEC CACHE) 🔌
# ==========================================
@st.cache_resource
def init_connection():
    """Initialise la connexion une seule fois pour éviter les erreurs."""
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # 1. Essai via Secrets (Cloud)
        if "google_credentials" in st.secrets:
            creds_dict = dict(st.secrets["google_credentials"])
            if "private_key" in creds_dict: 
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            return gspread.authorize(creds)
            
        # 2. Essai via Fichier Local
        elif os.path.exists("credentials.json"):
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
            return gspread.authorize(creds)
            
        else:
            return None
    except Exception as e:
        return None

# Initialisation
client = init_connection()

# URL de votre Sheet (Assurez-vous qu'elle est correcte)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1XqSb4DmiUEd-mt9WMlVPTow7VdeYUI2O870fsgrZx-0/edit?gid=0#gid=0"

# Vérification Connexion
if client is None:
    st.error("❌ خطأ حرج: لم يتم العثور على مفاتيح الاتصال (credentials.json).")
    st.stop()

try:
    sh = client.open_by_url(SPREADSHEET_URL)
    sheet_data = sh.get_worksheet(0)
except Exception as e:
    st.error(f"❌ خطأ في فتح الشيت: {e}")
    st.info("💡 الحل: تأكد أنك قمت بعمل Share للملف مع الإيميل الموجود داخل credentials.json")
    st.stop()

# ==========================================
# 4. FONCTIONS MÉTIER
# ==========================================
if "auth" not in st.session_state: st.session_state["auth"] = False

def check_login():
    u = str(st.session_state.login_user).strip()
    p = str(st.session_state.login_pin).strip()
    pwd = str(st.session_state.login_pass).strip()
    grp = next((g for g, pw in GROUPS_CONFIG.items() if pw == pwd), None)
    
    if grp and u and p:
        st.session_state.update({"auth": True, "user": u, "pin": p, "grp": grp})
    else: st.error("⛔ البيانات غير صحيحة")

def calculate_score(data):
    s = 0
    s += SCORE_RULES["Fajr"].get(data["الفجر"], 0)
    for p in ["الظهر", "العصر", "المغرب", "العشاء"]: s += SCORE_RULES["Prayers"].get(data[p], 0)
    s += SCORE_RULES["Quran"].get(data["القرآن"], 0)
    if data["قيام_الليل"] == "نعم": s += SCORE_RULES["Qiyam"]
    if data["الصيام"] == "نعم": s += SCORE_RULES["Fasting"]
    return s

def get_rank_title(points):
    if points < 500: return "🌱 مبتدئ"
    elif points < 1500: return "🛡️ مثابر"
    elif points < 3000: return "⚔️ مجاهد"
    elif points < 5000: return "👑 سابق"
    else: return "💎 رباني"

# ==========================================
# 5. PAGE LOGIN
# ==========================================
if not st.session_state["auth"]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><h1 style='text-align:center; color:#009688;'>🕌 سباق الصالحين</h1>", unsafe_allow_html=True)
        st.text_input("الاسم:", key="login_user")
        st.text_input("الرمز:", type="password", key="login_pin")
        st.text_input("الكود:", type="password", key="login_pass")
        st.button("🚀 دخول", on_click=check_login)
    st.stop()

# ==========================================
# 6. CHARGEMENT DONNÉES
# ==========================================
c_user = st.session_state["user"]
c_pin = st.session_state["pin"]
c_grp = st.session_state["grp"]

try:
    data = sheet_data.get_all_records()
    df = pd.DataFrame(data)
except: df = pd.DataFrame(columns=HEADERS)

if not df.empty:
    for col in HEADERS: 
        if col not in df.columns: df[col] = ""
    # Nettoyage
    df['نقاط_اليوم'] = pd.to_numeric(df['نقاط_اليوم'], errors='coerce').fillna(0)
    df['DateObj'] = pd.to_datetime(df['التاريخ'], errors='coerce')
    df['المجموعة'] = df['المجموعة'].astype(str).str.strip()
    df['الاسم'] = df['الاسم'].astype(str).str.strip()
    df['التاريخ'] = df['التاريخ'].astype(str).str.strip()

# ==========================================
# 7. INTERFACE PRINCIPALE
# ==========================================
col_h1, col_h2 = st.columns([6, 1])
with col_h1: st.markdown(f"### 🚩 {c_grp} | **{c_user}**")
with col_h2: 
    if st.button("خروج"):
        st.session_state["auth"] = False
        st.rerun()

# --- ADMIN ---
if c_grp == "الإدارة":
    st.markdown("## 👮‍♂️ الإدارة")
    if df.empty: st.warning("لا بيانات.")
    else:
        st.markdown("### 🏆 الترتيب العام")
        lb = df.groupby('الاسم')['نقاط_اليوم'].sum().sort_values(ascending=False).reset_index()
        lb.insert(0, 'الترتيب', lb.index + 1)
        st.dataframe(lb, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📈 تحليل")
        sel_user = st.selectbox("المتسابق:", df['الاسم'].unique())
        if sel_user:
            udata = df[df['الاسم'] == sel_user].sort_values('DateObj')
            chart = alt.Chart(udata).mark_line(point=True).encode(x='DateObj:T', y='نقاط_اليوم:Q')
            st.altair_chart(chart, use_container_width=True)

# --- USER ---
else:
    my_total = 0
    my_rank = "-"
    if not df.empty:
        my_total = df[df['الاسم'] == c_user]['نقاط_اليوم'].sum()
        totals = df.groupby('الاسم')['نقاط_اليوم'].sum().sort_values(ascending=False).reset_index()
        if c_user in totals['الاسم'].values:
            my_rank = totals[totals['الاسم'] == c_user].index[0] + 1

    # Header Stats
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"<div class='game-card'><h3>الرتبة</h3><h4>{get_rank_title(my_total)}</h4></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='game-card'><h3>النقاط</h3><h4>{int(my_total)}</h4></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='game-card'><h3>الترتيب</h3><h4>#{my_rank}</h4></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["📝 تسجيل اليوم", "🏆 المنافسة", "📜 سجلي"])

    # TAB 1: Enregistrement
    with t1:
        today = datetime.now().strftime("%Y-%m-%d")
        done = False
        if not df.empty:
            if not df[(df['الاسم'] == c_user) & (df['التاريخ'] == today)].empty: done = True
            
        if done:
            st.markdown(f"<div class='locked-box'>🔒 تم رصد درجات اليوم ({today}).</div>", unsafe_allow_html=True)
        else:
            with st.form("daily"):
                st.markdown("**1️⃣ الفجر 🕌**")
                fajr = st.selectbox("h_f", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء (متأخر)", "فاتتني"], label_visibility="collapsed")
                st.markdown("**2️⃣ الصلوات ⏰**")
                c1,c2,c3,c4 = st.columns(4)
                opts = ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء (متأخر)", "فاتتني"]
                p = {k: col.selectbox(k, opts, label_visibility="collapsed") for k, col in zip(["الظهر","العصر","المغرب","العشاء"], [c1,c2,c3,c4])}
                st.markdown("**3️⃣ الأعمال 🤲**")
                c1,c2,c3 = st.columns(3)
                quran = c1.selectbox("القرآن", ["0", "أقل من حزب", "حزب", "حزبين", "جزء أو أكثر"])
                qiyam = c2.checkbox("قيام (3 ركعات)")
                fast = c3.checkbox("صيام تطوع")
                
                if st.form_submit_button("✅ حفظ"):
                    data = {"الفجر": fajr, "القرآن": quran, "قيام_الليل": "نعم" if qiyam else "لا", "الصيام": "نعم" if fast else "لا"}
                    data.update(p)
                    pts = calculate_score(data)
                    row = [today, c_user, c_pin, c_grp, fajr, p["الظهر"], p["العصر"], p["المغرب"], p["العشاء"], quran, "نعم" if qiyam else "لا", "نعم" if fast else "لا", pts, ""]
                    
                    try:
                        sheet_data.append_row(row)
                        st.balloons()
                        st.success(f"تم الحفظ! نقاطك: {pts}")
                        time.sleep(2)
                        st.rerun()
                    except: st.error("خطأ اتصال")

    # TAB 2: Classement
    with t2:
        today = datetime.now().strftime("%Y-%m-%d")
        st.markdown(f"### 📊 ترتيب اليوم: {today}")
        if not df.empty:
            day_df = df[(df['التاريخ'] == today) & (df['المجموعة'] == c_grp)].copy()
            if not day_df.empty:
                day_df = day_df.sort_values('نقاط_اليوم', ascending=False).reset_index(drop=True)
                day_df['المركز'] = day_df.index + 1
                top = day_df.iloc[0]['نقاط_اليوم']
                day_df['الفارق'] = top - day_df['نقاط_اليوم']
                
                # Style
                def highlight(x):
                    return ['background-color: #d1e7dd; font-weight:bold' if x['الاسم'] == c_user else '' for _ in x]
                
                st.dataframe(day_df[['المركز', 'الاسم', 'نقاط_اليوم', 'الفارق']].style.apply(highlight, axis=1), use_container_width=True)
                
                # Info user
                me = day_df[day_df['الاسم'] == c_user]
                if not me.empty:
                    diff = int(me.iloc[0]['الفارق'])
                    if diff > 0: st.warning(f"⚠️ شد حيلك! بينك وبين الأول {diff} نقطة.")
                    else: st.success("👑 أنت المتصدر!")
            else: st.info("لا توجد تسجيلات اليوم بعد.")
        else: st.info("جاري التحميل...")

    # TAB 3: Historique
    with t3:
        if not df.empty:
            h = df[df['الاسم'] == c_user].sort_values('DateObj', ascending=False)
            if not h.empty:
                st.dataframe(h[['التاريخ', 'نقاط_اليوم', 'الفجر', 'القرآن']], use_container_width=True)
            else: st.info("لا سجل.")
