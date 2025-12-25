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
    {"text": "يد الله مع الجماعة", "source": "حديث شريف"},
    {"text": "إِنَّمَا الْأَعْمَالُ بِالنِّيَّاتِ", "source": "حديث شريف"},
    {"text": "لا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا", "source": "البقرة: 286"},
    {"text": "اغتنم خمساً قبل خمس: شبابك قبل هرمك...", "source": "حديث شريف"},
    {"text": "المؤمن القوي خير وأحب إلى الله من المؤمن الضعيف", "source": "حديث شريف"},
    {"text": "وَمَنْ يَتَّقِ اللَّهَ يَجْعَلْ لَهُ مَخْرَجًا", "source": "الطلاق: 2"},
    {"text": "تبسمك في وجه أخيك صدقة", "source": "حديث شريف"},
    {"text": "وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا", "source": "العنكبوت: 69"}
]
daily_quote = random.choice(MOTIVATIONAL_QUOTES)

# ==========================================
# 💡 مقترحات بطل الأسبوع
# ==========================================
DEFAULT_WEEKLY_IDEAS = {
    "❤️ عمل خيري": [
        "شراء كرتون ماء وتوزيعه على العمال",
        "تنظيف مسجد الحي وتطيبه",
        "جمع مبلغ بسيط للصدقة عن المجموعة",
        "زيارة مريض في المستشفى أو الحي",
        "إطعام قطط أو طيور في مكان عام"
    ],
    "🍉 طعام ولمة": [
        "فطور جماعي",
        "عشاء خفيف في بيت أحد الشباب",
        "شاي وقهوة في ممشى أو حديقة"
    ],
    "⚽ نشاط وترفيه": [
        "مباراة كرة قدم",
        "مشي جماعي لمدة 30 دقيقة",
        "مسابقة ثقافية خفيفة",
        "رحلة قصيرة لنصف يوم"
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
# 🧮 محرك الحسابات
# ==========================================
def calculate_score(row):
    score = 0
    if row.get('الفجر(وقت)') == 'نعم': score += 10
    if row.get('الفجر(مسجد)') == 'نعم': score += 5
    try: score += int(row.get('الصلوات(وقت)', 0)) * 6
    except: pass
    try: score += int(row.get('الصلوات(مسجد)', 0)) * 2
    except: pass
    if str(row.get('قيام')) not in ["0", "لا", ""]: score += 10
    if str(row.get('القرآن')) not in ["0", "لا", ""]: score += 5
    if row.get('الأذكار') == 'نعم': score += 5
    if row.get('الصيام') == 'نعم': score += 5
    if row.get('مجلس') == 'نعم': score += 5
    if row.get('أسرة') == 'نعم': score += 5
    if row.get('قراءة') == 'نعم': score += 5
    if row.get('زيارة') == 'نعم': score += 5
    return min(score, 100)

def get_level_and_rank(total_points):
    level = 1 + (total_points // 500)
    if level < 5: title = "مبتدئ (🌱)"
    elif level < 10: title = "مجتهد (💪)"
    elif level < 20: title = "سابق (🚀)"
    else: title = "رباني (👑)"
    return level, title

# ==========================================
# 📊 تجهيز البيانات (يومي - أسبوعي - عام)
# ==========================================
current_user = st.session_state["user_name"]

try:
    data = sheet_data.get_all_records()
    full_df = pd.DataFrame(data)
except:
    full_df = pd.DataFrame()

# متغيرات العرض
leaderboard = pd.DataFrame()
weekly_leaderboard = pd.DataFrame()
daily_leaderboard = pd.DataFrame()

weekly_champion_name = "---"
weekly_champion_score = 0
daily_champion_name = "---"
daily_champion_score = 0

if not full_df.empty:
    full_df['Score'] = full_df.apply(calculate_score, axis=1)
    
    # تحويل التاريخ لمعالجته
    full_df['DateObj'] = pd.to_datetime(full_df['التاريخ'], errors='coerce')
    
    # ----------------------------------------------------
    # 1. الترتيب العام (تراكمي)
    # ----------------------------------------------------
    leaderboard = full_df.groupby('الاسم')['Score'].sum().reset_index()
    leaderboard = leaderboard.sort_values('Score', ascending=False).reset_index(drop=True)
    leaderboard['المستوى'] = leaderboard['Score'].apply(lambda x: get_level_and_rank(x)[0])
    leaderboard['اللقب'] = leaderboard['Score'].apply(lambda x: get_level_and_rank(x)[1])
    leaderboard.insert(0, 'الترتيب', leaderboard.index + 1) # إضافة عمود الترتيب في البداية

    # إحصائيات المستخدم الحالي (من الترتيب العام)
    my_stats = leaderboard[leaderboard['الاسم'] == current_user]
    if not my_stats.empty:
        my_total_xp = my_stats.iloc[0]['Score']
        my_level = my_stats.iloc[0]['المستوى']
        my_rank = my_stats.iloc[0]['الترتيب']
    else:
        my_total_xp = 0; my_level = 1; my_rank = "-"

    # ----------------------------------------------------
    # 2. ترتيب الأسبوع الحالي (يتصفر كل أسبوع)
    # ----------------------------------------------------
    # نحدد رقم الأسبوع الحالي في السنة
    current_week_number = datetime.now().isocalendar()[1]
    current_year = datetime.now().year
    
    # فلترة البيانات لتشمل فقط الأسبوع الحالي
    full_df['WeekNum'] = full_df['DateObj'].dt.isocalendar().week
    full_df['YearNum'] = full_df['DateObj'].dt.year
    
    weekly_df = full_df[(full_df['WeekNum'] == current_week_number) & (full_df['YearNum'] == current_year)]
    
    if not weekly_df.empty:
        weekly_leaderboard = weekly_df.groupby('الاسم')['Score'].sum().reset_index()
        weekly_leaderboard = weekly_leaderboard.sort_values('Score', ascending=False).reset_index(drop=True)
        weekly_leaderboard.insert(0, 'الترتيب', weekly_leaderboard.index + 1)
        
        if not weekly_leaderboard.empty:
            weekly_champion_name = weekly_leaderboard.iloc[0]['الاسم']
            weekly_champion_score = weekly_leaderboard.iloc[0]['Score']

    # ----------------------------------------------------
    # 3. ترتيب اليوم (اليومي)
    # ----------------------------------------------------
    today_str = datetime.now().strftime("%Y-%m-%d")
    daily_df = full_df[full_df['التاريخ'] == today_str]
    
    if not daily_df.empty:
        daily_leaderboard = daily_df[['الاسم', 'Score']].sort_values('Score', ascending=False).reset_index(drop=True)
        daily_leaderboard.insert(0, 'الترتيب', daily_leaderboard.index + 1)
        
        if not daily_leaderboard.empty:
            daily_champion_name = daily_leaderboard.iloc[0]['الاسم']
            daily_champion_score = daily_leaderboard.iloc[0]['Score']

else:
    my_total_xp = 0; my_level = 1; my_rank = "-"

# ==========================================
# 🖥️ الواجهة الرئيسية
# ==========================================

# العنوان
col_h1, col_h2 = st.columns([6, 1])
with col_h1:
    st.title(f"مرحباً {current_user} 🌟")
with col_h2:
    if st.button("🚪 خروج", type="primary"):
        st.session_state["authenticated"] = False; st.rerun()

# الصندوق التحفيزي
st.markdown(f"""
<div style="background-color: #d4edda; color: #155724; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
    <b>{daily_quote['text']}</b> <br><small>— {daily_quote['source']}</small>
</div>
""", unsafe_allow_html=True)

# 🏆 === لوحة الصدارة البارزة (الأسبوعي) === 🏆
st.markdown("---")
col_champ, col_ideas = st.columns([1, 2])

with col_champ:
    st.markdown(f"""
    <div style="background-color: #fff3cd; border: 2px solid #ffeeba; border-radius: 10px; padding: 20px; text-align: center;">
        <h4 style="margin:0; color: #856404;">📅 بطل هذا الأسبوع</h4>
        <h2 style="color: #856404; margin: 10px 0;">{weekly_champion_name}</h2>
        <p style="font-size: 1.1em;">{weekly_champion_score} نقطة</p>
    </div>
    """, unsafe_allow_html=True)

with col_ideas:
    with st.expander("💡 خيارات الفائز لهذا الأسبوع", expanded=True):
        st.write(f"القرار عند **{weekly_champion_name}**، اختر لنا:")
        c_i1, c_i2, c_i3 = st.columns(3)
        with c_i1:
            st.info("**❤️ عمل خيري**")
            for item in WEEKLY_IDEAS["❤️ عمل خيري"]: st.write(f"- {item}")
        with c_i2:
            st.warning("**🍉 طعام ولمة**")
            for item in WEEKLY_IDEAS["🍉 طعام ولمة"]: st.write(f"- {item}")
        with c_i3:
            st.success("**⚽ نشاط**")
            for item in WEEKLY_IDEAS["⚽ نشاط وترفيه"]: st.write(f"- {item}")

st.markdown("---")

# شريط التقدم العام
st.info(f"🏅 **ترتيبك العام: #{my_rank}** | 🛡️ **المستوى {my_level}** | ✨ **كل النقاط: {my_total_xp}**")
points_next_level = (my_level * 500) - my_total_xp
progress = 1 - (points_next_level / 500)
st.progress(max(0.0, min(1.0, progress)), text=f"باقي {points_next_level} نقطة للمستوى التالي")

# --- التبويبات ---
tab1, tab2, tab3 = st.tabs(["📝 تسجيل اليوم", "🏆 لوحات الصدارة", "📊 سجلي"])

with tab1:
    with st.form("entry_form"):
        c_main, c_date = st.columns([3, 1])
        st.text_input("الاسم", value=current_user, disabled=True)
        day_date = datetime.now().strftime("%Y-%m-%d")
        c_date.write(f"📅 {day_date}")

        st.write("#### 🕌 الصلاة")
        c1, c2, c3 = st.columns(3)
        fajr_ontime = c1.checkbox("الفجر وقت (+10)")
        fajr_mosque = c1.checkbox("الفجر مسجد (+5)")
        prayers_ontime = c2.slider("الصلوات وقت (×6)", 0, 5, 5)
        prayers_mosque = c2.slider("الصلوات مسجد (×2)", 0, 5, 5)
        qiyam = c3.select_slider("قيام الليل (+10)", ["0", "2", "4", "6", "8", "أكثر"], "0")
        sunnah = c3.checkbox("السنن")

        st.write("#### 📖 روحانيات")
        c4, c5 = st.columns(2)
        quran = c4.select_slider("القرآن (+5)", ["0", "1/4", "1/2", "3/4", "1 حزب", "أكثر"])
        adhkar = c5.checkbox("الأذكار (+5)")
        fasting = c5.checkbox("الصيام (+5)")

        st.write("#### 🌱 اجتماعي")
        cc1, cc2, cc3, cc4 = st.columns(4)
        majlis = cc1.checkbox("مجلس علم (+5)")
        family = cc2.checkbox("جلسة أهل (+5)")
        reading = cc3.checkbox("قراءة (+5)")
        visit = cc4.checkbox("زيارة (+5)")

        if st.form_submit_button("✅ حفظ"):
            user_specific_df = full_df[full_df['الاسم'] == current_user] if not full_df.empty else pd.DataFrame()
            if not user_specific_df.empty and day_date in user_specific_df['التاريخ'].astype(str).values:
                st.error(f"⛔ مسجل مسبقاً لهذا اليوم ({day_date}).")
            else:
                row = [
                    day_date, current_user, 
                    "نعم" if fajr_ontime else "لا", "نعم" if fajr_mosque else "لا",
                    prayers_ontime, prayers_mosque, qiyam, quran,
                    "نعم" if adhkar else "لا", "نعم" if fasting else "لا",
                    "نعم" if majlis else "لا", "نعم" if family else "لا",
                    "نعم" if reading else "لا", "نعم" if visit else "لا"
                ]
                with st.spinner("جاري الحفظ..."):
                    sheet_data.append_row(row)
                    st.success("تم الحفظ!")
                    time.sleep(1)
                    st.rerun()

with tab2:
    st.markdown("### اختر الترتيب الذي تريد عرضه:")
    t2_1, t2_2, t2_3 = st.tabs(["🥇 الترتيب العام", "📅 ترتيب هذا الأسبوع", "🌟 ترتيب اليوم"])
    
    with t2_1:
        st.markdown("الترتيب التراكمي منذ بداية السباق")
        if not leaderboard.empty:
            st.dataframe(leaderboard[['الترتيب', 'الاسم', 'المستوى', 'Score', 'اللقب']], use_container_width=True, hide_index=True)
        else: st.info("لا بيانات")
        
    with t2_2:
        st.markdown(f"نقاط هذا الأسبوع فقط (الأسبوع رقم {current_week_number})")
        if not weekly_leaderboard.empty:
            st.dataframe(weekly_leaderboard[['الترتيب', 'الاسم', 'Score']], use_container_width=True, hide_index=True)
        else: st.info("لم يسجل أحد نقاطاً هذا الأسبوع بعد.")
        
    with t2_3:
        st.markdown(f"نقاط اليوم ({today_str})")
        if not daily_leaderboard.empty:
            st.dataframe(daily_leaderboard[['الترتيب', 'الاسم', 'Score']], use_container_width=True, hide_index=True)
            st.success(f"🌟 **نجم اليوم هو:** {daily_champion_name}")
        else: st.info("لم يسجل أحد اليوم بعد.")

with tab3:
    my_history = full_df[full_df['الاسم'] == current_user].copy() if not full_df.empty else pd.DataFrame()
    if not my_history.empty:
        st.line_chart(my_history.set_index("التاريخ")['Score'])
        st.dataframe(my_history, use_container_width=True)
    else:
        st.info("لا يوجد سجل.")
