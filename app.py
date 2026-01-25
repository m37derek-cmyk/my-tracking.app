import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import random
import time

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="سباق الصالحين", page_icon="🕌", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; }
    .stApp { background-color: #f8f9fa; }
    .metric-card { background-color: white; border-radius: 15px; padding: 20px; border-right: 5px solid #009688; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; }
    .metric-card h1 { color: #009688; font-weight: bold; margin: 0; }
    .stButton>button { background: linear-gradient(135deg, #009688 0%, #00796b 100%); color: white !important; border-radius: 12px; width: 100%; font-weight:bold; }
    .task-header { color: #00796b; font-weight: bold; border-bottom: 2px solid #e0f2f1; padding-bottom: 5px; }
    .locked-box { 
        background-color: #ffebee; 
        border: 2px solid #ef5350; 
        color: #c62828; 
        padding: 20px; 
        border-radius: 15px; 
        text-align: center; 
        font-weight: bold; 
        margin: 20px 0; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .result-box { background-color: #e0f2f1; border: 2px solid #009688; border-radius: 15px; padding: 20px; text-align: center; animation: fadeIn 1s; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONFIGURATION
# ==========================================
GROUPS_CONFIG = {
    "مجموعة الفردوس": "Firdaws@786!Top",
    "مجموعة الريان": "Rayyan#2025$Win",
    "مجموعة الفجر": "Fajr@Simple22", 
    "مجموعة النور": "Noor@Light55", 
    "مجموعة الهدى": "Huda@Guide77",
    "مجموعة السائرين": "Saerin@2025",
    "الإدارة": "Admin@MasterKey99!"
}

EXPECTED_HEADERS = [
    "التاريخ", "الاسم", "الرمز_الشخصي", "المجموعة",
    "الفجر_حالة", "الفجر_سنة", "الضحى", "الظهر_حالة", "الظهر_سنة",
    "العصر_حالة", "المغرب_حالة", "المغرب_سنة", "العشاء_حالة", "العشاء_سنة",
    "أذكار_الصباح", "أذكار_المساء", "أذكار_الصلاة", "أذكار_النوم", "سورة_الملك",
    "قيام", "القرآن", "الصيام", "قراءة_كتاب", "أسرة", "مجلس التدارس", "التعهد",
    "جمعة_كهف", "جمعة_صلاة_نبي", "جمعة_صلاة_جمعة"
]

# ==========================================
# 3. CONNEXION
# ==========================================
def get_client():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        if "google_credentials" in st.secrets:
            creds_dict = dict(st.secrets["google_credentials"])
            if "private_key" in creds_dict: creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        elif os.path.exists("credentials.json"):
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        else: st.error("❌ Credentials manquants."); st.stop()
        return gspread.authorize(creds)
    except Exception as e: st.error(f"Erreur connexion: {e}"); st.stop()

client = get_client()
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1XqSb4DmiUEd-mt9WMlVPTow7VdeYUI2O870fsgrZx-0/edit?gid=0#gid=0"
try:
    sh = client.open_by_url(spreadsheet_url)
    sheet_data = sh.get_worksheet(0)
except: st.error("Erreur sheet"); st.stop()

# ==========================================
# 4. LOGIQUE
# ==========================================
if "authenticated" not in st.session_state: st.session_state["authenticated"] = False

def check_login():
    u, p, c = str(st.session_state.login_user).strip(), str(st.session_state.login_pin).strip(), str(st.session_state.login_pass).strip()
    grp = next((g for g, pw in GROUPS_CONFIG.items() if pw == c), None)
    if grp and u and p:
        st.session_state.update({"authenticated": True, "user_name": u, "user_pin": p, "user_group": grp})
    else: st.error("⛔ البيانات غير صحيحة")

def safe_str(val): return str(val).strip() if not pd.isna(val) else ""

def calculate_score(row):
    score = 0
    grp = safe_str(row.get('المجموعة'))
    # LOGIQUE SIMPLIFIÉE
    if grp in ["مجموعة الهدى", "مجموعة السائرين"]:
        fajr = safe_str(row.get('الفجر_حالة'))
        if fajr == 'جماعة (مسجد)': score += 50
        elif fajr == 'في الوقت (بيت)': score += 40
        
        for p in ['الظهر', 'العصر', 'المغرب', 'العشاء']:
            if safe_str(row.get(f'{p}_حالة')) == 'جماعة (مسجد)': score += 20
            elif safe_str(row.get(f'{p}_حالة')) == 'في الوقت (بيت)': score += 15
            
        if safe_str(row.get('القرآن')) not in ['0', 'لا', '']: score += 30
        if "3" in safe_str(row.get('قيام')): score += 60
        if safe_str(row.get('الصيام')) == 'نعم': score += 100
        return score
    
    # LOGIQUE STANDARD
    else:
        for p in ['الفجر', 'الظهر', 'العصر', 'المغرب', 'العشاء']:
            stat = safe_str(row.get(f'{p}_حالة'))
            if stat == 'جماعة (مسجد)': score += 10
            elif stat == 'في الوقت (بيت)': score += 6
            if p != 'العصر' and safe_str(row.get(f'{p}_سنة')) == 'نعم': score += 3
        
        if safe_str(row.get('الضحى')) == 'نعم': score += 5
        for z in ['أذكار_الصباح', 'أذكار_المساء', 'أذكار_الصلاة', 'أذكار_النوم', 'سورة_الملك']:
            if safe_str(row.get(z)) == 'نعم': score += 3
        
        q = safe_str(row.get('القرآن'))
        if q not in ['0', 'لا', '']: score += 10
        if safe_str(row.get('قيام')) not in ['0', 'لا', '']: score += 10
        for d in ['الصيام', 'قراءة_كتاب', 'أسرة', 'مجلس التدارس', 'التعهد']:
            if safe_str(row.get(d)) == 'نعم': score += 5
        if safe_str(row.get('جمعة_كهف')) == 'نعم': score += 15
        if safe_str(row.get('جمعة_صلاة_نبي')) == 'نعم': score += 15
        if safe_str(row.get('جمعة_صلاة_جمعة')) == 'نعم': score += 20
        return min(score, 250)

def get_level(pts): return 1 + (int(pts) // 300)

# ==========================================
# 5. PAGE LOGIN
# ==========================================
if not st.session_state["authenticated"]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><h1 style='text-align:center; color:#009688;'>🕌 سباق الصالحين</h1>", unsafe_allow_html=True)
        st.text_input("👤 الاسم:", key="login_user")
        st.text_input("🔢 الرمز:", type="password", key="login_pin")
        st.text_input("🔑 كلمة المرور:", type="password", key="login_pass")
        st.button("دخول", on_click=check_login)
    st.stop()

# ==========================================
# 6. CHARGEMENT
# ==========================================
c_user = str(st.session_state["user_name"]).strip()
c_pin = str(st.session_state["user_pin"]).strip()
c_grp = st.session_state["user_group"]

try:
    data = sheet_data.get_all_records()
    df = pd.DataFrame(data)
except: df = pd.DataFrame()

my_xp, my_lvl, my_rank = 0, 1, "-"
grp_df = pd.DataFrame() 

if not df.empty:
    df['الاسم'] = df['الاسم'].astype(str).str.strip()
    df['الرمز_الشخصي'] = df['الرمز_الشخصي'].astype(str).str.strip()
    df['المجموعة'] = df['المجموعة'].astype(str).str.strip()
    
    for c in EXPECTED_HEADERS: 
        if c not in df.columns: df[c] = ""
    
    df['Score'] = df.apply(calculate_score, axis=1)
    df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    df['DateObj'] = pd.to_datetime(df['التاريخ'], errors='coerce')

    grp_df = df if c_grp == "الإدارة" else df[df['المجموعة'] == c_grp].copy()
    
    if not grp_df.empty:
        board = grp_df.groupby(['الاسم', 'الرمز_الشخصي'])['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
        board['Rank'] = board.index + 1
        
        me = board[(board['الاسم'] == c_user) & (board['الرمز_الشخصي'] == c_pin)]
        if not me.empty:
            my_xp = int(me.iloc[0]['Score'])
            my_lvl = get_level(my_xp)
            my_rank = me.iloc[0]['Rank']

# ==========================================
# 7. INTERFACE
# ==========================================
c1, c2 = st.columns([6, 1])
with c1: st.markdown(f"### 🚩 {c_grp} | {c_user}")
with c2: 
    if st.button("خروج"):
        st.session_state["authenticated"] = False
        st.rerun()

if c_grp != "الإدارة":
    k1, k2, k3 = st.columns(3)
    with k1: st.markdown(f"""<div class="metric-card"><h3>الترتيب</h3><h1>#{my_rank}</h1></div>""", unsafe_allow_html=True)
    with k2: st.markdown(f"""<div class="metric-card"><h3>المستوى</h3><h1>{my_lvl}</h1></div>""", unsafe_allow_html=True)
    with k3: st.markdown(f"""<div class="metric-card"><h3>النقاط</h3><h1>{my_xp}</h1></div>""", unsafe_allow_html=True)
    
    nxt = (my_lvl * 300) - my_xp
    prg = max(0.0, min(1.0, 1 - (nxt / 300)))
    st.progress(prg, text=f"🚀 باقي {nxt} نقطة")

st.markdown("---")

if c_grp == "الإدارة":
    st.info("لوحة الإدارة")
    if not df.empty: st.dataframe(df)
else:
    t1, t2, t3 = st.tabs(["📝 اليوم", "🏆 الصدارة", "📈 سجلي"])
    
    with t1:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # ⚠️ CRÉATION DE LA CLÉ DE SESSION UNIQUE POUR AUJOURD'HUI
        # Cette clé sert à mémoriser LOCALEMENT que l'utilisateur a fini
        session_done_key = f"done_{today}_{c_user}"
        
        is_done_today = False
        
        # 1. Vérification dans la session (Mémoire immédiate)
        if st.session_state.get(session_done_key, False):
            is_done_today = True
            
        # 2. Vérification dans le Sheet (Mémoire long terme)
        elif not df.empty:
            check = df[
                (df['الاسم'] == c_user) & 
                (df['الرمز_الشخصي'] == c_pin) & 
                (df['التاريخ'].astype(str).str.strip() == today)
            ]
            if not check.empty:
                is_done_today = True
                # On met à jour la session aussi
                st.session_state[session_done_key] = True

        if is_done_today:
            st.markdown(f"""
            <div class="locked-box">
                ⛔ التسجيل مغلق<br>
                <br>
                لقد قمت بتسجيل نقاط يوم <b>{today}</b> بنجاح.<br>
                لا يمكن الإضافة مرة أخرى.<br>
                <br>
                ✨ نلتقي غداً إن شاء الله ✨
            </div>
            """, unsafe_allow_html=True)
        
        else:
            if datetime.today().weekday() == 4: st.success("🕌 **يوم الجمعة!** لا تنسَ سنن الجمعة.")

            with st.form("f"):
                row = {c: "لا" for c in EXPECTED_HEADERS}
                row["القرآن"] = "0"; row["قيام"] = "0"; row["المجموعة"] = c_grp
                
                if c_grp in ["مجموعة الهدى", "مجموعة السائرين"]:
                    st.markdown(f"**تسجيل {c_grp}**")
                    st.markdown("🕌 **الفجر**")
                    row["الفجر_حالة"] = st.selectbox("الفجر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], label_visibility="collapsed")
                    
                    st.markdown("⏰ **الصلوات المفروضة**")
                    c1, c2, c3, c4 = st.columns(4)
                    row["الظهر_حالة"] = c1.selectbox("الظهر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"])
                    row["العصر_حالة"] = c2.selectbox("العصر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"])
                    row["المغرب_حالة"] = c3.selectbox("المغرب", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"])
                    row["العشاء_حالة"] = c4.selectbox("العشاء", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"])
                    
                    st.markdown("---")
                    c1, c2, c3 = st.columns(3)
                    c1.markdown("📖 **الورد**"); row["القرآن"] = c1.selectbox("الكمية", ["0", "ثمن", "ربع", "نصف", "حزب", "حزبين"])
                    c2.markdown("🌙 **قيام**"); 
                    if c2.checkbox("3 ركعات"): row["قيام"] = "3"
                    c3.markdown("🍽️ **صيام**"); 
                    if c3.checkbox("صمت اليوم"): row["الصيام"] = "نعم"

                else:
                    with st.expander("🕌 الصلوات", expanded=True):
                        c1, c2 = st.columns(2)
                        row["الفجر_حالة"] = c1.selectbox("الفجر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"])
                        if c1.checkbox("سنة الفجر"): row["الفجر_سنة"] = "نعم"
                        for p in ["الظهر", "العصر", "المغرب", "العشاء"]:
                            row[f"{p}_حالة"] = st.selectbox(p, ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"])
                    with st.expander("📖 أعمال"):
                        row["القرآن"] = st.selectbox("القرآن", ["0", "ثمن", "ربع", "نصف", "حزب"])

                sub = st.form_submit_button("✅ حفظ")
            
            if sub:
                # ⚠️ 3. ULTIME VERIFICATION AVANT ECRITURE
                already_in_sheet = False
                if not df.empty:
                    if not df[(df['الاسم']==c_user)&(df['الرمز_الشخصي']==c_pin)&(df['التاريخ'].astype(str)==today)].empty:
                        already_in_sheet = True
                
                # Si déjà en session OU déjà dans Sheet -> BLOQUAGE
                if st.session_state.get(session_done_key, False) or already_in_sheet:
                    st.error("⛔ تم التسجيل بالفعل!")
                    st.session_state[session_done_key] = True # On force le lock
                    time.sleep(2)
                    st.rerun()
                else:
                    final = [today, c_user, c_pin, c_grp] + [row.get(h, "لا") for h in EXPECTED_HEADERS[4:]]
                    try:
                        sheet_data.append_row(final)
                        
                        # 🔒 VERROUILLAGE IMMÉDIAT EN MÉMOIRE
                        st.session_state[session_done_key] = True
                        
                        row['المجموعة'] = c_grp
                        score_day = calculate_score(row)
                        new_tot = my_xp + score_day
                        nxt_lvl = get_level(new_tot)
                        rem = (nxt_lvl * 300) - new_tot
                        
                        st.balloons()
                        st.markdown(f"""
                        <div class="result-box">
                            <h3>🎉 تم الحفظ!</h3>
                            <h2>+{score_day} نقطة</h2>
                            <p>المجموع الجديد: <b>{new_tot}</b> | باقي للمستوى القادم: <b>{rem}</b></p>
                        </div>
                        """, unsafe_allow_html=True)
                        time.sleep(3)
                        st.rerun()
                    except Exception as e: st.error(f"Erreur: {e}")

    with t2:
        if not grp_df.empty:
            bd = grp_df.groupby(['الاسم', 'الرمز_الشخصي'])['Score'].sum().reset_index().sort_values('Score', ascending=False)
            bd['المستوى'] = bd['Score'].apply(get_level)
            bd.insert(0, '#', range(1, len(bd)+1))
            st.dataframe(bd[['#', 'الرمز_الشخصي', 'المستوى', 'Score']], use_container_width=True, hide_index=True)
        else: st.info("لا بيانات")

    with t3:
        if not df.empty:
            me = df[(df['الاسم']==c_user)&(df['الرمز_الشخصي']==c_pin)].sort_values('DateObj')
            if not me.empty:
                st.line_chart(me.set_index('DateObj')['Score'])
                cols = ['التاريخ', 'Score']
                if c_grp in ["مجموعة الهدى", "مجموعة السائرين"]: 
                    cols = ['التاريخ', 'الفجر_حالة', 'القرآن', 'Score']
                st.dataframe(me[cols], use_container_width=True)
            else: st.info("لا سجل")
