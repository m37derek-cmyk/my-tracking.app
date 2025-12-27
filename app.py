import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
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
# 🎨 التصميم (CSS - عربي حديث)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
    }
    
    .stApp { background-color: #f8f9fa; }

    /* تنسيق الاقتباس */
    .quote-box {
        background-color: #e0f2f1;
        border-right: 5px solid #009688;
        padding: 20px;
        margin: 20px 0;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .quote-text {
        font-size: 1.3rem;
        color: #00695c;
        font-weight: bold;
        margin-bottom: 8px;
    }
    .quote-source {
        font-size: 0.95rem;
        color: #555;
        font-style: italic;
    }

    .metric-card {
        background-color: white;
        border-radius: 15px;
        padding: 20px;
        border-right: 5px solid #009688;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        transition: transform 0.3s ease;
    }
    .metric-card:hover { transform: translateY(-5px); }
    .metric-card h3 { margin: 0; font-size: 1rem; color: #666; }
    .metric-card h1 { margin: 0; font-size: 2.5rem; color: #009688; font-weight: bold; }

    .stButton>button {
        background: linear-gradient(135deg, #009688 0%, #00796b 100%);
        color: white !important;
        border-radius: 12px;
        border: none;
        padding: 12px 25px;
        font-size: 1.1rem;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 150, 136, 0.3);
        width: 100%;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(0, 150, 136, 0.5);
    }
    
    .streamlit-expanderHeader {
        background-color: white;
        border-radius: 10px;
        font-weight: bold;
        color: #333;
    }

    h1, h2, h3, h4 { color: #2c3e50 !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 💎 اقتباسات (مع المصدر)
# ==========================================
MOTIVATIONAL_QUOTES = [
    {"text": "﴿ وَفِي ذَلِكَ فَلْيَتَنَافَسِ الْمُتَنَافِسُونَ ﴾", "source": "سورة المطففين: 26"},
    {"text": "﴿ وَأَن لَّيْسَ لِلْإِنسَانِ إِلَّا مَا سَعَىٰ ﴾", "source": "سورة النجم: 39"},
    {"text": "(( أحبُّ الأعمالِ إلى اللهِ أدْومُها وإنْ قَلَّ ))", "source": "حديث شريف (متفق عليه)"},
    {"text": "﴿ فَاذْكُرُونِي أَذْكُرْكُمْ وَاشْكُرُوا لِي وَلَا تَكْفُرُونِ ﴾", "source": "سورة البقرة: 152"},
    {"text": "﴿ إِنَّ اللَّهَ لَا يُضِيعُ أَجْرَ الْمُحْسِنِينَ ﴾", "source": "سورة التوبة: 120"},
    {"text": "(( اغتنمْ خمسًا قبل خمسٍ: شبابَك قبل هرمك... ))", "source": "حديث شريف"},
    {"text": "﴿ وَاصْبِرْ لِحُكْمِ رَبِّكَ فَإِنَّكَ بِأَعْيُنِنَا ﴾", "source": "سورة الطور: 48"},
    {"text": "﴿ وَسَارِعُوا إِلَىٰ مَغْفِرَةٍ مِّن رَّبِّكُمْ ﴾", "source": "سورة آل عمران: 133"},
    {"text": "(( الطهور شطر الإيمان، والحمد لله تملأ الميزان ))", "source": "رواه مسلم"},
    {"text": "﴿ أَلا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ ﴾", "source": "سورة الرعد: 28"},
    {"text": "(( المؤمن القوي خيرٌ وأحبُّ إلى الله من المؤمن الضعيف ))", "source": "رواه مسلم"},
    {"text": "﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ﴾", "source": "سورة العنكبوت: 69"},
    {"text": "(( الدال على الخير كفاعله ))", "source": "حديث شريف"},
    {"text": "﴿ لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا ﴾", "source": "سورة البقرة: 286"},
    {"text": "﴿ فَاسْتَقِمْ كَمَا أُمِرْتَ ﴾", "source": "سورة هود: 112"},
    {"text": "(( مَن سلك طريقًا يلتمس فيه علمًا، سهَّل الله له طريقًا للجنة ))", "source": "رواه مسلم"},
    {"text": "﴿ وَمَن يَتَّقِ اللَّهَ يَجْعَل لَّهُ مَخْرَجًا ﴾", "source": "سورة الطلاق: 2"},
    {"text": "(( اتقِ اللهَ حيثما كنتَ، وأتبعِ السيئةَ الحسنةَ تمحُها ))", "source": "رواه الترمذي"},
    {"text": "﴿ لَا تَقْنَطُوا مِن رَّحْمَةِ اللَّهِ ﴾", "source": "سورة الزمر: 53"},
    {"text": "(( إنما الأعمال بالنيات، وإنما لكل امرئ ما نوى ))", "source": "متفق عليه"},
    {"text": "﴿ وَبَشِّرِ الصَّابِرِينَ ﴾", "source": "سورة البقرة: 155"},
    {"text": "(( عجباً لأمر المؤمن إن أمره كله خير ))", "source": "رواه مسلم"},
    {"text": "﴿ ادْعُونِي أَسْتَجِبْ لَكُمْ ﴾", "source": "سورة غافر: 60"},
    {"text": "(( سبحان الله وبحمده، سبحان الله العظيم ))", "source": "متفق عليه"},
    {"text": "﴿ إِنَّ مَعَ الْعُسْرِ يُسْرًا ﴾", "source": "سورة الشرح: 6"},
    {"text": "﴿ مَا عِندَكُمْ يَنفَدُ ۖ وَمَا عِندَ اللَّهِ بَاقٍ ﴾", "source": "سورة النحل: 96"},
    {"text": "(( خيركم من تعلم القرآن وعلمه ))", "source": "رواه البخاري"},
    {"text": "﴿ رَبِّ إِنِّي لِمَا أَنزَلْتَ إِلَيَّ مِنْ خَيْرٍ فَقِيرٌ ﴾", "source": "سورة القصص: 24"},
    {"text": "(( لا تحقرن من المعروف شيئاً ولو أن تلقى أخاك بوجه طلق ))", "source": "رواه مسلم"},
    {"text": "﴿ وَتَزَوَّدُوا فَإِنَّ خَيْرَ الزَّادِ التَّقْوَىٰ ﴾", "source": "سورة البقرة: 197"}
]
daily_quote_data = random.choice(MOTIVATIONAL_QUOTES)

# ==========================================
# 🔑 إعدادات المجموعات (تم إضافة مجموعة الفجر)
# ==========================================
GROUPS_CONFIG = {
    "مجموعة الفردوس": "Firdaws@786!Top",
    "مجموعة الريان": "Rayyan#2025$Win",
    "مجموعة الفجر": "Fajr@Simple22",  # المجموعة المبسطة الجديدة
    "الإدارة": "Admin@MasterKey99!"
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
    "قيام", "القرآن", "الصيام", "قراءة_كتاب", "أسرة", "مجلس التدارس", "التعهد",
    "جمعة_كهف", "جمعة_صلاة_نبي"
]

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
    sheet_data = sh.get_worksheet(0)
except Exception as e:
    st.error(f"خطأ في فتح الملف: {e}")
    st.stop()

# ==========================================
# 🔒 تسجيل الدخول
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def check_login():
    input_user = st.session_state.login_user.strip()
    input_pass = st.session_state.login_pass.strip()
    
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
        st.error("⛔ الاسم أو كلمة المرور غير صحيحة")

if not st.session_state["authenticated"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background-color: white; padding: 40px; border-radius: 20px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
            <h1 style="color: #009688; margin-bottom: 10px;">🕌 سباق الصالحين</h1>
            <p style="color: #666; font-size: 1.1rem;">منصة التنافس الأخوي في الطاعات</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.text_input("👤 الاسم الكريم:", key="login_user")
        st.text_input("🔑 رمز المجموعة:", type="password", key="login_pass")
        st.button("🚀 دخول للسباق", on_click=check_login, use_container_width=True)
    st.stop()

# ==========================================
# 🧮 حساب النقاط
# ==========================================
def safe_str(val):
    return str(val).strip() if val else ""

def calculate_score(row):
    score = 0
    
    # 1. الصلوات
    prayers_map = {'الفجر': 'الفجر_حالة', 'الظهر': 'الظهر_حالة', 'العصر': 'العصر_حالة', 'المغرب': 'المغرب_حالة', 'العشاء': 'العشاء_حالة'}
    for p_name, col_name in prayers_map.items():
        status = safe_str(row.get(col_name))
        if status == 'جماعة (مسجد)': score += 10
        elif status == 'في الوقت (بيت)': score += 6
        
        if p_name != 'العصر':
            if safe_str(row.get(f"{p_name}_سنة")) == 'نعم': score += 3
            
    if safe_str(row.get('الضحى')) == 'نعم': score += 5
    
    # 2. الأذكار
    chk_list = ['أذكار_الصباح', 'أذكار_المساء', 'أذكار_الصلاة', 'أذكار_النوم']
    for chk in chk_list:
        if safe_str(row.get(chk)) == 'نعم': score += 3
    if safe_str(row.get('سورة_الملك')) == 'نعم': score += 5
    
    # 3. القرآن
    quran_val = safe_str(row.get('القرآن'))
    quran_points = {
        "ثمن": 2, 
        "ربع": 4, 
        "نصف": 6, 
        "حزب": 8, 
        "حزبين": 10
    }
    score += quran_points.get(quran_val, 0)
    
    # 4. قيام الليل
    qiyam_val = safe_str(row.get('قيام'))
    qiyam_points = {
        "ركعتان": 3, 
        "4 ركعات": 5, 
        "6 ركعات": 7, 
        "8 ركعات": 10
    }
    score += qiyam_points.get(qiyam_val, 0)

    # 5. أعمال البر
    good_deeds = ['الصيام', 'قراءة_كتاب', 'أسرة', 'مجلس التدارس', 'التعهد']
    points_deed = {
        'الصيام': 10, 
        'قراءة_كتاب': 4, 
        'أسرة': 4, 
        'مجلس التدارس': 4, 
        'التعهد': 4
    }
    for deed in good_deeds:
        if safe_str(row.get(deed)) == 'نعم': score += points_deed[deed]

    # 6. الجمعة
    if safe_str(row.get('جمعة_كهف')) == 'نعم': score += 15
    if safe_str(row.get('جمعة_صلاة_نبي')) == 'نعم': score += 15
    
    return min(score, 145)

def get_level_and_rank(total_points):
    level = 1 + (int(total_points) // 500)
    if level < 5: title = "مبتدئ (🌱)"
    elif level < 10: title = "مجتهد (💪)"
    elif level < 20: title = "سابق (🚀)"
    else: title = "رباني (👑)"
    return level, title

# ==========================================
# 📊 معالجة البيانات
# ==========================================
current_user = st.session_state["user_name"]
current_group = st.session_state["user_group"]

try:
    data = sheet_data.get_all_records()
    full_df = pd.DataFrame(data)
except:
    full_df = pd.DataFrame()

my_total_xp = 0
my_level = 1
my_rank = "-"
group_df = pd.DataFrame() 

# --- التحقق والإصلاح التلقائي ---
if not full_df.empty:
    missing_cols = [c for c in EXPECTED_HEADERS if c not in full_df.columns]
    
    if missing_cols:
        st.warning("⚠️ **تنبيه:** هيكل الملف غير متطابق مع التحديث الأخير.")
        st.caption(f"الأعمدة الناقصة: {missing_cols}")
        
        if st.button("🔧 إصلاح الملف تلقائياً"):
            try:
                with st.spinner("جاري تحديث الأعمدة..."):
                    sheet_data.update('A1', [EXPECTED_HEADERS])
                    st.success("✅ تم الإصلاح بنجاح! جاري إعادة التحميل...")
                    time.sleep(2)
                    st.rerun()
            except Exception as e:
                st.error(f"حدث خطأ: {e}")
        st.stop()
    else:
        full_df['Score'] = full_df.apply(calculate_score, axis=1)
        full_df['DateObj'] = pd.to_datetime(full_df['التاريخ'], errors='coerce')
        
        if current_group == "الإدارة":
            group_df = full_df.copy()
        else:
            group_df = full_df[full_df['المجموعة'] == current_group].copy()

        if not group_df.empty:
            temp_leaderboard = group_df.groupby('الاسم')['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
            temp_leaderboard.insert(0, 'الترتيب', temp_leaderboard.index + 1)
            
            my_stats = temp_leaderboard[temp_leaderboard['الاسم'] == current_user]
            if not my_stats.empty:
                my_total_xp = my_stats.iloc[0]['Score']
                my_level = 1 + (int(my_total_xp) // 500)
                my_rank = my_stats.iloc[0]['الترتيب']

# ==========================================
# 🖥️ الواجهة الرئيسية
# ==========================================

col_h1, col_h2 = st.columns([6, 1])
with col_h1:
    st.markdown(f"### 🚩 {current_group}")
    st.markdown(f"**أهلاً بك يا {current_user}**")
with col_h2:
    if st.button("خروج", key="logout"):
        st.session_state["authenticated"] = False
        st.rerun()

# الاقتباس اليومي
st.markdown(f"""
<div class="quote-box">
    <div class="quote-text">{daily_quote_data['text']}</div>
    <div class="quote-source">{daily_quote_data['source']}</div>
</div>
""", unsafe_allow_html=True)

# KPIs
kpi1, kpi2, kpi3 = st.columns(3)
with kpi1: st.markdown(f"""<div class="metric-card"><h3>🥇 الترتيب</h3><h1>#{my_rank}</h1></div>""", unsafe_allow_html=True)
with kpi2: st.markdown(f"""<div class="metric-card"><h3>🛡️ المستوى</h3><h1>{my_level}</h1></div>""", unsafe_allow_html=True)
with kpi3: st.markdown(f"""<div class="metric-card"><h3>✨ النقاط</h3><h1>{my_total_xp}</h1></div>""", unsafe_allow_html=True)

points_next = (my_level * 500) - my_total_xp
progress_val = max(0.0, min(1.0, 1 - (points_next / 500)))
st.markdown(f"<p style='text-align:center; margin-top:10px; color:#666;'>🚀 باقي <b>{points_next}</b> نقطة للمستوى القادم</p>", unsafe_allow_html=True)
st.progress(progress_val)

st.markdown("<br>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["📝 تسجيل اليوم", "🏆 لوحة الصدارة", "📈 تطور مستواي"])

# ==========================================
# TAB 1 : التسجيل
# ==========================================
with tab1:
    st.markdown("### 🤲 تسجيل إنجاز اليوم")
    
    is_friday = datetime.today().weekday() == 4
    if is_friday:
        st.success("🕌 **يوم الجمعة!** لا تنسَ سورة الكهف والصلاة على النبي.")

    with st.form("entry_form"):
        # تهيئة القيم الافتراضية للخانة المخفية لتجنب الأخطاء
        inputs = {}
        inputs['fasting'] = False
        inputs['book_read'] = False
        inputs['family'] = False
        inputs['majlis_tadarus'] = False
        inputs['taahod'] = False

        # الصلوات (يظهر للجميع)
        with st.expander("🕌 الصلوات المفروضة", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.caption("🌌 **الفجر**")
                inputs['fs'] = st.selectbox("الفجر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="fs", label_visibility="collapsed")
                inputs['fsn'] = st.checkbox("السنة", key="fsn")
            with c2:
                st.caption("☀️ **الظهر**")
                inputs['ds'] = st.selectbox("الظهر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="ds", label_visibility="collapsed")
                inputs['dsn'] = st.checkbox("السنة", key="dsn")
            with c3:
                st.caption("🌤️ **العصر**")
                inputs['as'] = st.selectbox("العصر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="as", label_visibility="collapsed")
            
            st.markdown("---")
            c4, c5, c6 = st.columns(3)
            with c4:
                st.caption("🌅 **المغرب**")
                inputs['ms'] = st.selectbox("المغرب", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="ms", label_visibility="collapsed")
                inputs['msn'] = st.checkbox("السنة", key="msn")
            with c5:
                st.caption("🌃 **العشاء**")
                inputs['is_val'] = st.selectbox("العشاء", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="is_val", label_visibility="collapsed")
                inputs['isn'] = st.checkbox("السنة", key="isn")
            with c6:
                st.caption("☀️ **الضحى**")
                st.markdown("<br>", unsafe_allow_html=True)
                inputs['duha'] = st.checkbox("صلاة الضحى", key="duha")

        # الروحانيات (يظهر للجميع)
        with st.expander("📖 الروحانيات (القرآن والقيام)", expanded=False):
            col_z1, col_z2 = st.columns(2)
            with col_z1:
                st.markdown("**📿 الأذكار**")
                inputs['az_m'] = st.checkbox("الصباح")
                inputs['az_e'] = st.checkbox("المساء")
                inputs['az_p'] = st.checkbox("دبر الصلاة")
                inputs['az_s'] = st.checkbox("النوم")
                inputs['mulk'] = st.checkbox("سورة الملك")
            with col_z2:
                st.markdown("**🌙 القرآن والقيام**")
                inputs['qiyam'] = st.selectbox("قيام الليل", options=["0", "ركعتان", "4 ركعات", "6 ركعات", "8 ركعات"])
                inputs['quran'] = st.selectbox("الورد القرآني", options=["0", "ثمن", "ربع", "نصف", "حزب", "حزبين"])
                
                if is_friday:
                    st.markdown("---")
                    cf1, cf2 = st.columns(2)
                    kahf = cf1.checkbox("سورة الكهف")
                    salat_nabi = cf2.checkbox("الصلاة على النبي")
                else:
                    kahf = False; salat_nabi = False

        # أعمال البر (⚠️ يظهر فقط إذا لم يكن من مجموعة الفجر)
        if current_group != "مجموعة الفجر":
            with st.expander("🌱 أعمال البر", expanded=False):
                b1, b2, b3, b4, b5 = st.columns(5)
                inputs['fasting'] = b1.checkbox("صيام تطوع")
                inputs['book_read'] = b2.checkbox("قراءة كتاب")
                inputs['family'] = b3.checkbox("بر الأسرة")
                inputs['majlis_tadarus'] = b4.checkbox("مجلس تدارس")
                inputs['taahod'] = b5.checkbox("التعهد")

        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.form_submit_button("✅ حفظ البيانات", use_container_width=True)

        if submit:
            day_date = datetime.now().strftime("%Y-%m-%d")
            
            # التحقق من التكرار
            is_duplicate = False
            if not full_df.empty:
                user_df = full_df[full_df['الاسم'] == current_user]
                if day_date in user_df['التاريخ'].astype(str).values:
                    is_duplicate = True
            
            if is_duplicate:
                st.error(f"⛔ لقد قمت بتسجيل بيانات يوم {day_date} مسبقاً.")
            else:
                row = [
                    day_date, current_user, current_group,
                    inputs['fs'], "نعم" if inputs['fsn'] else "لا", "نعم" if inputs['duha'] else "لا",
                    inputs['ds'], "نعم" if inputs['dsn'] else "لا",
                    inputs['as'],
                    inputs['ms'], "نعم" if inputs['msn'] else "لا",
                    inputs['is_val'], "نعم" if inputs['isn'] else "لا",
                    "نعم" if inputs['az_m'] else "لا", "نعم" if inputs['az_e'] else "لا", 
                    "نعم" if inputs['az_p'] else "لا", "نعم" if inputs['az_s'] else "لا", 
                    "نعم" if inputs['mulk'] else "لا",
                    inputs['qiyam'], 
                    inputs['quran'], 
                    "نعم" if inputs['fasting'] else "لا", 
                    "نعم" if inputs['book_read'] else "لا",
                    "نعم" if inputs['family'] else "لا", 
                    "نعم" if inputs['majlis_tadarus'] else "لا",
                    "نعم" if inputs['taahod'] else "لا",
                    "نعم" if kahf else "لا", "نعم" if salat_nabi else "لا"
                ]
                
                try:
                    with st.spinner("جاري الحفظ..."):
                        sheet_data.append_row(row)
                        st.balloons()
                        st.success("✅ تم الحفظ بنجاح! تقبل الله طاعتك.")
                        time.sleep(2)
                        st.rerun()
                except Exception as e:
                    st.error(f"حدث خطأ تقني: {e}")

# ==========================================
# TAB 2 : الصدارة
# ==========================================
with tab2:
    st.markdown("### 📊 لوحة الصدارة")
    
    target_group = current_group
    if current_group == "الإدارة":
        target_group = st.selectbox("🔍 عرض مجموعة:", ["مجموعة الفردوس", "مجموعة الريان", "مجموعة الفجر"])
    
    if not full_df.empty:
        display_df = full_df[full_df['المجموعة'] == target_group].copy()
    else:
        display_df = pd.DataFrame()

    t2_1, t2_2 = st.tabs(["🥇 الترتيب العام", "📅 الترتيب الأسبوعي"])
    
    with t2_1:
        if not display_df.empty and 'Score' in display_df.columns:
            gen_board = display_df.groupby('الاسم')['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
            gen_board['المستوى'] = gen_board['Score'].apply(lambda x: get_level_and_rank(x)[0])
            gen_board['اللقب'] = gen_board['Score'].apply(lambda x: get_level_and_rank(x)[1])
            gen_board.insert(0, 'الترتيب', gen_board.index + 1)
            
            st.dataframe(gen_board[['الترتيب', 'الاسم', 'المستوى', 'Score', 'اللقب']], use_container_width=True, hide_index=True)
        else:
            st.info("لا توجد بيانات متاحة.")

    with t2_2:
        if not display_df.empty and 'Score' in display_df.columns:
            curr_wk = datetime.now().isocalendar()[1]
            curr_yr = datetime.now().year
            
            wk_df = display_df[
                (display_df['DateObj'].dt.isocalendar().week == curr_wk) & 
                (display_df['DateObj'].dt.year == curr_yr)
            ]
            
            if not wk_df.empty:
                wk_board = wk_df.groupby('الاسم')['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
                wk_board.insert(0, 'الترتيب', wk_board.index + 1)
                
                top_name = wk_board.iloc[0]['الاسم']
                top_score = wk_board.iloc[0]['Score']
                st.success(f"🏆 بطل الأسبوع: **{top_name}** ({top_score} نقطة)")
                
                st.dataframe(wk_board[['الترتيب', 'الاسم', 'Score']], use_container_width=True, hide_index=True)
            else:
                st.info("لم يبدأ السباق الأسبوعي بعد.")
        else:
            st.info("لا توجد بيانات.")

# ==========================================
# TAB 3 : التاريخ
# ==========================================
with tab3:
    st.markdown("### 📈 تطور مستواي")
    if not full_df.empty and current_user in full_df['الاسم'].values and 'Score' in full_df.columns:
        my_hist = full_df[full_df['الاسم'] == current_user].copy()
        
        my_hist = my_hist.dropna(subset=['DateObj']).sort_values(by='DateObj')
        my_hist.set_index('DateObj', inplace=True)
        
        st.caption("رسم بياني يوضح نقاطك اليومية")
        st.line_chart(my_hist['Score'])
        
        st.markdown("#### سجل البيانات")
        st.dataframe(my_hist.drop(columns=['Score'], errors='ignore').reset_index(drop=True), use_container_width=True)
    else:
        st.info("لا يوجد سجل سابق.")
