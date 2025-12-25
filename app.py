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
# 💎 مكتبة التحفيز
# ==========================================
MOTIVATIONAL_QUOTES = [
    {"text": "وَسَارِعُوا إِلَىٰ مَغْفِرَةٍ مِّن رَّبِّكُمْ", "source": "آل عمران: 133"},
    {"text": "فَاسْتَبِقُوا الْخَيْرَاتِ", "source": "البقرة: 148"},
    {"text": "أحب الأعمال إلى الله أدومها وإن قل", "source": "حديث شريف"},
    {"text": "الدال على الخير كفاعله", "source": "حديث شريف"},
    {"text": "من صلى البردين دخل الجنة", "source": "حديث شريف"},
    {"text": "ركعتا الفجر خير من الدنيا وما فيها", "source": "حديث شريف"},
    {"text": "مثل الذي يذكر ربه والذي لا يذكر ربه مثل الحي والميت", "source": "حديث شريف"},
    {"text": "إِنَّ الصَّلَاةَ كَانَتْ عَلَى الْمُؤْمِنِينَ كِتَابًا مَوْقُوتًا", "source": "النساء: 103"}
]
daily_quote = random.choice(MOTIVATIONAL_QUOTES)

# ==========================================
# 💡 مقترحات بطل الأسبوع
# ==========================================
DEFAULT_WEEKLY_IDEAS = {
    "❤️ عمل خيري": [
        "شراء كرتون ماء وتوزيعه على العمال", "تنظيف مسجد الحي وتطيبه",
        "جمع مبلغ بسيط للصدقة عن المجموعة", "زيارة مريض", "إطعام قطط/طيور"
    ],
    "🍉 طعام ولمة": [
        "فطور جماعي", "عشاء خفيف (نواشف)", "قهوة في حديقة"
    ],
    "⚽ نشاط وترفيه": [
        "مباراة كرة قدم", "مشي جماعي 30 دقيقة", "مسابقة ثقافية", "كشتة قصيرة"
    ]
}
WEEKLY_IDEAS = DEFAULT_WEEKLY_IDEAS

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
# 🧮 محرك الحسابات (المنطق الجديد)
# ==========================================
def calculate_score(row):
    score = 0
    
    # 1. حساب الصلوات (جماعة=10، وقت=6، قضاء=0)
    # 2. حساب السنن (2 نقطة لكل سنة)
    prayers = ['الفجر', 'الظهر', 'العصر', 'المغرب', 'العشاء']
    
    for p in prayers:
        status = row.get(f'{p}_حالة')
        if status == 'جماعة (مسجد)': score += 10
        elif status == 'في الوقت (بيت)': score += 6
        
        # السنن (العصر ليس له سنة راتبة مؤكدة في التطبيق للتبسيط)
        if p != 'العصر': 
            if row.get(f'{p}_سنة') == 'نعم': score += 3

    # 3. الأذكار (3 نقاط لكل نوع)
    if row.get('أذكار_الصباح') == 'نعم': score += 3
    if row.get('أذكار_المساء') == 'نعم': score += 3
    if row.get('أذكار_الصلاة') == 'نعم': score += 3 # أذكار دبر الصلوات

    # 4. باقي الأعمال
    try: 
        qiyam_val = str(row.get('قيام'))
        if qiyam_val not in ["0", "لا", "", "None"]: score += 8
    except: pass
    
    try:
        quran_val = str(row.get('القرآن')) 
        if quran_val not in ["0", "لا", "", "None"]: score += 8
    except: pass
    
    if row.get('الصيام') == 'نعم': score += 10
    if row.get('مجلس') == 'نعم': score += 4
    if row.get('أسرة') == 'نعم': score += 4
    if row.get('قراءة') == 'نعم': score += 4
    if row.get('زيارة') == 'نعم': score += 4
    
    return min(score, 100) # الحد الأقصى 100

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

