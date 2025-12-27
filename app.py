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
# 🎨 التصميم (CSS - عربي)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
    }
    
    .stApp {
        background-image: radial-gradient(var(--primary-color) 0.5px, transparent 0.5px);
        background-size: 20px 20px;
    }

    .custom-container {
        background-color: var(--secondary-background-color);
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border: 1px solid rgba(128, 128, 128, 0.2);
        text-align: center;
        margin-bottom: 20px;
    }

    .stButton>button {
        background: linear-gradient(45deg, #009688, #4DB6AC);
        color: white !important;
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
        background-color: var(--secondary-background-color);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid var(--primary-color);
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .metric-card h1 { margin: 0; color: var(--primary-color); }
    .metric-card h3 { margin: 0; font-size: 1rem; opacity: 0.8; }

    /* تنسيق النصوص */
    h1, h2, h3, h4, p, label, .stMarkdown { color: var(--text-color) !important; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔑 إعدادات المجموعات (كلمات مرور قوية)
# ==========================================
GROUPS_CONFIG = {
    "مجموعة الفردوس": "Firdaws@786!Top",
    "مجموعة الريان": "Rayyan#2025$Win",
    "الإدارة": "Admin@MasterKey99!"
}

# ==========================================
# 📋 عناوين الأعمدة
# ==========================================
# ⚠️ يجب أن تتطابق هذه الأسماء تماماً مع الصف الأول في Google Sheet
EXPECTED_HEADERS = [
    "التاريخ", "الاسم", "المجموعة",
    "الفجر_حالة", "الفجر_سنة", "الضحى", 
    "الظهر_حالة", "الظهر_سنة",
    "العصر_حالة",
    "المغرب_حالة", "المغرب_سنة",
    "العشاء_حالة", "العشاء_سنة",
    "أذكار_الصباح", "أذكار_المساء", "أذكار_الصلاة", 
    "أذكار_النوم", "سورة_الملك",
    "قيام", "القرآن", "الصيام", "قراءة_كتاب", "أسرة", "قراءة", "التعهد",
    "جمعة_كهف", "جمعة_صلاة_نبي"
]

# ==========================================
# 💎 اقتباسات
# ==========================================
MOTIVATIONAL_QUOTES = [
    "أَحَبُّ الأعمالِ إلى اللهِ أدْومُها وإنْ قَلَّ",
    "وَفِي ذَٰلِكَ فَلْيَتَنَافَسِ الْمُتَنَافِسُونَ",
    "الدال على الخير كفاعله",
    "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ",
    "إِنَّمَا الأَعْمَالُ بِالنِّيَّاتِ"
]
daily_quote = random.choice(MOTIVATIONAL_QUOTES)

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
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="custom-container">
            <h1 style="color: #009688;">🕌 سباق الصالحين</h1>
            <p>منصة التنافس الأخوي في الطاعات</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("👋 مرحباً بك! أدخل اسمك وكلمة مرور المجموعة")
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
    # الصلوات
    prayers_map = {'الفجر': 'الفجر_حالة', 'الظهر': 'الظهر_حالة', 'العصر': 'العصر_حالة', 'المغرب': 'المغرب_حالة', 'العشاء': 'العشاء_حالة'}
    
    for p_name, col_name in prayers_map.items():
        status = safe_str(row.get(col_name))
        if status == 'جماعة (مسجد)': score += 10
        elif status == 'في الوقت (بيت)': score += 6
        
        if p_name != 'العصر':
            if safe_str(row.get(f"{p_name}_سنة")) == 'نعم': score += 3
            
    if safe_str(row.get('الضحى')) == 'نعم': score += 5
    
    # الأذكار
    chk_list = ['أذكار_الصباح', 'أذكار_المساء', 'أذكار_الصلاة', 'أذكار_النوم']
    for chk in chk_list:
        if safe_str(row.get(chk)) == 'نعم': score += 3
        
    if safe_str(row.get('سورة_الملك')) == 'نعم': score += 5
    
    # القرآن
    quran_val = safe_str(row.get('القرآن'))
    quran_points = {"ثمن": 2, "ربع": 4, "نصف": 6, "حزب": 8, "حزبين": 10}
    score += quran_points.get(quran_val, 0)
    
    # قيام الليل
    qiyam_val = safe_str(row.get('قيام'))
    qiyam_points = {"ركعتان": 3, "٤ ركعات": 5, "٦ ركعات": 7, "٨ ركعات": 10}
    score += qiyam_points.get(qiyam_val, 0)

    # أعمال البر
    good_deeds = ['الصيام', 'قراءة_كتاب', 'أسرة', 'قراءة', 'التعهد']
    points_deed = {'الصيام': 10, 'قراءة_كتاب': 4, 'أسرة': 4, 'قراءة': 4, 'التعهد': 4}
    
    for deed in good_deeds:
        if safe_str(row.get(deed)) == 'نعم': score += points_deed[deed]

    # الجمعة
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

# ⚠️ نظام حماية لمنع الخطأ عند عدم تطابق الأعمدة
missing_cols = []
if not full_df.empty:
    missing_cols = [c for c in EXPECTED_HEADERS if c not in full_df.columns]
    
    if missing_cols:
        st.error(f"⚠️ **خطأ في قاعدة البيانات:** يرجى تحديث أسماء الأعمدة في ملف Google Sheet لتطابق الكود.")
        st.error(f"الأعمدة المفقودة أو التي تغير اسمها: {missing_cols}")
        st.info("💡 الحل: اذهب لملف الإكسل وغير 'مجلس' إلى 'قراءة_كتاب' و 'زيارة' إلى 'التعهد'.")
        st.stop() # يوقف التطبيق بأمان بدلاً من الانهيار
    else:
        # إذا كانت الأعمدة صحيحة، نكمل الحسابات
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
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.markdown(f"## 🏆 {current_group}")
    st.markdown(f"مرحباً بالمجتهد **{current_user}**")
with col_head2:
    if st.button("🚪 خروج", key="logout_btn"):
        st.session_state["authenticated"] = False
        st.rerun()

# البطاقات
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f"""<div class="metric-card"><h3>🥇 الترتيب</h3><h1>#{my_rank}</h1></div>""", unsafe_allow_html=True)
with c2: st.markdown(f"""<div class="metric-card"><h3>🛡️ المستوى</h3><h1>{my_level}</h1></div>""", unsafe_allow_html=True)
with c3: st.markdown(f"""<div class="metric-card"><h3>✨ نقاطي</h3><h1>{my_total_xp}</h1></div>""", unsafe_allow_html=True)

# شريط التقدم
points_next_level = (my_level * 500) - my_total_xp
progress = max(0.0, min(1.0, 1 - (points_next_level / 500)))
st.markdown("<br>", unsafe_allow_html=True)
st.progress(progress, text=f"🚀 باقي {points_next_level} نقطة للمستوى القادم")

# التبويبات
tab1, tab2, tab3 = st.tabs(["📝 تسجيل اليوم", "🏆 لوحة الصدارة", "📊 سجلي السابق"])

# --- تبويب 1: التسجيل ---
with tab1:
    st.markdown("### 🤲 تسجيل إنجاز اليوم")
    is_friday = datetime.today().weekday() == 4
    if is_friday: st.success("🕌 اليوم الجمعة! لا تنسَ سورة الكهف والصلاة على النبي.")
    
    with st.form("entry_form"):
        if is_friday:
            col_f1, col_f2 = st.columns(2)
            kahf = col_f1.checkbox("📖 قراءة الكهف")
            salat_nabi = col_f2.checkbox("📿 الصلاة على النبي")
            st.markdown("---")
        else:
            kahf = False; salat_nabi = False

        # الصلوات
        st.markdown("##### 🕌 الصلوات المفروضة")
        cols = st.columns(3)
        inputs = {}
        
        with cols[0]:
            st.markdown("**الفجر**")
            inputs['fs'] = st.selectbox("الحالة", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="fs", label_visibility="collapsed")
            inputs['fsn'] = st.checkbox("السنة", key="fsn")
        with cols[1]:
            st.markdown("**الظهر**")
            inputs['ds'] = st.selectbox("الحالة", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="ds", label_visibility="collapsed")
            inputs['dsn'] = st.checkbox("السنة", key="dsn")
        with cols[2]:
            st.markdown("**العصر**")
            inputs['as'] = st.selectbox("الحالة", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="as", label_visibility="collapsed")
            
        st.markdown("<br>", unsafe_allow_html=True)
        cols2 = st.columns(3)
        with cols2[0]:
            st.markdown("**المغرب**")
            inputs['ms'] = st.selectbox("الحالة", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="ms", label_visibility="collapsed")
            inputs['msn'] = st.checkbox("السنة", key="msn")
        with cols2[1]:
            st.markdown("**العشاء**")
            inputs['is_val'] = st.selectbox("الحالة", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="is_val", label_visibility="collapsed")
            inputs['isn'] = st.checkbox("السنة", key="isn")
        with cols2[2]:
            st.markdown("**☀️ الضحى**")
            inputs['duha'] = st.checkbox("صلاة الضحى", key="duha")

        st.markdown("---")
        
        # الأذكار والقرآن
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 📿 الأذكار")
            inputs['az_m'] = st.checkbox("الصباح")
            inputs['az_e'] = st.checkbox("المساء")
            inputs['az_p'] = st.checkbox("بعد الصلاة")
            inputs['az_s'] = st.checkbox("قبل النوم")
            inputs['mulk'] = st.checkbox("سورة الملك")
            
        with c2:
            st.markdown("##### 📖 القرآن والقيام")
            inputs['qiyam'] = st.selectbox("🌙 قيام الليل", ["0", "ركعتان", "٤ ركعات", "٦ ركعات", "٨ ركعات"])
            inputs['quran'] = st.selectbox("📖 الورد القرآني", ["0", "ثمن", "ربع", "نصف", "حزب", "حزبين"])

        st.markdown("---")
        st.markdown("##### 🌱 أعمال البر")
        cc1, cc2, cc3, cc4, cc5 = st.columns(5)
        inputs['fasting'] = cc1.checkbox("صيام تطوع")
        # ⚠️ قراءة كتاب
        inputs['book_read'] = cc2.checkbox("قراءة كتاب")
        inputs['family'] = cc3.checkbox("بر الأسرة")
        inputs['read'] = cc4.checkbox("قراءة نافعة")
        # ⚠️ التعهد
        inputs['taahod'] = cc5.checkbox("التعهد")

        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.form_submit_button("✅ حفظ البيانات", use_container_width=True)

        if submit:
            day_date = datetime.now().strftime("%Y-%m-%d")
            
            is_duplicate = False
            if not full_df.empty:
                user_df = full_df[full_df['الاسم'] == current_user]
                if day_date in user_df['التاريخ'].astype(str).values:
                    is_duplicate = True
            
            if is_duplicate:
                st.error(f"⛔ لقد قمت بتسجيل بيانات يوم {day_date} مسبقاً")
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
                    inputs['qiyam'], inputs['quran'], 
                    "نعم" if inputs['fasting'] else "لا", 
                    "نعم" if inputs['book_read'] else "لا", # قراءة كتاب
                    "نعم" if inputs['family'] else "لا", "نعم" if inputs['read'] else "لا", 
                    "نعم" if inputs['taahod'] else "لا", # التعهد
                    "نعم" if kahf else "لا", "نعم" if salat_nabi else "لا"
                ]
                
                try:
                    with st.spinner("جاري الحفظ..."):
                        sheet_data.append_row(row)
                        st.balloons()
                        st.success("تم الحفظ بنجاح! تقبل الله طاعتك")
                        time.sleep(2)
                        st.rerun()
                except Exception as e:
                    st.error(f"حدث خطأ: {e}")

# --- تبويب 2: الصدارة ---
with tab2:
    st.markdown("### 📊 لوحة الصدارة")
    
    # اختيار المجموعة للإدمن
    target_group = current_group
    if current_group == "الإدارة":
        target_group = st.selectbox("🔍 عرض مجموعة:", ["مجموعة الفردوس", "مجموعة الريان"])
    
    # فلترة البيانات
    if not full_df.empty:
        display_df = full_df[full_df['المجموعة'] == target_group].copy()
    else:
        display_df = pd.DataFrame()

    t2_1, t2_2 = st.tabs(["🥇 الترتيب العام", "📅 الترتيب الأسبوعي"])
    
    # 1. الترتيب العام
    with t2_1:
        if not display_df.empty and 'Score' in display_df.columns:
            gen_leaderboard = display_df.groupby('الاسم')['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
            gen_leaderboard['المستوى'] = gen_leaderboard['Score'].apply(lambda x: get_level_and_rank(x)[0])
            gen_leaderboard['اللقب'] = gen_leaderboard['Score'].apply(lambda x: get_level_and_rank(x)[1])
            gen_leaderboard.insert(0, 'الترتيب', gen_leaderboard.index + 1)
            
            st.dataframe(
                gen_leaderboard[['الترتيب', 'الاسم', 'المستوى', 'Score', 'اللقب']], 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("لا توجد بيانات لهذه المجموعة (أو لم يتم حساب النقاط).")

    # 2. الترتيب الأسبوعي
    with t2_2:
        if not display_df.empty and 'Score' in display_df.columns:
            curr_wk = datetime.now().isocalendar()[1]
            curr_yr = datetime.now().year
            
            weekly_df = display_df[
                (display_df['DateObj'].dt.isocalendar().week == curr_wk) & 
                (display_df['DateObj'].dt.year == curr_yr)
            ]
            
            if not weekly_df.empty:
                wk_leaderboard = weekly_df.groupby('الاسم')['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
                wk_leaderboard.insert(0, 'الترتيب', wk_leaderboard.index + 1)
                
                champion = wk_leaderboard.iloc[0]['الاسم']
                score_ch = wk_leaderboard.iloc[0]['Score']
                st.success(f"🏆 بطل الأسبوع: **{champion}** ({score_ch} نقطة)")
                
                st.dataframe(
                    wk_leaderboard[['الترتيب', 'الاسم', 'Score']], 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info("لا توجد بيانات لهذا الأسبوع.")
        else:
            st.info("لا توجد بيانات.")

# --- تبويب 3: السجل (رسم بياني زمني) ---
with tab3:
    st.markdown("### 📈 سجلي البياني")
    if not full_df.empty and current_user in full_df['الاسم'].values and 'Score' in full_df.columns:
        my_hist = full_df[full_df['الاسم'] == current_user].copy()
        
        # التأكد من صحة التواريخ والترتيب
        my_hist['DateObj'] = pd.to_datetime(my_hist['التاريخ'], errors='coerce')
        my_hist = my_hist.dropna(subset=['DateObj']) # حذف التواريخ الخاطئة
        my_hist = my_hist.sort_values(by='DateObj') # الترتيب زمنياً
        
        # تهيئة الفهرس للرسم
        my_hist.set_index('DateObj', inplace=True)
        
        st.write("#### تطور النقاط عبر الأيام")
        st.line_chart(my_hist['Score'])
        
        st.write("#### السجل التفصيلي")
        st.dataframe(my_hist.drop(columns=['Score'], errors='ignore').reset_index(drop=True), use_container_width=True)
    else:
        st.info("لا يوجد سجل سابق.")
