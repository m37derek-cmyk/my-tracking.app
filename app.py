import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import os
import random
import time 

# --- إعدادات الصفحة ---
st.set_page_config(page_title="سباق الصالحين", layout="wide", page_icon="🕌")

# ==========================================
# 🔑 كلمة المرور
# ==========================================
MY_PASSWORD = "Taqwa@2025@Secret!"

# ==========================================
# 📋 عناوين الأعمدة (HEADERS) - النظام الجديد
# ==========================================
# هذه القائمة هي المرجع الأساسي لترتيب الأعمدة في ملف الإكسل
EXPECTED_HEADERS = [
    "التاريخ", "الاسم",
    "الفجر_حالة", "الفجر_سنة",
    "الظهر_حالة", "الظهر_سنة",
    "العصر_حالة",
    "المغرب_حالة", "المغرب_سنة",
    "العشاء_حالة", "العشاء_سنة",
    "أذكار_الصباح", "أذكار_المساء", "أذكار_الصلاة",
    "قيام", "القرآن", "الصيام", "مجلس", "أسرة", "قراءة", "زيارة"
]

# ==========================================
# 💎 مكتبة التحفيز
# ==========================================
MOTIVATIONAL_QUOTES = [
    {"text": "وَسَارِعُوا إِلَىٰ مَغْفِرَةٍ مِّن رَّبِّكُمْ", "source": "آل عمران: 133"},
    {"text": "فَاسْتَبِقُوا الْخَيْرَاتِ", "source": "البقرة: 148"},
    {"text": "أحب الأعمال إلى الله أدومها وإن قل", "source": "حديث شريف"},
    {"text": "الدال على الخير كفاعله", "source": "حديث شريف"},
    {"text": "من صلى البردين دخل الجنة", "source": "حديث شريف"},
    {"text": "ركعتا الفجر خير من الدنيا وما فيها", "source": "حديث شريف"}
]
daily_quote = random.choice(MOTIVATIONAL_QUOTES)

# ==========================================
# 💡 مقترحات بطل الأسبوع
# ==========================================
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
    
    # 🔥🔥🔥 التصحيح التلقائي لملف الإكسل (جديد) 🔥🔥🔥
    # هذا الكود يفحص السطر الأول، إذا كان فارغاً أو خطأ، يقوم بإصلاحه فوراً
    try:
        current_headers = sheet_data.row_values(1)
        if not current_headers or current_headers != EXPECTED_HEADERS:
            # إذا كانت العناوين مختلفة، قم بتحديث السطر الأول فقط
            # تنبيه: هذا لا يمسح البيانات القديمة، فقط يصحح العناوين
            sheet_data.delete_rows(1)
            sheet_data.insert_row(EXPECTED_HEADERS, 1)
            st.toast("✅ تم تحديث هيكل قاعدة البيانات تلقائياً!", icon="🛠️")
    except Exception as e:
        st.warning(f"ملاحظة: لم نتمكن من التحقق من العناوين: {e}")

except Exception as e:
    st.error(f"خطأ في فتح الملف: {e}")
    st.stop()

# ==========================================
# 🔒 نظام تسجيل الدخول
# ==========================================
def check_login():
    input_user = st.session_state["login_user"].strip()
    input_pass = st.session_state["login_pass"].strip()
    if input_pass == MY_PASSWORD and input_user:
        st.session_state["authenticated"] = True
        st.session_state["user_name"] = input_user
    else:
        st.session_state["authenticated"] = False
        st.error("⛔ كلمة المرور غير صحيحة.")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<br><br><h2 style='text-align: center;'>🔒 تسجيل الدخول</h2>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: st.text_input("الاسم الكريم:", key="login_user")
    with c2: st.text_input("كلمة المرور:", type="password", key="login_pass")
    st.button("دخول", on_click=check_login, use_container_width=True)
    st.stop()

