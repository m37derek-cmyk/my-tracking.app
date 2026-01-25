import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import random
import time

# ==========================================
# 1. CONFIGURATION ET DESIGN
# ==========================================
st.set_page_config(
    page_title="سباق الصالحين",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
        padding: 20px;
        border-right: 5px solid #009688;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        transition: transform 0.3s ease;
    }
    .metric-card h3 { margin: 0; font-size: 0.9rem; color: #666; }
    .metric-card h1 { margin: 0; font-size: 2rem; color: #009688; font-weight: bold; }

    .stButton>button {
        background: linear-gradient(135deg, #009688 0%, #00796b 100%);
        color: white !important;
        border-radius: 12px;
        border: none;
        padding: 12px 25px;
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
    
    .result-box {
        background-color: #e0f2f1;
        border: 2px solid #009688;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        margin-top: 20px;
        animation: fadeIn 1s;
    }
    .score-text {
        color: #00796b;
        font-size: 1.5em;
        font-weight: bold;
    }
    .next-level-text {
        color: #d84315;
        font-weight: bold;
        margin-top: 10px;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DONNÉES ET CONFIGURATION
# ==========================================
MOTIVATIONAL_QUOTES = [
    "أحب الأعمال إلى الله أدومها وإن قل",
    "ركعتا الفجر خير من الدنيا وما فيها",
    "والذاكرين الله كثيرا والذاكرات",
    "الصيام جنة",
    "أقرب ما يكون العبد من ربه وهو ساجد"
]

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
    "الفجر_حالة", "الفجر_سنة", "الضحى", 
    "الظهر_حالة", "الظهر_سنة",
    "العصر_حالة",
    "المغرب_حالة", "المغرب_سنة",
    "العشاء_حالة", "العشاء_سنة",
    "أذكار_الصباح", "أذكار_المساء", "أذكار_الصلاة", 
    "أذكار_النوم", "سورة_الملك",
    "قيام", "القرآن", "الصيام", "قراءة_كتاب", "أسرة", "مجلس التدارس", "التعهد",
    "جمعة_كهف", "جمعة_صلاة_نبي", "جمعة_صلاة_جمعة"
]

# ==========================================
# 3. CONNEXION GOOGLE SHEETS
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
    st.error(f"Erreur d'ouverture Sheet : {e}")
    st.stop()

# ==========================================
# 4. LOGIQUE MÉTIER & CALCULS
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

def safe_str(val):
    return str(val).strip() if val else ""

# 🧮 CALCUL DES POINTS
def calculate_score(row):
    score = 0
    group = safe_str(row.get('المجموعة'))
    
    # GROUPE AL HUDA & SAERIN (Points Boostés)
    if group in ["مجموعة الهدى", "مجموعة السائرين"]:
        fajr = safe_str(row.get('الفجر_حالة'))
        if fajr == 'جماعة (مسجد)': score += 50
        elif fajr == 'في الوقت (بيت)': score += 40
        
        prayers_map = {'الظهر_حالة', 'العصر_حالة', 'المغرب_حالة', 'العشاء_حالة'}
        for col in prayers_map:
            val = safe_str(row.get(col))
            if val == 'جماعة (مسجد)': score += 20
            elif val == 'في الوقت (بيت)': score += 15
            
        if safe_str(row.get('القرآن')) != '0': score += 30
        if "3" in safe_str(row.get('قيام')): score += 60 
        if safe_str(row.get('الصيام')) == 'نعم': score += 100
        
        return score

    # GROUPE STANDARD
    else:
        prayers_map = {'الفجر': 'الفجر_حالة', 'الظهر': 'الظهر_حالة', 'العصر': 'العصر_حالة', 'المغرب': 'المغرب_حالة', 'العشاء': 'العشاء_حالة'}
        for p_name, col_name in prayers_map.items():
            status = safe_str(row.get(col_name))
            if status == 'جماعة (مسجد)': score += 10
            elif status == 'في الوقت (بيت)': score += 6
            if p_name != 'العصر':
                if safe_str(row.get(f"{p_name}_سنة")) == 'نعم': score += 3
        if safe_str(row.get('الضحى')) == 'نعم': score += 5
        
        chk_list = ['أذكار_الصباح', 'أذكار_المساء', 'أذكار_الصلاة', 'أذكار_النوم']
        for chk in chk_list:
            if safe_str(row.get(chk)) == 'نعم': score += 3
        if safe_str(row.get('سورة_الملك')) == 'نعم': score += 5
        
        quran_val = safe_str(row.get('القرآن'))
        quran_points = {"ثمن": 2, "ربع": 4, "نصف": 6, "حزب": 8, "حزبين": 10}
        score += quran_points.get(quran_val, 0)
        
        qiyam_val = safe_str(row.get('قيام'))
        qiyam_points = {"ركعتان": 5, "3 ركعات": 8, "4 ركعات": 10, "6 ركعات": 12, "8 ركعات": 15}
        score += qiyam_points.get(qiyam_val, 0)

        good_deeds = ['الصيام', 'قراءة_كتاب', 'أسرة', 'مجلس التدارس', 'التعهد']
        points_deed = {'الصيام': 15, 'قراءة_كتاب': 4, 'أسرة': 4, 'مجلس التدارس': 4, 'التعهد': 4}
        for deed in good_deeds:
            if safe_str(row.get(deed)) == 'نعم': score += points_deed[deed]

        if safe_str(row.get('جمعة_كهف')) == 'نعم': score += 15
        if safe_str(row.get('جمعة_صلاة_نبي')) == 'نعم': score += 15
        if safe_str(row.get('جمعة_صلاة_جمعة')) == 'نعم': score += 20
        
        return min(score, 250)

def get_level_and_rank(total_points):
    # Palier de 300 points
    level = 1 + (int(total_points) // 300)
    return level

# ==========================================
# 5. PAGE DE CONNEXION
# ==========================================
if not st.session_state["authenticated"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background-color: white; padding: 40px; border-radius: 20px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
            <h1 style="color: #009688; margin-bottom: 10px;">🕌 سباق الصالحين</h1>
            <p style="color: #666; font-size: 1.1rem;">منصة التنافس الأخوي</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.text_input("👤 الاسم الكريم:", key="login_user")
        st.text_input("🔢 الرمز الشخصي:", type="password", key="login_pin")
        st.text_input("🔑 كلمة مرور المجموعة:", type="password", key="login_pass")
        st.button("🚀 دخول للسباق", on_click=check_login)
    st.stop()

# ==========================================
# 6. CHARGEMENT DONNÉES
# ==========================================
current_user = st.session_state["user_name"]
current_pin = st.session_state["user_pin"]
current_group = st.session_state["user_group"]

my_total_xp = 0
my_level = 1
my_rank = "-"
group_df = pd.DataFrame() 

try:
    data = sheet_data.get_all_records()
    full_df = pd.DataFrame(data)
except:
    full_df = pd.DataFrame()

if not full_df.empty:
    current_cols = full_df.columns.tolist()
    if not set(EXPECTED_HEADERS).issubset(current_cols):
        try: sheet_data.update('A1', [EXPECTED_HEADERS])
        except: pass

    for col in EXPECTED_HEADERS:
        if col not in full_df.columns: full_df[col] = ""

    # Nettoyage et Calculs
    full_df['المجموعة'] = full_df['المجموعة'].astype(str).str.strip()
    full_df['Score'] = full_df.apply(calculate_score, axis=1)
    full_df['Score'] = pd.to_numeric(full_df['Score'], errors='coerce').fillna(0)
    full_df['DateObj'] = pd.to_datetime(full_df['التاريخ'], errors='coerce')
    
    if current_group == "الإدارة":
        group_df = full_df.copy()
    else:
        group_df = full_df[full_df['المجموعة'] == current_group].copy()

    if not group_df.empty:
        temp_leaderboard = group_df.groupby(['الاسم', 'الرمز_الشخصي'])['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
        temp_leaderboard.insert(0, 'الترتيب', temp_leaderboard.index + 1)
        
        my_stats = temp_leaderboard[(temp_leaderboard['الاسم'] == current_user) & (temp_leaderboard['الرمز_الشخصي'].astype(str) == str(current_pin))]
        if not my_stats.empty:
            my_total_xp = my_stats.iloc[0]['Score']
            my_level = get_level_and_rank(my_total_xp)
            my_rank = my_stats.iloc[0]['الترتيب']

# ==========================================
# 7. INTERFACE PRINCIPALE
# ==========================================
col_h1, col_h2 = st.columns([6, 1])
with col_h1:
    st.markdown(f"### 🚩 {current_group}")
    st.caption(f"المتسابق: {current_user} | الرمز: {current_pin}")
with col_h2:
    if st.button("خروج", key="logout"):
        st.session_state["authenticated"] = False
        st.rerun()

# 📊 Calcul de progression
points_next = (my_level * 300) - my_total_xp
prog = max(0.0, min(1.0, 1 - (points_next / 300)))

if current_group != "الإدارة":
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1: st.markdown(f"""<div class="metric-card"><h3>🥇 الترتيب</h3><h1>#{my_rank}</h1></div>""", unsafe_allow_html=True)
    with kpi2: st.markdown(f"""<div class="metric-card"><h3>🛡️ المستوى</h3><h1>{my_level}</h1></div>""", unsafe_allow_html=True)
    with kpi3: st.markdown(f"""<div class="metric-card"><h3>✨ النقاط الكلية</h3><h1>{my_total_xp}</h1></div>""", unsafe_allow_html=True)
    
    st.markdown(f"<br>", unsafe_allow_html=True)
    st.progress(prog, text=f"🚀 باقي {points_next} نقطة للوصول للمستوى {my_level + 1}")

st.markdown("---")

# ==========================================
# 8. TABS (ENREGISTREMENT & RÉSULTATS)
# ==========================================
if current_group == "الإدارة":
    st.markdown("## 👮‍♂️ لوحة تحكم الإدارة")
    target_group = st.selectbox("🔍 عرض مجموعة:", list(GROUPS_CONFIG.keys())[:-1])
    
    if not full_df.empty:
        display_df = full_df[full_df['المجموعة'] == target_group].copy()
        if not display_df.empty:
            gen_board = display_df.groupby(['الاسم', 'الرمز_الشخصي'])['Score'].sum().reset_index().sort_values('Score', ascending=False)
            gen_board.insert(0, 'الترتيب', range(1, 1 + len(gen_board)))
            gen_board['المستوى'] = gen_board['Score'].apply(lambda x: get_level_and_rank(x))
            st.dataframe(gen_board, use_container_width=True, hide_index=True)
        else: st.info("لا توجد بيانات.")
else:
    tab1, tab2, tab3 = st.tabs(["📝 تسجيل اليوم", "🏆 لوحة الصدارة", "📈 تطور مستواي"])

    with tab1:
        st.markdown("### 🤲 تسجيل إنجاز اليوم")
        day_date = datetime.now().strftime("%Y-%m-%d")
        
        is_already_submitted = False
        if not full_df.empty:
            check_exists = full_df[
                (full_df['الاسم'] == current_user) & 
                (full_df['الرمز_الشخصي'].astype(str) == str(current_pin)) & 
                (full_df['التاريخ'].astype(str) == day_date)
            ]
            if not check_exists.empty:
                is_already_submitted = True

        if is_already_submitted:
            st.markdown(f"""
            <div class="success-box">
                <h2>✅ تم التسجيل بنجاح لهذا اليوم</h2>
                <p>تقبل الله طاعتكم. لا يمكنك التسجيل مرتين في نفس اليوم.</p>
            </div>
            """, unsafe_allow_html=True)
        
        else:
            if datetime.today().weekday() == 4: st.success("🕌 **يوم الجمعة!** لا تنسَ سنن الجمعة.")

            with st.form("entry_form"):
                data_row = {col: "لا" for col in EXPECTED_HEADERS}
                data_row["القرآن"] = "0"
                data_row["قيام"] = "0"
                data_row["المجموعة"] = current_group # Important pour le calcul du score
                
                # --- AL HUDA & SAERIN ---
                if current_group in ["مجموعة الهدى", "مجموعة السائرين"]:
                    st.markdown(f"**نموذج {current_group}**")
                    st.markdown("<div class='task-header'>🕌 صلاة الفجر</div>", unsafe_allow_html=True)
                    data_row["الفجر_حالة"] = st.selectbox("الفجر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], label_visibility="collapsed")
                    
                    st.markdown("<br><div class='task-header'>⏰ الصلوات المفروضة</div>", unsafe_allow_html=True)
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.markdown("**☀️ الظهر**")
                        data_row["الظهر_حالة"] = st.selectbox("الظهر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], label_visibility="collapsed")
                    with c2:
                        st.markdown("**🌤️ العصر**")
                        data_row["العصر_حالة"] = st.selectbox("العصر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], label_visibility="collapsed")
                    with c3:
                        st.markdown("**🌅 المغرب**")
                        data_row["المغرب_حالة"] = st.selectbox("المغرب", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], label_visibility="collapsed")
                    with c4:
                        st.markdown("**🌃 العشاء**")
                        data_row["العشاء_حالة"] = st.selectbox("العشاء", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], label_visibility="collapsed")
                    
                    st.markdown("<hr>", unsafe_allow_html=True)
                    
                    cc1, cc2, cc3 = st.columns(3)
                    with cc1:
                        st.markdown("<div class='task-header'>📖 الورد اليومي</div>", unsafe_allow_html=True)
                        data_row["القرآن"] = st.selectbox("الكمية", ["0", "ثمن", "ربع", "نصف", "حزب", "حزبين"], label_visibility="collapsed")
                    with cc2:
                        st.markdown("<div class='task-header'>🌙 قيام الليل</div>", unsafe_allow_html=True)
                        if st.checkbox("أديت 3 ركعات (الشفع والوتر)"): data_row["قيام"] = "3 ركعات"
                    with cc3:
                        st.markdown("<div class='task-header'>🍽️ صيام التطوع</div>", unsafe_allow_html=True)
                        if st.checkbox("نعم، صمت هذا اليوم"): data_row["الصيام"] = "نعم"

                # --- STANDARD ---
                else:
                    with st.expander("🕌 الصلوات المفروضة", expanded=True):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.markdown("**🌌 الفجر**")
                            data_row["الفجر_حالة"] = st.selectbox("الفجر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="f", label_visibility="collapsed")
                            if st.checkbox("سنة الفجر", key="fsn"): data_row["الفجر_سنة"] = "نعم"
                        with c2:
                            st.markdown("**☀️ الظهر**")
                            data_row["الظهر_حالة"] = st.selectbox("الظهر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="d", label_visibility="collapsed")
                            if st.checkbox("سنة الظهر", key="dsn"): data_row["الظهر_سنة"] = "نعم"
                        with c3:
                            st.markdown("**🌤️ العصر**")
                            data_row["العصر_حالة"] = st.selectbox("العصر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="a", label_visibility="collapsed")
                        st.markdown("---")
                        c4, c5, c6 = st.columns(3)
                        with c4:
                            st.markdown("**🌅 المغرب**")
                            data_row["المغرب_حالة"] = st.selectbox("المغرب", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="m", label_visibility="collapsed")
                            if st.checkbox("سنة المغرب", key="msn"): data_row["المغرب_سنة"] = "نعم"
                        with c5:
                            st.markdown("**🌃 العشاء**")
                            data_row["العشاء_حالة"] = st.selectbox("العشاء", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="i", label_visibility="collapsed")
                            if st.checkbox("سنة العشاء", key="isn"): data_row["العشاء_سنة"] = "نعم"
                        with c6:
                            st.markdown("**☀️ الضحى**")
                            if st.checkbox("صلاة الضحى", key="duha"): data_row["الضحى"] = "نعم"

                    with st.expander("📖 الروحانيات", expanded=False):
                        c_z1, c_z2 = st.columns(2)
                        with c_z1:
                            st.markdown("**📿 الأذكار**")
                            if st.checkbox("الصباح"): data_row["أذكار_الصباح"] = "نعم"
                            if st.checkbox("المساء"): data_row["أذكار_المساء"] = "نعم"
                            if st.checkbox("دبر الصلاة"): data_row["أذكار_الصلاة"] = "نعم"
                            if st.checkbox("النوم"): data_row["أذكار_النوم"] = "نعم"
                            if st.checkbox("سورة الملك"): data_row["سورة_الملك"] = "نعم"
                        with c_z2:
                            st.markdown("**🌙 القرآن والقيام**")
                            data_row["القرآن"] = st.selectbox("الورد القرآني", ["0", "ثمن", "ربع", "نصف", "حزب", "حزبين"])
                            data_row["قيام"] = st.selectbox("قيام الليل", ["0", "ركعتان", "4 ركعات", "6 ركعات", "8 ركعات"])

                    with st.expander("🌱 أعمال البر", expanded=False):
                        b1, b2, b3, b4, b5 = st.columns(5)
                        if b1.checkbox("صيام"): data_row["الصيام"] = "نعم"
                        if b2.checkbox("قراءة"): data_row["قراءة_كتاب"] = "نعم"
                        if b3.checkbox("بر"): data_row["أسرة"] = "نعم"
                        if b4.checkbox("تدارس"): data_row["مجلس التدارس"] = "نعم"
                        if b5.checkbox("تعهد"): data_row["التعهد"] = "نعم"

                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("✅ حفظ وتسجيل النقاط", use_container_width=True)

            # TRAITEMENT APRÈS SOUMISSION (HORS FORMULAIRE)
            if submitted:
                # Double vérification pour éviter le double clic
                already_done = False
                if not full_df.empty:
                    check_exists_now = full_df[
                        (full_df['الاسم'] == current_user) & 
                        (full_df['الرمز_الشخصي'].astype(str) == str(current_pin)) & 
                        (full_df['التاريخ'].astype(str) == day_date)
                    ]
                    if not check_exists_now.empty:
                        already_done = True
                
                if already_done:
                    st.error("⛔ تم التسجيل بالفعل! لا يمكن الإرسال مرتين.")
                else:
                    final_row = []
                    data_row["التاريخ"] = day_date
                    data_row["الاسم"] = current_user
                    data_row["الرمز_الشخصي"] = current_pin
                    data_row["المجموعة"] = current_group
                    
                    # Préparation de la liste ordonnée
                    for header in EXPECTED_HEADERS:
                        final_row.append(data_row.get(header, "لا"))
                    
                    try:
                        with st.spinner("جاري حساب النقاط والحفظ..."):
                            sheet_data.append_row(final_row)
                            
                            # 🧮 CALCUL IMMÉDIAT DU SCORE DU JOUR
                            daily_score = calculate_score(data_row)
                            
                            # 🧮 CALCUL PROJECTION NIVEAU SUIVANT
                            new_total_xp = my_total_xp + daily_score
                            new_level = 1 + (int(new_total_xp) // 300)
                            points_needed_now = (new_level * 300) - new_total_xp
                            
                            st.balloons()
                            
                            # ✨ AFFICHAGE DU RÉSULTAT (RESULT BOX)
                            st.markdown(f"""
                            <div class="result-box">
                                <h3>🎉 تم الحفظ بنجاح!</h3>
                                <p>حصدت اليوم:</p>
                                <div class="score-text">+{daily_score} نقطة</div>
                                <hr style="border-top: 1px dashed #009688;">
                                <p>مجموع نقاطك الجديد: <b>{new_total_xp}</b></p>
                                <div class="next-level-text">🚀 باقي {points_needed_now} نقطة للمستوى {new_level + 1}</div>
                            </div>
                            """, unsafe_allow_html=True)

                            if st.button("🔄 تحديث الصفحة (إغلاق)"):
                                st.rerun()
                                
                    except Exception as e:
                        st.error(f"خطأ تقني: {e}")

        # === 📅 HISTORIQUE RAPIDE ===
        st.markdown("---")
        st.markdown("### 📅 سجلي السابق")
        if not full_df.empty:
            my_history_full = full_df[
                (full_df['الاسم'] == current_user) & 
                (full_df['الرمز_الشخصي'].astype(str) == str(current_pin))
            ].copy()
            if not my_history_full.empty:
                my_history_full = my_history_full.sort_values('DateObj', ascending=False)
                cols_to_show = ['التاريخ', 'Score'] # Simple pour la vue mobile
                valid_cols = [c for c in cols_to_show if c in my_history_full.columns]
                st.dataframe(my_history_full[valid_cols], use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("### 🏆 لوحة الصدارة (مجموعتي)")
        if not full_df.empty:
            display_df = full_df[full_df['المجموعة'] == current_group].copy()
            if not display_df.empty:
                gen_board = display_df.groupby(['الاسم', 'الرمز_الشخصي'])['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
                gen_board['المستوى'] = gen_board['Score'].apply(lambda x: get_level_and_rank(x)[0])
                gen_board.insert(0, 'الترتيب', gen_board.index + 1)
                
                st.dataframe(
                    gen_board[['الترتيب', 'الرمز_الشخصي', 'المستوى', 'Score']].rename(columns={'الرمز_الشخصي': 'الرمز'}), 
                    use_container_width=True, hide_index=True
                )
            else: st.info("لا توجد بيانات لهذه المجموعة.")
        else: st.info("قاعدة البيانات فارغة.")

    with tab3:
        st.markdown("### 📈 تطور مستواي")
        if not full_df.empty:
            my_hist = full_df[full_df['الرمز_الشخصي'].astype(str) == str(current_pin)].copy()
            if not my_hist.empty:
                my_hist = my_hist.dropna(subset=['DateObj']).sort_values(by='DateObj')
                my_hist.set_index('DateObj', inplace=True)
                st.line_chart(my_hist['Score'])
            else: st.info("لا يوجد سجل سابق.")
        else: st.info("لا يوجد سجل سابق.")
