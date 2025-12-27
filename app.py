import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import random
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="سباق الصالحين",
    layout="wide",
    page_icon="🕌",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🎨 DESIGN & CSS (Style Moderne)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
    }
    
    /* Arrière-plan subtil */
    .stApp {
        background-color: #f8f9fa;
    }

    /* Cartes de statistiques (Haut de page) */
    .metric-card {
        background-color: white;
        border-radius: 15px;
        padding: 20px;
        border-right: 5px solid #009688; /* Couleur verte islamique */
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    .metric-card h3 { margin: 0; font-size: 1rem; color: #666; }
    .metric-card h1 { margin: 0; font-size: 2.5rem; color: #009688; font-weight: bold; }

    /* Boutons */
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

    /* Expander (Menus dépliants) */
    .streamlit-expanderHeader {
        background-color: white;
        border-radius: 10px;
        font-weight: bold;
        color: #333;
    }
    
    /* Titres */
    h1, h2, h3, h4 { color: #2c3e50 !important; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔑 CONFIGURATION (Mots de passe & Groupes)
# ==========================================
GROUPS_CONFIG = {
    "مجموعة الفردوس": "Firdaws@786!Top",
    "مجموعة الريان": "Rayyan#2025$Win",
    "الإدارة": "Admin@MasterKey99!"
}

# ==========================================
# 📋 STRUCTURE DES DONNÉES (Colonnes)
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
# 🚀 CONNEXION GOOGLE SHEETS
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
            st.error("❌ Clés d'authentification manquantes.")
            st.stop()
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
        st.stop()

client = get_client()
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1XqSb4DmiUEd-mt9WMlVPTow7VdeYUI2O870fsgrZx-0/edit?gid=0#gid=0"

try:
    sh = client.open_by_url(spreadsheet_url)
    sheet_data = sh.get_worksheet(0)
except Exception as e:
    st.error(f"Erreur ouverture fichier : {e}")
    st.stop()

# ==========================================
# 🔒 GESTION LOGIN
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
        st.error("⛔ Nom ou mot de passe incorrect")

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
        st.text_input("👤 الاسم الكريم (Votre Nom) :", key="login_user")
        st.text_input("🔑 رمز المجموعة (Code) :", type="password", key="login_pass")
        st.button("🚀 Démarrer (دخول)", on_click=check_login, use_container_width=True)
    st.stop()

# ==========================================
# 🧮 LOGIQUE DES POINTS (SCORING)
# ==========================================
def safe_str(val):
    return str(val).strip() if val else ""

def calculate_score(row):
    score = 0
    
    # 1. Prières
    prayers_map = {'الفجر': 'الفجر_حالة', 'الظهر': 'الظهر_حالة', 'العصر': 'العصر_حالة', 'المغرب': 'المغرب_حالة', 'العشاء': 'العشاء_حالة'}
    for p_name, col_name in prayers_map.items():
        status = safe_str(row.get(col_name))
        if status == 'جماعة (مسجد)': score += 10
        elif status == 'في الوقت (بيت)': score += 6
        
        if p_name != 'العصر':
            if safe_str(row.get(f"{p_name}_سنة")) == 'نعم': score += 3
            
    if safe_str(row.get('الضحى')) == 'نعم': score += 5
    
    # 2. Adhkar
    chk_list = ['أذكار_الصباح', 'أذكار_المساء', 'أذكار_الصلاة', 'أذكار_النوم']
    for chk in chk_list:
        if safe_str(row.get(chk)) == 'نعم': score += 3
    if safe_str(row.get('سورة_الملك')) == 'نعم': score += 5
    
    # 3. Coran & Qiyam
    quran_val = safe_str(row.get('القرآن'))
    quran_points = {"ثمن": 2, "ربع": 4, "نصف": 6, "حزب": 8, "حزبين": 10}
    score += quran_points.get(quran_val, 0)
    
    qiyam_val = safe_str(row.get('قيام'))
    qiyam_points = {"ركعتان": 3, "٤ ركعات": 5, "٦ ركعات": 7, "٨ ركعات": 10}
    score += qiyam_points.get(qiyam_val, 0)

    # 4. Bonnes Actions
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

    # 5. Vendredi
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
# 📊 CHARGEMENT ET TRAITEMENT DONNÉES
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

# --- VÉRIFICATION ET AUTO-RÉPARATION ---
if not full_df.empty:
    missing_cols = [c for c in EXPECTED_HEADERS if c not in full_df.columns]
    
    if missing_cols:
        st.warning("⚠️ **Attention:** La structure du fichier Excel ne correspond pas à la mise à jour.")
        st.caption(f"Colonnes manquantes : {missing_cols}")
        
        if st.button("🔧 RÉPARER AUTOMATIQUEMENT (Clic unique)"):
            try:
                with st.spinner("Mise à jour des colonnes en cours..."):
                    sheet_data.update('A1', [EXPECTED_HEADERS])
                    st.success("✅ Réparation réussie ! Rechargement...")
                    time.sleep(2)
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")
        st.stop()
    else:
        # Calculs si tout va bien
        full_df['Score'] = full_df.apply(calculate_score, axis=1)
        full_df['DateObj'] = pd.to_datetime(full_df['التاريخ'], errors='coerce')
        
        # Filtrage par groupe
        if current_group == "الإدارة":
            group_df = full_df.copy()
        else:
            group_df = full_df[full_df['المجموعة'] == current_group].copy()

        # Stats Utilisateur
        if not group_df.empty:
            temp_leaderboard = group_df.groupby('الاسم')['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
            temp_leaderboard.insert(0, 'الترتيب', temp_leaderboard.index + 1)
            
            my_stats = temp_leaderboard[temp_leaderboard['الاسم'] == current_user]
            if not my_stats.empty:
                my_total_xp = my_stats.iloc[0]['Score']
                my_level = 1 + (int(my_total_xp) // 500)
                my_rank = my_stats.iloc[0]['الترتيب']

# ==========================================
# 🖥️ INTERFACE PRINCIPALE (UI)
# ==========================================

# En-tête avec bouton déconnexion
col_h1, col_h2 = st.columns([6, 1])
with col_h1:
    st.markdown(f"### 🚩 {current_group}")
    st.markdown(f"**Bienvenue, {current_user}**")
with col_h2:
    if st.button("Sortir", key="logout"):
        st.session_state["authenticated"] = False
        st.rerun()

# --- ZONE DE GLOIRE (KPIs) ---
st.markdown("<br>", unsafe_allow_html=True)
kpi1, kpi2, kpi3 = st.columns(3)
with kpi1: st.markdown(f"""<div class="metric-card"><h3>🥇 Rang</h3><h1>#{my_rank}</h1></div>""", unsafe_allow_html=True)
with kpi2: st.markdown(f"""<div class="metric-card"><h3>🛡️ Niveau</h3><h1>{my_level}</h1></div>""", unsafe_allow_html=True)
with kpi3: st.markdown(f"""<div class="metric-card"><h3>✨ Score</h3><h1>{my_total_xp}</h1></div>""", unsafe_allow_html=True)

# Barre de progression vers le niveau suivant
points_next = (my_level * 500) - my_total_xp
progress_val = max(0.0, min(1.0, 1 - (points_next / 500)))
st.markdown(f"<p style='text-align:center; margin-top:10px; color:#666;'>🚀 Encore <b>{points_next}</b> points pour le niveau suivant</p>", unsafe_allow_html=True)
st.progress(progress_val)

# --- NAVIGATION (Onglets) ---
st.markdown("<br>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["📝 Mon Journal", "🏆 Classement", "📈 Historique"])

# ==========================================
# TAB 1 : SAISIE (NOUVELLE ORGANISATION)
# ==========================================
with tab1:
    st.markdown("### 🤲 Remplir ma journée")
    
    # Détection Vendredi
    is_friday = datetime.today().weekday() == 4
    if is_friday:
        st.success("🕌 **C'est Vendredi !** N'oubliez pas Sourate Al-Kahf et la prière sur le Prophète.")

    with st.form("entry_form"):
        
        # BLOC A : PRIÈRES (Ouvert par défaut)
        with st.expander("🕌 الصلوات المفروضة (Prières Obligatoires)", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.caption("🌌 **Fajr**")
                inputs = {}
                inputs['fs'] = st.selectbox("Etat F", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="fs", label_visibility="collapsed")
                inputs['fsn'] = st.checkbox("Sunna", key="fsn")
            with c2:
                st.caption("☀️ **Dhuhr**")
                inputs['ds'] = st.selectbox("Etat D", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="ds", label_visibility="collapsed")
                inputs['dsn'] = st.checkbox("Sunna", key="dsn")
            with c3:
                st.caption("🌤️ **Asr**")
                inputs['as'] = st.selectbox("Etat A", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="as", label_visibility="collapsed")
            
            st.markdown("---")
            c4, c5, c6 = st.columns(3)
            with c4:
                st.caption("🌅 **Maghreb**")
                inputs['ms'] = st.selectbox("Etat M", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="ms", label_visibility="collapsed")
                inputs['msn'] = st.checkbox("Sunna", key="msn")
            with c5:
                st.caption("🌃 **Isha**")
                inputs['is_val'] = st.selectbox("Etat I", ["جماعة (مسجد)", "في الوقت (بيت)", "قضاء/فاتت"], key="is_val", label_visibility="collapsed")
                inputs['isn'] = st.checkbox("Sunna", key="isn")
            with c6:
                st.caption("☀️ **Duha**")
                st.markdown("<br>", unsafe_allow_html=True)
                inputs['duha'] = st.checkbox("Salat Duha", key="duha")

        # BLOC B : SPIRITUALITÉ
        with st.expander("📖 الروحانيات (Coran & Adhkar)", expanded=False):
            col_z1, col_z2 = st.columns(2)
            with col_z1:
                st.markdown("**📿 Adhkar**")
                inputs['az_m'] = st.checkbox("Matin (الصباح)")
                inputs['az_e'] = st.checkbox("Soir (المساء)")
                inputs['az_p'] = st.checkbox("Après Prière (دبر الصلاة)")
                inputs['az_s'] = st.checkbox("Avant dormir (النوم)")
                inputs['mulk'] = st.checkbox("S. Al-Mulk (الملك)")
            with col_z2:
                st.markdown("**🌙 Coran & Qiyam**")
                inputs['qiyam'] = st.select_slider("Qiyam (Nuit)", options=["0", "ركعتان", "٤ ركعات", "٦ ركعات", "٨ ركعات"])
                inputs['quran'] = st.select_slider("Lecture Coran", options=["0", "ثمن", "ربع", "نصف", "حزب", "حزبين"])
                
                if is_friday:
                    st.markdown("---")
                    cf1, cf2 = st.columns(2)
                    kahf = cf1.checkbox("S. Al-Kahf")
                    salat_nabi = cf2.checkbox("Salat Nabi")
                else:
                    kahf = False; salat_nabi = False

        # BLOC C : BONNES ACTIONS
        with st.expander("🌱 أعمال البر (Bonnes Actions)", expanded=False):
            b1, b2, b3, b4, b5 = st.columns(5)
            inputs['fasting'] = b1.checkbox("Jeûne")
            inputs['book_read'] = b2.checkbox("Lecture Livre")
            inputs['family'] = b3.checkbox("Famille")
            inputs['majlis_tadarus'] = b4.checkbox("Majlis")
            inputs['taahod'] = b5.checkbox("Engagement")

        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.form_submit_button("✅ ENREGISTRER MA JOURNÉE", use_container_width=True)

        if submit:
            day_date = datetime.now().strftime("%Y-%m-%d")
            
            # Vérification doublons
            is_duplicate = False
            if not full_df.empty:
                user_df = full_df[full_df['الاسم'] == current_user]
                if day_date in user_df['التاريخ'].astype(str).values:
                    is_duplicate = True
            
            if is_duplicate:
                st.error(f"⛔ Vous avez déjà enregistré une entrée pour aujourd'hui ({day_date}).")
            else:
                # Création de la ligne (Respect strict de l'ordre des colonnes)
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
                    "نعم" if inputs['book_read'] else "لا",
                    "نعم" if inputs['family'] else "لا", 
                    "نعم" if inputs['majlis_tadarus'] else "لا",
                    "نعم" if inputs['taahod'] else "لا",
                    "نعم" if kahf else "لا", "نعم" if salat_nabi else "لا"
                ]
                
                try:
                    with st.spinner("Enregistrement en cours..."):
                        sheet_data.append_row(row)
                        st.balloons()
                        st.success("✅ Enregistré avec succès ! Taqabbal Allah.")
                        time.sleep(2)
                        st.rerun()
                except Exception as e:
                    st.error(f"Erreur technique : {e}")

# ==========================================
# TAB 2 : CLASSEMENT
# ==========================================
with tab2:
    st.markdown("### 📊 Classement")
    
    target_group = current_group
    if current_group == "الإدارة":
        target_group = st.selectbox("🔍 Voir le groupe :", ["مجموعة الفردوس", "مجموعة الريان"])
    
    if not full_df.empty:
        display_df = full_df[full_df['المجموعة'] == target_group].copy()
    else:
        display_df = pd.DataFrame()

    t2_1, t2_2 = st.tabs(["🥇 Général", "📅 Hebdomadaire"])
    
    # Général
    with t2_1:
        if not display_df.empty and 'Score' in display_df.columns:
            gen_board = display_df.groupby('الاسم')['Score'].sum().reset_index().sort_values('Score', ascending=False).reset_index(drop=True)
            gen_board['Niveau'] = gen_board['Score'].apply(lambda x: get_level_and_rank(x)[0])
            gen_board['Titre'] = gen_board['Score'].apply(lambda x: get_level_and_rank(x)[1])
            gen_board.insert(0, 'Rang', gen_board.index + 1)
            
            st.dataframe(gen_board[['Rang', 'الاسم', 'Niveau', 'Score', 'Titre']], use_container_width=True, hide_index=True)
        else:
            st.info("Aucune donnée disponible.")

    # Hebdomadaire
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
                wk_board.insert(0, 'Rang', wk_board.index + 1)
                
                top_name = wk_board.iloc[0]['الاسم']
                top_score = wk_board.iloc[0]['Score']
                st.success(f"🏆 Champion de la semaine : **{top_name}** ({top_score} pts)")
                
                st.dataframe(wk_board[['Rang', 'الاسم', 'Score']], use_container_width=True, hide_index=True)
            else:
                st.info("Pas encore de données pour cette semaine.")
        else:
            st.info("Aucune donnée.")

# ==========================================
# TAB 3 : HISTORIQUE
# ==========================================
with tab3:
    st.markdown("### 📈 Mon Évolution")
    if not full_df.empty and current_user in full_df['الاسم'].values and 'Score' in full_df.columns:
        my_hist = full_df[full_df['الاسم'] == current_user].copy()
        
        # Tri chronologique pour le graphique
        my_hist = my_hist.dropna(subset=['DateObj']).sort_values(by='DateObj')
        my_hist.set_index('DateObj', inplace=True)
        
        st.caption("Progression de vos points jour par jour")
        st.line_chart(my_hist['Score'])
        
        st.markdown("#### Détails")
        st.dataframe(my_hist.drop(columns=['Score'], errors='ignore').reset_index(drop=True), use_container_width=True)
    else:
        st.info("Aucun historique trouvé.")