# ==========================================
# 🧮 محرك الحسابات
# ==========================================
def calculate_score(row):
    score = 0
    # استخدام أسماء الأعمدة الجديدة للبحث في البيانات
    # ملاحظة: pandas تستخدم أسماء الأعمدة كما هي في EXPECTED_HEADERS
    
    # 1. الصلوات
    prayers_map = {
        'الفجر': 'الفجر_حالة', 'الظهر': 'الظهر_حالة', 
        'العصر': 'العصر_حالة', 'المغرب': 'المغرب_حالة', 'العشاء': 'العشاء_حالة'
    }
    
    for p_name, col_name in prayers_map.items():
        status = row.get(col_name)
        if status == 'جماعة (مسجد)': score += 10
        elif status == 'في الوقت (بيت)': score += 6
        
        # السنن (ماعدا العصر)
        if p_name != 'العصر':
            sunnah_col = f"{p_name}_سنة"
            if row.get(sunnah_col) == 'نعم': score += 3

    # 2. الأذكار
    if row.get('أذكار_الصباح') == 'نعم': score += 3
    if row.get('أذكار_المساء') == 'نعم': score += 3
    if row.get('أذكار_الصلاة') == 'نعم': score += 3

    # 3. الباقي
    if str(row.get('قيام')) not in ["0", "لا", "", "None"]: score += 8
    if str(row.get('القرآن')) not in ["0", "لا", "", "None"]: score += 8
    
    if row.get('الصيام') == 'نعم': score += 10
    if row.get('مجلس') == 'نعم': score += 4
    if row.get('أسرة') == 'نعم': score += 4
    if row.get('قراءة') == 'نعم': score += 4
    if row.get('زيارة') == 'نعم': score += 4
    
    return min(score, 100)

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
    # التأكد من وجود الأعمدة المطلوبة لتجنب الأخطاء
    missing_cols = [c for c in EXPECTED_HEADERS if c not in full_df.columns]
    if not missing_cols:
        full_df['Score'] = full_df.apply(calculate_score, axis=1)
        full_df['DateObj'] = pd.to_datetime(full_df['التاريخ'], errors='coerce')
        
        # الترتيب العام
        leaderboard = full_df.groupby('الاسم')['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
        leaderboard['المستوى'] = leaderboard['Score'].apply(lambda x: get_level_and_rank(x)[0])
        leaderboard['اللقب'] = leaderboard['Score'].apply(lambda x: get_level_and_rank(x)[1])
        leaderboard.insert(0, 'الترتيب', leaderboard.index + 1)

        my_stats = leaderboard[leaderboard['الاسم'] == current_user]
        if not my_stats.empty:
            my_total_xp = my_stats.iloc[0]['Score']
            my_level = my_stats.iloc[0]['المستوى']
            my_rank = my_stats.iloc[0]['الترتيب']

        # الأسبوعي
        curr_wk = datetime.now().isocalendar()[1]
        curr_yr = datetime.now().year
        weekly_df = full_df[(full_df['DateObj'].dt.isocalendar().week == curr_wk) & (full_df['DateObj'].dt.year == curr_yr)]
        if not weekly_df.empty:
            weekly_leaderboard = weekly_df.groupby('الاسم')['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
            weekly_leaderboard.insert(0, 'الترتيب', weekly_leaderboard.index + 1)
            if not weekly_leaderboard.empty:
                weekly_champion_name = weekly_leaderboard.iloc[0]['الاسم']
                weekly_champion_score = weekly_leaderboard.iloc[0]['Score']

        # اليومي
        today_str = datetime.now().strftime("%Y-%m-%d")
        daily_df = full_df[full_df['التاريخ'] == today_str]
        if not daily_df.empty:
            daily_leaderboard = daily_df[['الاسم', 'Score']].sort_values('Score', ascending=False).reset_index(drop=True)
            daily_leaderboard.insert(0, 'الترتيب', daily_leaderboard.index + 1)
            if not daily_leaderboard.empty:
                daily_champion_name = daily_leaderboard.iloc[0]['الاسم']
                daily_champion_score = daily_leaderboard.iloc[0]['Score']

# ==========================================
# 🖥️ الواجهة
# ==========================================
col_h1, col_h2 = st.columns([6, 1])
with col_h1: st.title(f"مرحباً {current_user} 🌟")
with col_h2: 
    if st.button("🚪 خروج", type="primary"): st.session_state["authenticated"] = False; st.rerun()

st.markdown(f"<div style='background-color: #d4edda; color: #155724; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 20px;'><b>{daily_quote['text']}</b> <br><small>— {daily_quote['source']}</small></div>", unsafe_allow_html=True)

st.markdown("---")
col_champ, col_ideas = st.columns([1, 2])
with col_champ:
    st.markdown(f"""
    <div style="background-color: #fff3cd; border: 2px solid #ffeeba; border-radius: 10px; padding: 20px; text-align: center;">
        <h4 style="margin:0; color: #856404;">📅 بطل الأسبوع</h4>
        <h2 style="color: #856404; margin: 10px 0;">{weekly_champion_name}</h2>
        <p style="font-size: 1.1em;">{weekly_champion_score} نقطة</p>
    </div>
    """, unsafe_allow_html=True)
with col_ideas:
    with st.expander("💡 خيارات الفائز", expanded=True):
        st.write(f"القرار عند **{weekly_champion_name}**:")
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

st.markdown("---")
st.info(f"🏅 **ترتيبك: #{my_rank}** | 🛡️ **مستوى {my_level}** | ✨ **نقاط: {my_total_xp}**")
progress = 1 - (((my_level * 500) - my_total_xp) / 500)
st.progress(max(0.0, min(1.0, progress)), text=f"باقي {(my_level * 500) - my_total_xp} نقطة")

# --- التبويبات ---
tab1, tab2, tab3 = st.tabs(["📝 تسجيل اليوم", "🏆 اللوحات", "📊 سجلي"])

with tab1:
    with st.form("entry_form"):
        st.write("### 🕌 الصلوات")
        status_opts = ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"]
        
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            fajr_st = st.selectbox("الفجر", status_opts, key="fs")
            fajr_sn = st.checkbox("سنة الفجر", key="fsn")
        with c_p2:
            dhuhr_st = st.selectbox("الظهر", status_opts, key="ds")
            dhuhr_sn = st.checkbox("سنة الظهر", key="dsn")
        with c_p3:
            asr_st = st.selectbox("العصر", status_opts, key="as")
            
        st.write("---")
        c_p4, c_p5, dum = st.columns(3)
        with c_p4:
            mag_st = st.selectbox("المغرب", status_opts, key="ms")
            mag_sn = st.checkbox("سنة المغرب", key="msn")
        with c_p5:
            isha_st = st.selectbox("العشاء", status_opts, key="is")
            isha_sn = st.checkbox("سنة العشاء", key="isn")

        st.write("---")
        st.write("#### 📿 الروحانيات")
        c_az1, c_az2, c_az3 = st.columns(3)
        az_m = c_az1.checkbox("أذكار الصباح")
        az_e = c_az2.checkbox("أذكار المساء")
        az_p = c_az3.checkbox("أذكار الصلاة")
        
        st.write("")
        c_q1, c_q2 = st.columns(2)
        qiyam = c_q1.select_slider("قيام الليل", ["0", "2", "4", "6", "8", "أكثر"], "0")
        quran = c_q2.select_slider("الورد", ["0", "وجه", "ربع", "نصف", "حزب", "جزء"], "0")

        st.write("#### 🌱 أعمال")
        cc1, cc2, cc3, cc4, cc5 = st.columns(5)
        fasting = cc1.checkbox("صيام")
        majlis = cc2.checkbox("مجلس")
        family = cc3.checkbox("أسرة")
        read = cc4.checkbox("قراءة")
        visit = cc5.checkbox("زيارة")

        if st.form_submit_button("✅ حفظ"):
            day_date = datetime.now().strftime("%Y-%m-%d")
            user_specific_df = full_df[full_df['الاسم'] == current_user] if not full_df.empty else pd.DataFrame()
            if not user_specific_df.empty and day_date in user_specific_df['التاريخ'].astype(str).values:
                st.error(f"⛔ مسجل مسبقاً ({day_date}).")
            else:
                row = [
                    day_date, current_user,
                    fajr_st, "نعم" if fajr_sn else "لا",
                    dhuhr_st, "نعم" if dhuhr_sn else "لا",
                    asr_st,
                    mag_st, "نعم" if mag_sn else "لا",
                    isha_st, "نعم" if isha_sn else "لا",
                    "نعم" if az_m else "لا", "نعم" if az_e else "لا", "نعم" if az_p else "لا",
                    qiyam, quran, "نعم" if fasting else "لا", "نعم" if majlis else "لا",
                    "نعم" if family else "لا", "نعم" if read else "لا", "نعم" if visit else "لا"
                ]
                with st.spinner("جاري الحفظ..."):
                    sheet_data.append_row(row)
                    st.success("تم!")
                    time.sleep(1)
                    st.rerun()

with tab2:
    t2_1, t2_2, t2_3 = st.tabs(["🥇 العام", "📅 الأسبوعي", "🌟 اليومي"])
    with t2_1: st.dataframe(leaderboard[['الترتيب', 'الاسم', 'المستوى', 'Score', 'اللقب']], use_container_width=True, hide_index=True) if not leaderboard.empty else st.info("..")
    with t2_2: st.dataframe(weekly_leaderboard[['الترتيب', 'الاسم', 'Score']], use_container_width=True, hide_index=True) if not weekly_leaderboard.empty else st.info("..")
    with t2_3: 
        if not daily_leaderboard.empty: 
            st.dataframe(daily_leaderboard[['الترتيب', 'الاسم', 'Score']], use_container_width=True, hide_index=True)
            st.success(f"نجم اليوم: {daily_champion_name}")
        else: st.info("..")

with tab3:
    if not full_df.empty and current_user in full_df['الاسم'].values:
        my_hist = full_df[full_df['الاسم'] == current_user]
        st.line_chart(my_hist.set_index("التاريخ")['Score'])
        st.dataframe(my_hist, use_container_width=True)
    else: st.info("سجلك فارغ.")
