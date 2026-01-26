import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
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

# Palette Couleurs
COLOR_PRIMARY = "#009688"
COLOR_GOLD = "#FFD700"
COLOR_RED = "#FF5252"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Cairo', sans-serif;
        direction: rtl;
    }}
    
    .stApp {{ background-color: #f8f9fa; }}
    
    .game-card {{
        background: white;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        text-align: center;
        border-bottom: 5px solid {COLOR_PRIMARY};
        transition: transform 0.2s;
    }}
    .game-card:hover {{ transform: translateY(-5px); }}
    .game-card h3 {{ color: #7f8c8d; font-size: 0.9em; margin: 0; }}
    .game-card .value {{ color: {COLOR_PRIMARY}; font-size: 2em; font-weight: bold; }}
    
    .level-badge {{
        background: linear-gradient(45deg, #FFD700, #FFA500);
        color: white;
        padding: 5px 20px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 1.1em;
        display: inline-block;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        margin-top: 5px;
    }}

    .locked-box {{
        background-color: #ffebee;
        border: 2px solid {COLOR_RED};
        color: #c62828;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        font-weight: bold;
        font-size: 1.2em;
        margin: 20px 0;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }}

    .stButton>button {{
        background: linear-gradient(135deg, {COLOR_PRIMARY} 0%, #00796b 100%);
        color: white !important;
        border-radius: 12px;
        font-weight: bold;
        border: none;
        height: 50px;
        width: 100%;
        font-size: 1.1em;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. RÈGLES DU JEU (5 PILIERS)
# ==========================================
SCORE_RULES = {
    "Fajr": {"جماعة (مسجد)": 50, "في الوقت (بيت)": 40, "قضاء (متأخر)": 10, "فاتتني": -30},
    "Prayers": {"جماعة (مسجد)": 20, "في الوقت (بيت)": 15, "قضاء (متأخر)": 5, "فاتتني": -10},
    "Quran": {"جزء أو أكثر": 40, "حزبين": 30, "حزب": 20, "أقل من حزب": 10, "0": 0},
    "Qiyam": 50,   # 3 Rakats
    "Fasting": 100 # Jeûne
}

GROUPS_CONFIG = {
    "مجموعة الفردوس": "Firdaws@786!Top",
    "مجموعة الريان": "Rayyan#2025$Win",
    "الإدارة": "Admin@MasterKey99!"
}

HEADERS = [
    "التاريخ", "الاسم", "الرمز", "المجموعة",
    "الفجر", "الظهر", "العصر", "المغرب", "العشاء",
    "القرآن", "قيام_الليل", "الصيام",
    "نقاط_اليوم", "ملاحظات"
]

# ==========================================
# 3. CONNEXION SÉCURISÉE (CACHE)
# ==========================================
@st.cache_resource
def init_connection():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        if "google_credentials" in st.secrets:
            creds_dict = dict(st.secrets["google_credentials"])
            if "private_key" in creds_dict: 
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            return gspread.authorize(creds)
            
        elif os.path.exists("credentials.json"):
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
            return gspread.authorize(creds)
        else:
            return None
    except Exception:
        return None

client = init_connection()
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1XqSb4DmiUEd-mt9WMlVPTow7VdeYUI2O870fsgrZx-0/edit?gid=0#gid=0"

if client:
    try:
        sh = client.open_by_url(spreadsheet_url)
        sheet_data = sh.get_worksheet(0)
    except:
        st.error("❌ Erreur connexion Excel.")
        st.stop()
else:
    st.error("❌ Clés manquantes.")
    st.stop()

# ==========================================
# 4. LOGIQUE MÉTIER
# ==========================================
if "auth" not in st.session_state: st.session_state["auth"] = False
if "submit_lock" not in st.session_state: st.session_state["submit_lock"] = False

def check_login():
    u = str(st.session_state.login_user).strip()
    p = str(st.session_state.login_pin).strip()
    pwd = str(st.session_state.login_pass).strip()
    
    grp = next((g for g, pw in GROUPS_CONFIG.items() if pw == pwd), None)
    if grp and u and p:
        st.session_state.update({"auth": True, "user": u, "pin": p, "grp": grp})
    else: st.error("⛔ البيانات غير صحيحة")

def calculate_score(data):
    score = 0
    score += SCORE_RULES["Fajr"].get(data["الفجر"], 0)
    for p in ["الظهر", "العصر", "المغرب", "العشاء"]:
        score += SCORE_RULES["Prayers"].get(data[p], 0)
    score += SCORE_RULES["Quran"].get(data["القرآن"], 0)
    if data["قيام_الليل"] == "نعم": score += SCORE_RULES["Qiyam"]
    if data["الصيام"] == "نعم": score += SCORE_RULES["Fasting"]
    return score

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
        st.markdown("<br><h1 style='text-align:center; color:#009688;'>🕌 سباق الصالحين</h1><p style='text-align:center'>الفجر • الصلاة • القرآن • القيام • الصيام</p>", unsafe_allow_html=True)
        st.text_input("الاسم:", key="login_user")
        st.text_input("الرمز السري:", type="password", key="login_pin")
        st.text_input("كود المجموعة:", type="password", key="login_pass")
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
    df['نقاط_اليوم'] = pd.to_numeric(df['نقاط_اليوم'], errors='coerce').fillna(0)
    df['DateObj'] = pd.to_datetime(df['التاريخ'], errors='coerce')
    df['المجموعة'] = df['المجموعة'].astype(str).str.strip()
    df['الاسم'] = df['الاسم'].astype(str).str.strip()
    df['التاريخ'] = df['التاريخ'].astype(str).str.strip()

# ==========================================
# 7. INTERFACE PRINCIPALE
# ==========================================
col_h1, col_h2 = st.columns([6, 1])
with col_h1: st.markdown(f"### 🚩 {c_grp} | المتسابق: **{c_user}**")
with col_h2: 
    if st.button("خروج"):
        st.session_state["auth"] = False
        st.session_state["submit_lock"] = False
        st.rerun()

# --- ADMIN ---
if c_grp == "الإدارة":
    st.markdown("## 👮‍♂️ الإدارة")
    if df.empty: st.warning("لا توجد بيانات.")
    else:
        st.markdown("### 🏆 الترتيب العام")
        leaderboard = df.groupby('الاسم')['نقاط_اليوم'].sum().sort_values(ascending=False).reset_index()
        leaderboard.insert(0, 'الترتيب', leaderboard.index + 1)
        st.dataframe(leaderboard, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📈 تحليل")
        users = df['الاسم'].unique()
        sel = st.selectbox("اختر:", users)
        if sel:
            udata = df[df['الاسم'] == sel].sort_values('DateObj')
            chart = alt.Chart(udata).mark_area(color='#009688').encode(x='DateObj:T', y='نقاط_اليوم:Q')
            st.altair_chart(chart, use_container_width=True)

# --- USER ---
else:
    my_total = 0
    my_rank_num = "-"
    if not df.empty:
        my_data = df[df['الاسم'] == c_user]
        my_total = my_data['نقاط_اليوم'].sum()
        totals = df.groupby('الاسم')['نقاط_اليوم'].sum().sort_values(ascending=False).reset_index()
        if c_user in totals['الاسم'].values:
            my_rank_num = totals[totals['الاسم'] == c_user].index[0] + 1

    rank_title = get_rank_title(my_total)
    
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"<div class='game-card'><h3>الرتبة</h3><div class='level-badge'>{rank_title}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='game-card'><h3>مجموع النقاط</h3><div class='value'>{int(my_total)}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='game-card'><h3>الترتيب العام</h3><div class='value'>#{my_rank_num}</div></div>", unsafe_allow_html=True)

    next_lvl = (int(my_total) // 500 + 1) * 500
    st.progress(min(1.0, (my_total % 500) / 500))

    tab1, tab2, tab3 = st.tabs(["📝 تسجيل اليوم", "🏆 المنافسة (اليوم)", "📜 سجلي"])

    # --- TAB 1: Enregistrement ---
    with tab1:
        today = datetime.now().strftime("%Y-%m-%d")
        session_key = f"done_{today}_{c_user}"
        is_locked = st.session_state.get(session_key, False)
        
        if not is_locked and not df.empty:
            check = df[(df['الاسم'] == c_user) & (df['التاريخ'] == today)]
            if not check.empty:
                is_locked = True
                st.session_state[session_key] = True

        if is_locked:
            st.markdown(f"<div class='locked-box'>🔒 تم تسجيل يوم {today} بنجاح.<br>تقبل الله طاعتكم.</div>", unsafe_allow_html=True)
        elif st.session_state["submit_lock"]:
            st.info("⏳ جاري الحفظ...")
        else:
            with st.form("daily"):
                st.markdown("### 📋 مهام اليوم")
                st.markdown("**1️⃣ صلاة الفجر 🕌**")
                fajr = st.selectbox("حالة الفجر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء (متأخر)", "فاتتني"], label_visibility="collapsed")
                st.markdown("---")
                st.markdown("**2️⃣ الصلوات المفروضة ⏰**")
                c1, c2, c3, c4 = st.columns(4)
                opts = ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء (متأخر)", "فاتتني"]
                p_res = {
                    "الظهر": c1.selectbox("الظهر", opts), 
                    "العصر": c2.selectbox("العصر", opts),
                    "المغرب": c3.selectbox("المغرب", opts), 
                    "العشاء": c4.selectbox("العشاء", opts)
                }
                st.markdown("---")
                c_q1, c_q2 = st.columns(2)
                with c_q1:
                    st.markdown("**3️⃣ الورد اليومي 📖**")
                    quran = st.selectbox("الكمية", ["0", "أقل من حزب", "حزب", "حزبين", "جزء أو أكثر"], label_visibility="collapsed")
                with c_q2:
                    st.markdown("**4️⃣ قيام الليل (3 ركعات) 🌙**")
                    qiyam = st.checkbox("أديت 3 ركعات (الشفع والوتر)")
                st.markdown("---")
                st.markdown("**5️⃣ صيام تطوع (يوم في الأسبوع) ❤️**")
                fasting = st.checkbox("نعم، صمت اليوم")
                
                submit = st.form_submit_button("✅ حفظ واعتماد")
                
            if submit:
                final_check = False
                if not df.empty:
                    if not df[(df['الاسم'] == c_user) & (df['التاريخ'] == today)].empty:
                        final_check = True
                
                if final_check:
                    st.error("⛔ تم التسجيل بالفعل!")
                    st.session_state[session_key] = True
                    time.sleep(2)
                    st.rerun()
                else:
                    st.session_state["submit_lock"] = True
                    r_data = {"الفجر": fajr, "القرآن": quran, "قيام_الليل": "نعم" if qiyam else "لا", "الصيام": "نعم" if fasting else "لا"}
                    r_data.update(p_res)
                    pts = calculate_score(r_data)
                    row = [today, c_user, c_pin, c_grp, fajr, p_res["الظهر"], p_res["العصر"], p_res["المغرب"], p_res["العشاء"], quran, "نعم" if qiyam else "لا", "نعم" if fasting else "لا", pts, ""]
                    
                    try:
                        sheet_data.append_row(row)
                        st.balloons()
                        st.session_state[session_key] = True
                        st.success(f"✅ تم الحفظ! لقد حصلت على {pts} نقطة.")
                        time.sleep(3)
                        st.session_state["submit_lock"] = False
                        st.rerun()
                    except Exception as e:
                        st.session_state["submit_lock"] = False
                        st.error(f"خطأ: {e}")

    # --- TAB 2: CLASSEMENT JOURNALIER (LEADERBOARD) ---
    with tab2:
        today = datetime.now().strftime("%Y-%m-%d")
        st.markdown(f"### 📊 ترتيب المجموعة ليوم: {today}")
        
        if not df.empty:
            # Filtrer par date et groupe
            daily_df = df[
                (df['التاريخ'] == today) & 
                (df['المجموعة'] == c_grp)
            ].copy()
            
            if not daily_df.empty:
                # Trier par points
                daily_df = daily_df.sort_values('نقاط_اليوم', ascending=False).reset_index(drop=True)
                
                # Ajouter colonne Rang
                daily_df['المركز'] = daily_df.index + 1
                
                # Calculer le Gap (Fariq)
                top_score = daily_df.iloc[0]['نقاط_اليوم']
                daily_df['الفارق عن الأول'] = top_score - daily_df['نقاط_اليوم']
                
                # Tableau final
                final_table = daily_df[['المركز', 'الاسم', 'نقاط_اليوم', 'الفارق عن الأول']]
                
                # Fonction de style pour mettre en évidence l'utilisateur
                def highlight_me(x):
                    if x['الاسم'] == c_user:
                        return ['background-color: #d4edda; font-weight: bold; color: #155724'] * len(x)
                    else:
                        return [''] * len(x)

                st.dataframe(
                    final_table.style.apply(highlight_me, axis=1), 
                    use_container_width=True
                )
                
                # Message de motivation
                my_daily = daily_df[daily_df['الاسم'] == c_user]
                if not my_daily.empty:
                    rank = my_daily.iloc[0]['المركز']
                    gap = int(my_daily.iloc[0]['الفارق عن الأول'])
                    
                    if rank == 1:
                        st.success("👑 **أنت المتصدر اليوم!** حافظ على همتك.")
                    else:
                        st.warning(f"⚠️ **انتبه:** أنت في المركز **{rank}**. ينقصك **{gap}** نقطة لتلحق بالمتصدر.")
                else:
                    st.info("لم تظهر في الترتيب لأنك لم تسجل نقاط اليوم بعد.")
            else:
                st.info("لم يقم أحد بتسجيل النقاط اليوم حتى الآن. كن المبادر وسجل أولاً!")
        else: st.info("جاري التحميل...")

    # --- TAB 3: HISTORIQUE ---
    with tab3:
        st.markdown("### 📈 أرشيف إنجازاتي")
        if not df.empty:
            my_hist = df[df['الاسم'] == c_user].sort_values('DateObj', ascending=False)
            if not my_hist.empty:
                cols_to_show = ['التاريخ', 'نقاط_اليوم', 'الفجر', 'القرآن', 'قيام_الليل', 'الصيام']
                st.dataframe(my_hist[cols_to_show], use_container_width=True, hide_index=True)
            else: st.info("لا يوجد سجل.")