leaderboard = pd.DataFrame()
weekly_leaderboard = pd.DataFrame()
daily_leaderboard = pd.DataFrame()
weekly_champion_name = "---"; weekly_champion_score = 0
daily_champion_name = "---"; daily_champion_score = 0
my_total_xp = 0; my_level = 1; my_rank = "-"

if not full_df.empty:
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
    current_week_number = datetime.now().isocalendar()[1]
    current_year = datetime.now().year
    full_df['WeekNum'] = full_df['DateObj'].dt.isocalendar().week
    full_df['YearNum'] = full_df['DateObj'].dt.year
    weekly_df = full_df[(full_df['WeekNum'] == current_week_number) & (full_df['YearNum'] == current_year)]
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
# 🖥️ الواجهة الرئيسية
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
            st.info("**❤️ عمل خيري**")
            for i in WEEKLY_IDEAS["❤️ عمل خيري"]: st.write(f"- {i}")
        with c2: 
            st.warning("**🍉 طعام**")
            for i in WEEKLY_IDEAS["🍉 طعام ولمة"]: st.write(f"- {i}")
        with c3: 
            st.success("**⚽ ترفيه**")
            for i in WEEKLY_IDEAS["⚽ نشاط وترفيه"]: st.write(f"- {i}")

st.markdown("---")
st.info(f"🏅 **ترتيبك العام: #{my_rank}** | 🛡️ **المستوى {my_level}** | ✨ **كل النقاط: {my_total_xp}**")
points_next_level = (my_level * 500) - my_total_xp
progress = 1 - (points_next_level / 500)
st.progress(max(0.0, min(1.0, progress)), text=f"باقي {points_next_level} نقطة")

# --- التبويبات ---
tab1, tab2, tab3 = st.tabs(["📝 تسجيل اليوم", "🏆 لوحات الصدارة", "📊 سجلي"])

