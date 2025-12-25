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
# 🔑 كلمة المرور (موحدة للجميع)
# ==========================================
MY_PASSWORD = "Taqwa@2025@Secret!"

# ==========================================
# 💡 الأقوال التحفيزية
# ==========================================
QUOTES = [
    "من حاسب نفسه ربح.",
    "أحب الأعمال إلى الله أدومها وإن قل.",
    "وفي ذلك فليتنافس المتنافسون.",
    "يا ابن آدم، إنما أنت أيام.",
    "بادروا بالأعمال الصالحة.",
]
selected_quote = random.choice(QUOTES)

# ==========================================
# 🚀 الاتصال بقاعدة البيانات (Google Sheets)
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
# 🧮 محرك الحسابات (النقاط)
# ==========================================
def calculate_score(row):
    score = 0
    # حساب النقاط (المجموع 100)
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
    # المنطق: مستوى جديد كل 500 نقطة
    level = 1 + (total_points // 500)
    
    # الألقاب التشريفية
    if level < 5: title = "مبتدئ (🌱)"
    elif level < 10: title = "مجتهد (💪)"
    elif level < 20: title = "سابق للخيرات (🚀)"
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

# 1. حساب النقاط للجميع
if not full_df.empty:
    full_df['Score'] = full_df.apply(calculate_score, axis=1)

    # 2. إنشاء لوحة المتصدرين (Leaderboard)
    # تجميع النقاط حسب الاسم
    leaderboard = full_df.groupby('الاسم')['Score'].sum().reset_index()
    leaderboard.columns = ['الاسم', 'مجموع_النقاط']
    leaderboard = leaderboard.sort_values('مجموع_النقاط', ascending=False).reset_index(drop=True)
    
    # إضافة المستوى واللقب
    leaderboard['المستوى'] = leaderboard['مجموع_النقاط'].apply(lambda x: get_level_and_rank(x)[0])
    leaderboard['اللقب'] = leaderboard['مجموع_النقاط'].apply(lambda x: get_level_and_rank(x)[1])
    leaderboard['الترتيب'] = leaderboard.index + 1
    
    # إحصائيات المستخدم الحالي
    my_stats = leaderboard[leaderboard['الاسم'] == current_user]
    if not my_stats.empty:
        my_total_xp = my_stats.iloc[0]['مجموع_النقاط']
        my_level = my_stats.iloc[0]['المستوى']
        my_rank = my_stats.iloc[0]['الترتيب']
    else:
        my_total_xp = 0
        my_level = 1
        my_rank = "-"
else:
    leaderboard = pd.DataFrame()
    my_total_xp = 0; my_level = 1; my_rank = "-"

# ==========================================
# 🖥️ الواجهة الرئيسية
# ==========================================

# العنوان وزر الخروج
col_h1, col_h2 = st.columns([6, 1])
with col_h1:
    st.title(f"أهلاً بك يا {current_user} 🌟")
with col_h2:
    st.write("")
    if st.button("🚪 خروج", type="primary"):
        st.session_state["authenticated"] = False; st.rerun()

# --- شريط التقدم ---
st.info(f"🏆 **الترتيب الحالي: #{my_rank}** | 🛡️ **المستوى {my_level}** | ✨ **مجموع النقاط: {my_total_xp}**")
points_next_level = (my_level * 500) - my_total_xp
progress = 1 - (points_next_level / 500)
st.progress(max(0.0, min(1.0, progress)), text=f"باقي {points_next_level} نقطة للوصول للمستوى {my_level + 1}.. واصل!")

# --- التبويبات ---
tab1, tab2, tab3 = st.tabs(["📝 تسجيل اليوم", "🏆 لوحة المتصدرين", "📊 سجلي الشخصي"])

# ==========================================
# التبويب 1: التسجيل
# ==========================================
with tab1:
    st.markdown("### 📝 تسجيل إنجاز اليوم")
    with st.form("entry_form"):
        c_main, c_date = st.columns([3, 1])
        st.text_input("الاسم", value=current_user, disabled=True)
        day_date = datetime.now().strftime("%Y-%m-%d")
        c_date.write(f"📅 {day_date}")

        st.write("#### 🕌 الصلاة")
        c1, c2, c3 = st.columns(3)
        fajr_ontime = c1.checkbox("الفجر في وقتها (+10)")
        fajr_mosque = c1.checkbox("الفجر في المسجد (+5)")
        prayers_ontime = c2.slider("الصلوات في وقتها (×6)", 0, 5, 5)
        prayers_mosque = c2.slider("الصلوات في المسجد (×2)", 0, 5, 5)
        qiyam = c3.select_slider("قيام الليل (+10)", ["0", "2", "4", "6", "8", "أكثر"], "0")
        sunnah = c3.checkbox("السنن الرواتب")

        st.write("#### 📖 الزاد الروحي")
        c4, c5 = st.columns(2)
        quran = c4.select_slider("القرآن (+5)", ["0", "1/4", "1/2", "3/4", "1 حزب", "أكثر"])
        adhkar = c5.checkbox("أذكار الصباح والمساء (+5)")
        fasting = c5.checkbox("الصيام (+5)")

        st.write("#### 🌱 اجتماعي وتزكية")
        cc1, cc2, cc3, cc4 = st.columns(4)
        majlis = cc1.checkbox("مجلس علم (+5)")
        family = cc2.checkbox("جلسة أسرية (+5)")
        reading = cc3.checkbox("قراءة (+5)")
        visit = cc4.checkbox("زيارة/صلة (+5)")

        if st.form_submit_button("✅ حفظ التسجيل"):
            # التحقق من التكرار (للمستخدم الحالي فقط)
            user_specific_df = full_df[full_df['الاسم'] == current_user] if not full_df.empty else pd.DataFrame()
            
            if not user_specific_df.empty and day_date in user_specific_df['التاريخ'].astype(str).values:
                st.error(f"⛔ تنبيه! لقد قمت بتسجيل بيانات يوم {day_date} مسبقاً.")
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
                    st.success("تم الحفظ بنجاح! راجع ترتيبك الآن.")
                    time.sleep(1)
                    st.rerun()

# ==========================================
# التبويب 2: لوحة المتصدرين
# ==========================================
with tab2:
    st.markdown("### 🏆 لوحة الأبطال")
    st.markdown("يرتفع المستوى كل **500 نقطة**.")
    
    if not leaderboard.empty:
        # عرض الجدول
        st.dataframe(
            leaderboard[['الترتيب', 'الاسم', 'المستوى', 'مجموع_النقاط', 'اللقب']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "الترتيب": st.column_config.NumberColumn("الترتيب", format="#%d"),
                "مجموع_النقاط": st.column_config.ProgressColumn("النقاط (XP)", min_value=0, max_value=5000, format="%d نقطة"),
            }
        )
        
        # منصة التتويج
        if len(leaderboard) >= 3:
            st.markdown("---")
            col_win1, col_win2, col_win3 = st.columns(3)
            col_win1.success(f"🥇 الأول: {leaderboard.iloc[0]['الاسم']}")
            col_win2.info(f"🥈 الثاني: {leaderboard.iloc[1]['الاسم']}")
            col_win3.warning(f"🥉 الثالث: {leaderboard.iloc[2]['الاسم']}")
            
    else:
        st.info("لا توجد بيانات كافية حتى الآن.")

# ==========================================
# التبويب 3: السجل الشخصي
# ==========================================
with tab3:
    st.subheader("📊 إحصائياتي")
    # فلترة بيانات المستخدم فقط
    my_history = full_df[full_df['الاسم'] == current_user].copy() if not full_df.empty else pd.DataFrame()
    
    if not my_history.empty:
        st.line_chart(my_history.set_index("التاريخ")['Score'])
        st.dataframe(my_history, use_container_width=True)
    else:
        st.info("سجلك فارغ حالياً.")