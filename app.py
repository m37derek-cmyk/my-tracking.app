import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import os
import random
import time 

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="سباق الصالحين", 
    layout="wide", 
    page_icon="🕌",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🎨 التصميم الجذاب (CSS + Fonts)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
    }
    .stApp {
        background-color: #f8f9fa;
        background-image: radial-gradient(#e2e2e2 1px, transparent 1px);
        background-size: 20px 20px;
    }
    .login-container {
        background-color: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        text-align: center;
        border-top: 5px solid #009688;
    }
    .stButton>button {
        background: linear-gradient(45deg, #009688, #4DB6AC);
        color: white;
        border-radius: 12px;
        border: none;
        padding: 10px 25px;
        font-weight: bold;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 5px 15px rgba(0, 150, 136, 0.4);
    }
    .metric-card {
        background-color: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        text-align: center;
        transition: transform 0.3s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: #009688;
    }
    h1, h2, h3 { color: #2c3e50; }
    .champion-box {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
        border: 2px solid #ffc107;
        border-radius: 15px;
        padding: 20px;
        color: #856404;
        text-align: center;
        box-shadow: 0 4px 15px rgba(255, 193, 7, 0.3);
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔑 إعدادات المجموعات
# ==========================================
GROUPS_CONFIG = {
    "مجموعة الفردوس": "Firdaws2025",
    "مجموعة الريان": "Rayyan2025",
    "الإدارة": "Admin123"
}

# ==========================================
# 📋 عناوين الأعمدة
# ==========================================
EXPECTED_HEADERS = [
    "التاريخ", "الاسم", "المجموعة",
    "الفجر_حالة", "الفجر_سنة", "الضحى", 
    "الظهر_حالة", "الظهر_سنة",
    "العصر_حالة",
    "المغرب_حالة", "المغرب_سنة",
    "العشاء_حالة", "العشاء_سنة",
    "أذكار_الصباح", "أذكار_المساء", "أذكار_الصلاة", 
    "أذكار_النوم", "سورة_الملك",
    "قيام", "القرآن", "صيام التطوع", "مجلس التدارس", "أسرة", "قراءة", "زيارة",
    "جمعة_كهف", "جمعة_صلاة_نبي"
]

# ==========================================
# 💎 مكتبة التحفيز
# ==========================================
MOTIVATIONAL_QUOTES = [
    {"text": "يُصْبِحُ عَلَى كُلِّ سُلَامَى مِنْ أَحَدِكُمْ صَدَقَةٌ... وَيُجْزِئُ مِنْ ذَلِكَ رَكْعَتَانِ يَرْكَعُهُمَا مِنَ الضُّحَى", "source": "حديث شريف"},
    {"text": "سورة تبارك هي المانعة من عذاب القبر", "source": "حديث شريف"},
    {"text": "إِنَّ اللَّهَ وَمَلَائِكَتَهُ يُصَلُّونَ عَلَى النَّبِيِّ", "source": "الأحزاب: 56"},
    {"text": "وَفِي ذَٰلِكَ فَلْيَتَنَافَسِ الْمُتَنَافِسُونَ", "source": "المطففين: 26"},
    {"text": "يد الله مع الجماعة", "source": "حديث شريف"},
    {"text": "أَحَبُّ الأعمالِ إلى اللهِ أدْومُها وإنْ قَلَّ", "source": "حديث شريف"},
    {"text": "فَاذْكُرُونِي أَذْكُرْكُمْ", "source": "البقرة: 152"},
    {"text": "الكلمة الطيبة صدقة", "source": "حديث شريف"},
    {"text": "وَمَنْ يَتَّقِ اللَّهَ يَجْعَلْ لَهُ مَخْرَجًا", "source": "الطلاق: 2"},
    {"text": "مَنْ سَلَكَ طَرِيقًا يَلْتَمِسُ فِيهِ عِلْمًا سَهَّلَ اللَّهُ لَهُ بِهِ طَرِيقًا إِلَى الْجَنَّةِ", "source": "حديث شريف"},
    {"text": "إِنَّ الْحَسَنَاتِ يُذْهِبْنَ السَّيِّئَاتِ", "source": "هود: 114"},
    {"text": "تبسمك في وجه أخيك صدقة", "source": "حديث شريف"},
    {"text": "وَاسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ", "source": "البقرة: 45"},
    {"text": "الدال على الخير كفاعله", "source": "حديث شريف"},
    {"text": "لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا", "source": "البقرة: 286"},
    {"text": "مَا نَقَصَتْ صَدَقَةٌ مِنْ مَالٍ", "source": "حديث شريف"},
    {"text": "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ", "source": "الرعد: 28"},
    {"text": "اغتنم خمساً قبل خمس: شبابك قبل هرمك...", "source": "حديث شريف"},
    {"text": "وَقُلِ اعْمَلُوا فَسَيَرَى اللَّهُ عَمَلَكُمْ وَرَسُولُهُ وَالْمُؤْمِنُونَ", "source": "التوبة: 105"},
    {"text": "خيركم من تعلم القرآن وعلمه", "source": "حديث شريف"},
    {"text": "ادْعُونِي أَسْتَجِبْ لَكُمْ", "source": "غافر: 60"},
    {"text": "الطُّهُورُ شَطْرُ الْإِيمَانِ", "source": "حديث شريف"},
    {"text": "إِنَّ مَعَ الْعُسْرِ يُسْرًا", "source": "الشرح: 6"},
    {"text": "من صلى البردين (الفجر والعصر) دخل الجنة", "source": "حديث شريف"},
    {"text": "وَأَن لَّيْسَ لِلْإِنسَانِ إِلَّا مَا سَعَىٰ", "source": "النجم: 39"},
    {"text": "اتق الله حيثما كنت، وأتبع السيئة الحسنة تمحها", "source": "حديث شريف"},
    {"text": "فَاصْبِرْ صَبْرًا جَمِيلًا", "source": "المعارج: 5"},
    {"text": "ركعتا الفجر خير من الدنيا وما فيها", "source": "حديث شريف"},
    {"text": "وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا", "source": "العنكبوت: 69"},
    {"text": "تهادوا تحابوا", "source": "حديث شريف"},
    {"text": "رَبِّ إِنِّي لِمَا أَنزَلْتَ إِلَيَّ مِنْ خَيْرٍ فَقِيرٌ", "source": "القصص: 24"},
    {"text": "المؤمن للمؤمن كالبنيان يشد بعضه بعضاً", "source": "حديث شريف"},
    {"text": "وَعَجِلْتُ إِلَيْكَ رَبِّ لِتَرْضَىٰ", "source": "طه: 84"},
    {"text": "أقرب ما يكون العبد من ربه وهو ساجد", "source": "حديث شريف"},
    {"text": "إِنَّمَا الأَعْمَالُ بِالنِّيَّاتِ", "source": "حديث شريف"}
]
daily_quote = random.choice(MOTIVATIONAL_QUOTES)

WEEKLY_IDEAS = {
    "❤️ عمل خيري": ["ماء للعمال", "تنظيف مسجد", "صدقة", "زيارة مريض", "إطعام طير"],
    "🍉 طعام": ["فطور جماعي", "عشاء خفيف", "قهوة"],
    "⚽ ترفيه": ["كرة قدم", "مشي 30د", "مسابقة", "كشتة"]
}

# ==========================================
# 🚀 الاتصال بقاعدة البيانات
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
    sheet_data = sh.sheet1 
    try:
        current_headers = sheet_data.row_values(1)
        if not current_headers or current_headers != EXPECTED_HEADERS:
            sheet_data.delete_rows(1)
            sheet_data.insert_row(EXPECTED_HEADERS, 1)
    except: pass
except Exception as e:
    st.error(f"خطأ في فتح الملف: {e}")
    st.stop()

# ==========================================
# 🔒 صفحة تسجيل الدخول
# ==========================================
def check_login():
    input_user = st.session_state["login_user"].strip()
    input_pass = st.session_state["login_pass"].strip()
    
    found_group = None
    for group_name, group_pass in GROUPS_CONFIG.items():
        if input_pass == group_pass:
            found_group = group_name
            break
            
    if found_group and input_user:
        st.session_state["authenticated"] = True
        st.session_state["user_name"] = input_user
        st.session_state["user_group"] = found_group
    else:
        st.toast("⛔ اسم المستخدم أو كلمة المرور غير صحيحة", icon="❌")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="login-container">
            <h1 style="color: #009688;">🕌 سباق الصالحين</h1>
            <p style="color: #666; font-size: 1.1em;">منصة التنافس الأخوي في الطاعات</p>
            <hr style="border-top: 1px solid #eee; margin: 20px 0;">
        </div>
        """, unsafe_allow_html=True)
        
        st.info("👋 أهلاً بك! أدخل اسمك وكلمة مرور مجموعتك")
        st.text_input("👤 الاسم الكريم:", key="login_user", placeholder="اكتب اسمك هنا...")
        st.text_input("🔑 كلمة المرور:", type="password", key="login_pass", placeholder="رمز المجموعة...")
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("🚀 انطلق في السباق", on_click=check_login, use_container_width=True)
        st.markdown("""<div style="text-align: center; margin-top: 20px; font-size: 0.9em; color: #888;">"وفي ذلك فليتنافس المتنافسون"</div>""", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 🧮 محرك الحسابات
# ==========================================
def calculate_score(row):
    score = 0
    # الصلوات
    prayers_map = {'الفجر': 'الفجر_حالة', 'الظهر': 'الظهر_حالة', 'العصر': 'العصر_حالة', 'المغرب': 'المغرب_حالة', 'العشاء': 'العشاء_حالة'}
    for p_name, col_name in prayers_map.items():
        status = row.get(col_name)
        if status == 'جماعة (مسجد)': score += 10
        elif status == 'في الوقت (بيت)': score += 6
        if p_name != 'العصر':
            if row.get(f"{p_name}_سنة") == 'نعم': score += 3
    if row.get('الضحى') == 'نعم': score += 5
    
    # الأذكار
    if row.get('أذكار_الصباح') == 'نعم': score += 3
    if row.get('أذكار_المساء') == 'نعم': score += 3
    if row.get('أذكار_الصلاة') == 'نعم': score += 3
    if row.get('أذكار_النوم') == 'نعم': score += 3 
    if row.get('سورة_الملك') == 'نعم': score += 5 
    
    # الورد القرآني (نقاط متدرجة)
    quran_val = str(row.get('القرآن'))
    quran_points = {"ثمن": 2, "ربع": 4, "نصف": 6, "حزب": 8, "حزبين": 10}
    score += quran_points.get(quran_val, 0)
    
    # قيام الليل (نقاط متدرجة)
    qiyam_val = str(row.get('قيام'))
    qiyam_points = {"ركعتان": 3, "٤ ركعات": 5, "٦ ركعات": 7, "٨ ركعات": 10}
    score += qiyam_points.get(qiyam_val, 0)

    # الباقي
    if row.get('الصيام') == 'نعم': score += 10
    if row.get('مجلس التدارس') == 'نعم': score += 4
    if row.get('أسرة') == 'نعم': score += 4
    if row.get('قراءة كتاب') == 'نعم': score += 4
    if row.get('زيارة') == 'نعم': score += 4
    # الجمعة
    if row.get('جمعة_كهف') == 'نعم': score += 15
    if row.get('جمعة_صلاة_نبي') == 'نعم': score += 15
    return min(score, 145)

def get_level_and_rank(total_points):
    level = 1 + (total_points // 500)
    if level < 5: title = "مبتدئ (🌱)"
    elif level < 10: title = "مجتهد (💪)"
    elif level < 20: title = "سابق (🚀)"
    else: title = "رباني (👑)"
    return level, title

# ==========================================
# 📊 تجهيز البيانات
# ==========================================
current_user = st.session_state["user_name"]
current_group = st.session_state["user_group"]

try:
    data = sheet_data.get_all_records()
    full_df = pd.DataFrame(data)
except:
    full_df = pd.DataFrame()

leaderboard = pd.DataFrame(); weekly_leaderboard = pd.DataFrame(); daily_leaderboard = pd.DataFrame()
weekly_champion_name = "---"; weekly_champion_score = 0
daily_champion_name = "---"; daily_champion_score = 0
my_total_xp = 0; my_level = 1; my_rank = "-"

if not full_df.empty:
    missing_cols = [c for c in EXPECTED_HEADERS if c not in full_df.columns]
    if not missing_cols:
        full_df['Score'] = full_df.apply(calculate_score, axis=1)
        full_df['DateObj'] = pd.to_datetime(full_df['التاريخ'], errors='coerce')
        
        if current_group != "الإدارة":
            group_df = full_df[full_df['المجموعة'] == current_group].copy()
        else:
            group_df = full_df.copy()

        if not group_df.empty:
            leaderboard = group_df.groupby('الاسم')['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
            leaderboard['المستوى'] = leaderboard['Score'].apply(lambda x: get_level_and_rank(x)[0])
            leaderboard['اللقب'] = leaderboard['Score'].apply(lambda x: get_level_and_rank(x)[1])
            leaderboard.insert(0, 'الترتيب', leaderboard.index + 1)

            my_stats = leaderboard[leaderboard['الاسم'] == current_user]
            if not my_stats.empty:
                my_total_xp = my_stats.iloc[0]['Score']
                my_level = my_stats.iloc[0]['المستوى']
                my_rank = my_stats.iloc[0]['الترتيب']

            curr_wk = datetime.now().isocalendar()[1]
            curr_yr = datetime.now().year
            weekly_df = group_df[(group_df['DateObj'].dt.isocalendar().week == curr_wk) & (group_df['DateObj'].dt.year == curr_yr)]
            if not weekly_df.empty:
                weekly_leaderboard = weekly_df.groupby('الاسم')['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
                weekly_leaderboard.insert(0, 'الترتيب', weekly_leaderboard.index + 1)
                if not weekly_leaderboard.empty:
                    weekly_champion_name = weekly_leaderboard.iloc[0]['الاسم']
                    weekly_champion_score = weekly_leaderboard.iloc[0]['Score']

            today_str = datetime.now().strftime("%Y-%m-%d")
            daily_df = group_df[group_df['التاريخ'] == today_str]
            if not daily_df.empty:
                daily_leaderboard = daily_df[['الاسم', 'Score']].sort_values('Score', ascending=False).reset_index(drop=True)
                daily_leaderboard.insert(0, 'الترتيب', daily_leaderboard.index + 1)
                if not daily_leaderboard.empty:
                    daily_champion_name = daily_leaderboard.iloc[0]['الاسم']
                    daily_champion_score = daily_leaderboard.iloc[0]['Score']

# ==========================================
# 🖥️ الواجهة الرئيسية
# ==========================================
col_logo, col_title, col_logout = st.columns([1, 4, 1])
with col_title:
    st.markdown(f"<h1 style='text-align: center; color: #009688;'>🏆 {current_group} 🏆</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'>مرحباً بالمجتهد <b>{current_user}</b></p>", unsafe_allow_html=True)
with col_logout:
    st.write("")
    if st.button("🚪 خروج", key="logout_btn"): st.session_state["authenticated"] = False; st.rerun()

st.markdown("---")
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f"""<div class="metric-card"><h3>🥇 الترتيب</h3><h1 style="color:#009688;">#{my_rank}</h1></div>""", unsafe_allow_html=True)
with c2: st.markdown(f"""<div class="metric-card"><h3>🛡️ المستوى</h3><h1 style="color:#FBC02D;">{my_level}</h1><small>{get_level_and_rank(my_total_xp)[1]}</small></div>""", unsafe_allow_html=True)
with c3: st.markdown(f"""<div class="metric-card"><h3>✨ النقاط</h3><h1 style="color:#1565C0;">{my_total_xp}</h1></div>""", unsafe_allow_html=True)

points_next_level = (my_level * 500) - my_total_xp
progress = 1 - (points_next_level / 500)
st.markdown("<br>", unsafe_allow_html=True)
st.progress(max(0.0, min(1.0, progress)), text=f"🚀 باقي {points_next_level} نقطة للوصول للمستوى التالي")

st.markdown(f"""<div style="background-color: #e0f2f1; padding: 15px; border-radius: 10px; margin: 20px 0; border-right: 5px solid #009688;"><h4 style="margin:0; color: #00695c;">🌿 حكمة اليوم</h4><p style="font-size: 1.1em; margin-top:5px;"><i>"{daily_quote['text']}"</i> <br><span style="font-size:0.8em; color:#666;">— {daily_quote['source']}</span></p></div>""", unsafe_allow_html=True)

st.markdown(f"""<div class="champion-box"><h3 style="margin:0;">👑 بطل الأسبوع</h3><h1 style="font-size: 2.5em; margin: 10px 0;">{weekly_champion_name}</h1><p>مجموع {weekly_champion_score} نقطة هذا الأسبوع</p></div>""", unsafe_allow_html=True)

with st.expander("🎁 انقر هنا لرؤية جائزة البطل (الاختيار)", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1: 
        st.info("**❤️ خيري**")
        for i in WEEKLY_IDEAS["❤️ عمل خيري"]: st.write(f"- {i}")
    with c2: 
        st.warning("**🍉 طعام**")
        for i in WEEKLY_IDEAS["🍉 طعام"]: st.write(f"- {i}")
    with c3: 
        st.success("**⚽ ترفيه**")
        for i in WEEKLY_IDEAS["⚽ ترفيه"]: st.write(f"- {i}")

st.markdown("<br>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["📝 تسجيل إنجاز اليوم", "🏆 لوحة الصدارة", "📊 سجلي الشخصي"])

with tab1:
    st.markdown("### 🤲 اللهم تقبل منا")
    is_friday = datetime.today().weekday() == 4
    if is_friday: st.success("🕌 اليوم الجمعة! لا تنس السنن الإضافية")
    
    with st.form("entry_form"):
        if is_friday:
            col_f1, col_f2 = st.columns(2)
            kahf = col_f1.checkbox("📖 قراءة سورة الكهف (+15)")
            salat_nabi = col_f2.checkbox("📿 الصلاة على النبي 100 مرة (+15)")
            st.markdown("---")
        else:
            kahf = False; salat_nabi = False

        st.markdown("##### 🕌 الصلوات المفروضة")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.markdown("**الفجر**")
            fajr_st = st.selectbox("الحالة", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="fs", label_visibility="collapsed")
            fajr_sn = st.checkbox("السنة الراتبة", key="fsn")
        with col_p2:
            st.markdown("**الظهر**")
            dhuhr_st = st.selectbox("الحالة", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="ds", label_visibility="collapsed")
            dhuhr_sn = st.checkbox("السنة الراتبة", key="dsn")
        with col_p3:
            st.markdown("**العصر**")
            asr_st = st.selectbox("الحالة", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="as", label_visibility="collapsed")

        st.markdown("<br>", unsafe_allow_html=True)
        col_p4, col_p5, col_p6 = st.columns(3)
        with col_p4:
            st.markdown("**المغرب**")
            mag_st = st.selectbox("الحالة", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="ms", label_visibility="collapsed")
            mag_sn = st.checkbox("السنة الراتبة", key="msn")
        with col_p5:
            st.markdown("**العشاء**")
            isha_st = st.selectbox("الحالة", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="is", label_visibility="collapsed")
            isha_sn = st.checkbox("السنة الراتبة", key="isn")
        with col_p6:
            st.markdown("**☀️ الضحى**")
            duha = st.checkbox("ركعتا الضحى (+5)", key="duha")

        st.markdown("---")
        st.markdown("##### 📿 الأذكار والقرآن")
        c_az1, c_az2, c_az3, c_az4 = st.columns(4)
        az_m = c_az1.checkbox("أذكار الصباح")
        az_e = c_az2.checkbox("أذكار المساء")
        az_p = c_az3.checkbox("أذكار الصلاة")
        with c_az4:
            az_s = st.checkbox("أذكار النوم")
            mulk = st.checkbox("سورة الملك")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- التعديل هنا: صناديق الاختيارات للقيام والقرآن ---
        c_q1, c_q2 = st.columns(2)
        qiyam = c_q1.selectbox("🌙 قيام الليل", ["0", "ركعتان", "٤ ركعات", "٦ ركعات", "٨ ركعات"])
        quran = c_q2.selectbox("📖 الورد القرآني", ["0", "ثمن", "ربع", "نصف", "حزب", "حزبين"])
        # -----------------------------------------------------

        st.markdown("---")
        st.markdown("##### 🌱 أعمال البر")
        cc1, cc2, cc3, cc4, cc5 = st.columns(5)
        fasting = cc1.checkbox(" صيام التطوع")
        majlis = cc2.checkbox("مجلس علم")
        family = cc3.checkbox("بر الأسرة")
        read = cc4.checkbox("قراءة نافعة")
        visit = cc5.checkbox("زيارة/صلة")

        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.form_submit_button("✅ حفظ الأعمال", use_container_width=True)

        if submit:
            day_date = datetime.now().strftime("%Y-%m-%d")
            user_specific_df = full_df[full_df['الاسم'] == current_user] if not full_df.empty else pd.DataFrame()
            if not user_specific_df.empty and day_date in user_specific_df['التاريخ'].astype(str).values:
                st.error(f"⛔ لقد قمت بتسجيل يوم {day_date} مسبقاً")
            else:
                row = [
                    day_date, current_user, current_group,
                    fajr_st, "نعم" if fajr_sn else "لا", "نعم" if duha else "لا",
                    dhuhr_st, "نعم" if dhuhr_sn else "لا",
                    asr_st,
                    mag_st, "نعم" if mag_sn else "لا",
                    isha_st, "نعم" if isha_sn else "لا",
                    "نعم" if az_m else "لا", "نعم" if az_e else "لا", "نعم" if az_p else "لا",
                    "نعم" if az_s else "لا", "نعم" if mulk else "لا",
                    qiyam, quran, # تخزين القيمة النصية كما هي
                    "نعم" if fasting else "لا", "نعم" if majlis else "لا",
                    "نعم" if family else "لا", "نعم" if read else "لا", "نعم" if visit else "لا",
                    "نعم" if kahf else "لا", "نعم" if salat_nabi else "لا"
                ]
                with st.spinner("جاري الحفظ..."):
                    sheet_data.append_row(row)
                    st.balloons()
                    st.toast("تم حفظ إنجازك بنجاح! تقبل الله", icon="✅")
                    time.sleep(2)
                    st.rerun()

with tab2:
    st.markdown("### 📊 لوحة الصدارة")
    t2_1, t2_2, t2_3 = st.tabs(["🥇 العام", "📅 الأسبوعي", "🌟 اليومي"])
    with t2_1: 
        if not leaderboard.empty: st.dataframe(leaderboard[['الترتيب', 'الاسم', 'المستوى', 'Score', 'اللقب']], use_container_width=True, hide_index=True)
        else: st.info("لا توجد بيانات بعد")
    with t2_2: 
        if not weekly_leaderboard.empty: st.dataframe(weekly_leaderboard[['الترتيب', 'الاسم', 'Score']], use_container_width=True, hide_index=True)
        else: st.info("بداية أسبوع جديدة")
    with t2_3: 
        if not daily_leaderboard.empty: 
            st.dataframe(daily_leaderboard[['الترتيب', 'الاسم', 'Score']], use_container_width=True, hide_index=True)
            st.success(f"نجم اليوم: {daily_champion_name}")
        else: st.info("لم يسجل أحد اليوم")

with tab3:
    st.markdown("### 📈 سجلي البياني")
    if not full_df.empty and current_user in full_df['الاسم'].values:
        my_hist = full_df[full_df['الاسم'] == current_user]
        st.area_chart(my_hist.set_index("التاريخ")['Score'], color="#009688")
        st.dataframe(my_hist, use_container_width=True)
    else: st.info("ليس لديك سجلات سابقة")