with tab1:
    with st.form("entry_form"):
        st.write("### 🕌 الصلوات الخمس")
        st.caption("حدد حالة كل صلاة (جماعة / وقت / قضاء) وهل صليت السنة الراتبة؟")
        
        # خيارات الحالة
        status_options = ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"]
        
        # الصف الأول: فجر - ظهر - عصر
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            st.markdown("**الفجر**")
            fajr_status = st.selectbox("حالة الفجر", status_options, key="fajr_st")
            fajr_sunnah = st.checkbox("سنة الفجر", key="fajr_sn")
        with c_p2:
            st.markdown("**الظهر**")
            dhuhr_status = st.selectbox("حالة الظهر", status_options, key="dhuhr_st")
            dhuhr_sunnah = st.checkbox("سنة الظهر", key="dhuhr_sn")
        with c_p3:
            st.markdown("**العصر**")
            asr_status = st.selectbox("حالة العصر", status_options, key="asr_st")
            st.write("") # العصر غالباً ليس له سنة راتبة مؤكدة في التتبع اليومي البسيط
            
        st.write("---")
        # الصف الثاني: مغرب - عشاء
        c_p4, c_p5, c_dummy = st.columns(3)
        with c_p4:
            st.markdown("**المغرب**")
            maghrib_status = st.selectbox("حالة المغرب", status_options, key="mag_st")
            maghrib_sunnah = st.checkbox("سنة المغرب", key="mag_sn")
        with c_p5:
            st.markdown("**العشاء**")
            isha_status = st.selectbox("حالة العشاء", status_options, key="isha_st")
            isha_sunnah = st.checkbox("سنة العشاء", key="isha_sn")

        st.write("---")
        st.write("#### 📿 الأذكار والقرآن")
        c_az1, c_az2, c_az3 = st.columns(3)
        adhkar_morn = c_az1.checkbox("☀️ أذكار الصباح")
        adhkar_eve = c_az2.checkbox("🌙 أذكار المساء")
        adhkar_post = c_az3.checkbox("🤲 أذكار دبر الصلاة")
        
        st.write("")
        c_q1, c_q2 = st.columns(2)
        qiyam = c_q1.select_slider("قيام الليل", ["0", "2", "4", "6", "8", "أكثر"], "0")
        quran = c_q2.select_slider("الورد القرآني", ["0", "وجه", "ربع", "نصف", "حزب", "حزبين"], "0")

        st.write("#### 🌱 أعمال أخرى")
        cc1, cc2, cc3, cc4, cc5 = st.columns(5)
        fasting = cc1.checkbox("صيام")
        majlis = cc2.checkbox("مجلس التدارس")
        family = cc3.checkbox("بر/أسرة")
        reading = cc4.checkbox("قراءة")
        visit = cc5.checkbox("زيارة")

        if st.form_submit_button("✅ حفظ التسجيل"):
            day_date = datetime.now().strftime("%Y-%m-%d")
            user_specific_df = full_df[full_df['الاسم'] == current_user] if not full_df.empty else pd.DataFrame()
            if not user_specific_df.empty and day_date in user_specific_df['التاريخ'].astype(str).values:
                st.error(f"⛔ قمت بالتسجيل مسبقاً لهذا اليوم ({day_date}).")
            else:
                # ترتيب البيانات للحفظ
                row = [
                    day_date, current_user,
                    # الصلوات
                    fajr_status, "نعم" if fajr_sunnah else "لا",
                    dhuhr_status, "نعم" if dhuhr_sunnah else "لا",
                    asr_status,
                    maghrib_status, "نعم" if maghrib_sunnah else "لا",
                    isha_status, "نعم" if isha_sunnah else "لا",
                    # الأذكار
                    "نعم" if adhkar_morn else "لا",
                    "نعم" if adhkar_eve else "لا",
                    "نعم" if adhkar_post else "لا",
                    # الباقي
                    qiyam, quran,
                    "نعم" if fasting else "لا",
                    "نعم" if majlis else "لا", "نعم" if family else "لا",
                    "نعم" if reading else "لا", "نعم" if visit else "لا"
                ]
                with st.spinner("جاري الحفظ..."):
                    # هنا نستخدم أسماء الأعمدة الجديدة في رأس الملف (سيتم إضافتها تلقائياً كصف جديد)
                    # لكن يفضل مسح الملف القديم أو إضافة عناوين يدوياً إذا اختلطت البيانات
                    sheet_data.append_row(row)
                    st.success("تم الحفظ بنجاح!")
                    time.sleep(1)
                    st.rerun()

with tab2:
    st.markdown("### اختر الترتيب:")
    t2_1, t2_2, t2_3 = st.tabs(["🥇 العام", "📅 الأسبوعي", "🌟 اليومي"])
    
    with t2_1:
        if not leaderboard.empty: st.dataframe(leaderboard[['الترتيب', 'الاسم', 'المستوى', 'Score', 'اللقب']], use_container_width=True, hide_index=True)
        else: st.info("لا بيانات")
    with t2_2:
        if not weekly_leaderboard.empty: st.dataframe(weekly_leaderboard[['الترتيب', 'الاسم', 'Score']], use_container_width=True, hide_index=True)
        else: st.info("بداية أسبوع جديدة!")
    with t2_3:
        if not daily_leaderboard.empty: 
            st.dataframe(daily_leaderboard[['الترتيب', 'الاسم', 'Score']], use_container_width=True, hide_index=True)
            st.success(f"🌟 **نجم اليوم:** {daily_champion_name}")
        else: st.info("لم يسجل أحد اليوم.")

with tab3:
    my_history = full_df[full_df['الاسم'] == current_user].copy() if not full_df.empty else pd.DataFrame()
    if not my_history.empty:
        st.line_chart(my_history.set_index("التاريخ")['Score'])
        st.dataframe(my_history, use_container_width=True)
    else: st.info("سجلك فارغ.")
