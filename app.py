import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import altair as alt

# ==========================================
# 1. إعدادات الصفحة والتصميم
# ==========================================
st.set_page_config(
    page_title="سباق الصالحين",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# الألوان
COLOR_PRIMARY = "#009688"
COLOR_GOLD = "#FFD700"
COLOR_RED = "#FF5252"
COLOR_ME = "#E0F2F1"  # لون لتمييز المستخدم

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
    
    /* تنسيق الجدول لتمييز الصفوف */
    .dataframe {{ width: 100%; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. إعدادات اللعبة وقواعد النقاط
# ==========================================
SCORE_RULES = {
    "Fajr": {"جماعة (مسجد)": 50, "في الوقت (بيت)": 30, "قضاء (متأخر)": 5, "فاتتني": -20},
    "Prayers": {"جماعة (مسجد)": 20, "في الوقت (بيت)": 15, "قضاء (متأخر)": 5, "فاتتني": -10},
    "Quran": {"جزء أو أكثر": 40, "حزبين": 30, "حزب": 20, "أقل من حزب": 10, "0": 0},
    "Qiyam": 50,
    "Fasting": 100
}

GROUPS_CONFIG = {
    "مجموعة السائرين": "Saerin@2025",
    "الإدارة": "Admin@MasterKey99!"
}

HEADERS = [
    "التاريخ", "الاسم", "الرمز", "المجموعة",
    "الفجر", "الظهر", "العصر", "المغرب", "العشاء",
    "القرآن", "قيام_الليل", "الصيام",
    "نقاط_اليوم", "ملاحظات"
]

# ==========================================
# 3. الاتصال بقاعدة البيانات
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
        else: st.error("❌ مفاتيح الاتصال مفقودة."); st.stop()
        return gspread.authorize(creds)
    except Exception as e: st.error(f"خطأ في الاتصال: {e}"); st.stop()

client = get_client()
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1XqSb4DmiUEd-mt9WMlVPTow7VdeYUI2O870fsgrZx-0/edit?gid=0#gid=0"

try:
    sh = client.open_by_url(spreadsheet_url)
    sheet_data = sh.get_worksheet(0)
except: st.error("خطأ في فتح ملف Google Sheet"); st.stop()

# ==========================================
# 4. المنطق البرمجي
# ==========================================
if "auth" not in st.session_state: st.session_state["auth"] = False

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
    elif points < 5000: return "👑 سابق بالخيرات"
    else: return "💎 رباني"

# ==========================================
# 5. صفحة تسجيل الدخول
# ==========================================
if not st.session_state["auth"]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><h1 style='text-align:center; color:#009688;'>🕌 سباق الصالحين</h1><p style='text-align:center'>منصة التنافس في الطاعات</p>", unsafe_allow_html=True)
        st.text_input("الاسم:", key="login_user")
        st.text_input("الرمز السري:", type="password", key="login_pin")
        st.text_input("كود المجموعة:", type="password", key="login_pass")
        st.button("🚀 دخول", on_click=check_login)
    st.stop()

# ==========================================
# 6. تحميل البيانات
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

# ==========================================
# 7. واجهة المستخدم
# ==========================================
col_h1, col_h2 = st.columns([6, 1])
with col_h1: st.markdown(f"### 🚩 {c_grp} | المتسابق: **{c_user}**")
with col_h2: 
    if st.button("خروج"):
        st.session_state["auth"] = False
        st.rerun()

# --- لوحة تحكم الإدارة ---
if c_grp == "الإدارة":
    st.markdown("## 👮‍♂️ غرفة المراقبة (الإدارة)")
    if df.empty: st.warning("لا توجد بيانات.")
    else:
        st.markdown("### 🏆 الترتيب العام")
        leaderboard = df.groupby('الاسم')['نقاط_اليوم'].sum().sort_values(ascending=False).reset_index()
        leaderboard.insert(0, 'الترتيب', leaderboard.index + 1)
        st.dataframe(leaderboard, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📈 تحليل متسابق")
        users = df['الاسم'].unique().tolist()
        sel_user = st.selectbox("اختر المتسابق:", users)
        if sel_user:
            udata = df[df['الاسم'] == sel_user].sort_values('DateObj')
            chart = alt.Chart(udata).mark_area(color='#009688').encode(x='DateObj:T', y='نقاط_اليوم:Q').properties(height=300)
            st.altair_chart(chart, use_container_width=True)

# --- واجهة المتسابق ---
else:
    my_total_score = 0
    my_rank_num = "-"
    
    # حساب المجاميع العامة (تاريخي)
    if not df.empty:
        my_data = df[df['الاسم'] == c_user]
        my_total_score = my_data['نقاط_اليوم'].sum()
        
        # الترتيب العام (تراكمي)
        total_scores = df.groupby('الاسم')['نقاط_اليوم'].sum().sort_values(ascending=False).reset_index()
        if c_user in total_scores['الاسم'].values:
            my_rank_num = total_scores[total_scores['الاسم'] == c_user].index[0] + 1

    rank_title = get_rank_title(my_total_score)
    
    # كروت المعلومات
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"<div class='game-card'><h3>الرتبة</h3><div class='level-badge'>{rank_title}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='game-card'><h3>مجموع النقاط</h3><div class='value'>{int(my_total_score)}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='game-card'><h3>الترتيب العام</h3><div class='value'>#{my_rank_num}</div></div>", unsafe_allow_html=True)

    next_lvl = (int(my_total_score) // 500 + 1) * 500
    st.progress(min(1.0, (my_total_score % 500) / 500))

    tab1, tab2, tab3 = st.tabs(["📝 تسجيل اليوم", "🏆 ترتيب اليوم", "📜 سجلي"])

    # --- TAB 1: تسجيل ---
    with tab1:
        today = datetime.now().strftime("%Y-%m-%d")
        already_done = False
        if not df.empty:
            check = df[(df['الاسم'] == c_user) & (df['التاريخ'] == today)]
            if not check.empty: already_done = True
            
        if already_done:
            st.markdown(f"<div class='locked-box'>🔒 تم تسجيل يوم {today} بنجاح.<br>لا يمكنك التعديل الآن.</div>", unsafe_allow_html=True)
        else:
            with st.form("daily"):
                st.markdown("### 📋 مهام اليوم")
                st.markdown("**1️⃣ صلاة الفجر 🕌**")
                fajr = st.selectbox("الفجر", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء (متأخر)", "فاتتني"], label_visibility="collapsed")
                st.markdown("---")
                st.markdown("**2️⃣ الصلوات المفروضة ⏰**")
                c1, c2, c3, c4 = st.columns(4)
                opts = ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء (متأخر)", "فاتتني"]
                p_res = {
                    "الظهر": c1.selectbox("الظهر", opts), "العصر": c2.selectbox("العصر", opts),
                    "المغرب": c3.selectbox("المغرب", opts), "العشاء": c4.selectbox("العشاء", opts)
                }
                st.markdown("---")
                c_q1, c_q2 = st.columns(2)
                with c_q1:
                    st.markdown("**3️⃣ القرآن 📖**")
                    quran = st.selectbox("الكمية", ["0", "أقل من حزب", "حزب", "حزبين", "جزء أو أكثر"], label_visibility="collapsed")
                with c_q2:
                    st.markdown("**4️⃣ قيام (3 ركعات) 🌙**")
                    qiyam = st.checkbox("تم")
                st.markdown("---")
                st.markdown("**5️⃣ صيام تطوع**")
                fasting = st.checkbox("صائم اليوم")
                
                if st.form_submit_button("✅ اعتماد"):
                    r_data = {"الفجر": fajr, "القرآن": quran, "قيام_الليل": "نعم" if qiyam else "لا", "الصيام": "نعم" if fasting else "لا"}
                    r_data.update(p_res)
                    pts = calculate_score(r_data)
                    row = [today, c_user, c_pin, c_grp, fajr, p_res["الظهر"], p_res["العصر"], p_res["المغرب"], p_res["العشاء"], quran, "نعم" if qiyam else "لا", "نعم" if fasting else "لا", pts, ""]
                    try:
                        sheet_data.append_row(row)
                        st.balloons()
                        st.success(f"تم الحفظ! نقاطك اليوم: {pts}")
                        time.sleep(2)
                        st.rerun()
                    except: st.error("خطأ اتصال")

    # --- TAB 2: ترتيب اليوم (مع الفارق) ---
    with tab2:
        today = datetime.now().strftime("%Y-%m-%d")
        st.markdown(f"### 📊 ترتيب المجموعة ليوم: {today}")
        
        if not df.empty:
            daily_df = df[(df['التاريخ'] == today) & (df['المجموعة'] == c_grp)].copy()
            
            if not daily_df.empty:
                # ترتيب المتسابقين اليوم
                daily_df = daily_df.sort_values('نقاط_اليوم', ascending=False).reset_index(drop=True)
                
                # إضافة عمود الترتيب
                daily_df['المركز'] = daily_df.index + 1
                
                # حساب الفارق عن المتصدر
                top_score = daily_df.iloc[0]['نقاط_اليوم']
                daily_df['الفارق عن الأول'] = top_score - daily_df['نقاط_اليوم']
                
                # تجميل الجدول
                final_table = daily_df[['المركز', 'الاسم', 'نقاط_اليوم', 'الفارق عن الأول']]
                
                # 💡 تمييز المستخدم الحالي (Highlight)
                def highlight_me(x):
                    return ['background-color: #E0F2F1; font-weight: bold; border: 2px solid #009688' if x['الاسم'] == c_user else '' for _ in x]

                st.dataframe(final_table.style.apply(highlight_me, axis=1), use_container_width=True)
                
                # 🚀 رسالة تحفيزية ذكية
                my_daily_stats = daily_df[daily_df['الاسم'] == c_user]
                if not my_daily_stats.empty:
                    my_pos = my_daily_stats.iloc[0]['المركز']
                    my_score = my_daily_stats.iloc[0]['نقاط_اليوم']
                    
                    if my_pos == 1:
                        st.balloons()
                        st.markdown(f"""
                        <div style="background-color:#d4edda; padding:15px; border-radius:10px; color:#155724; text-align:center; border:2px solid #c3e6cb;">
                            👑 <b>ما شاء الله! أنت المتصدر اليوم!</b><br>
                            حافظ على هذا المستوى غداً.
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        diff = int(my_daily_stats.iloc[0]['الفارق عن الأول'])
                        st.markdown(f"""
                        <div style="background-color:#fff3cd; padding:15px; border-radius:10px; color:#856404; text-align:center; border:2px solid #ffeeba;">
                            ⚠️ <b>انتبه!</b> أنت في المركز <b>#{my_pos}</b>.<br>
                            الفرق بينك وبين الأول هو <b>{diff}</b> نقطة فقط.<br>
                            شد حيلك بكرة عشان تجيب المركز الأول! 💪
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("لم تقم بالتسجيل اليوم بعد، لذلك لا تظهر في القائمة.")
            else:
                st.info("لم يسجل أحد نقاطه اليوم حتى الآن. كن الأول!")
        else: st.info("جاري التحميل...")

    # --- TAB 3: سجلي ---
    with tab3:
        if not df.empty:
            my_hist = df[df['الاسم'] == c_user].sort_values('DateObj', ascending=False)
            if not my_hist.empty:
                st.markdown("#### 📅 سجل الأيام السابقة")
                st.dataframe(my_hist[['التاريخ', 'نقاط_اليوم', 'الفجر', 'القرآن', 'قيام_الليل', 'الصيام']], use_container_width=True)
            else: st.info("لا يوجد سجل.")
