import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import time
import altair as alt # Pour des graphiques avancés

# ==========================================
# 1. CONFIGURATION & DESIGN GAMIFIÉ
# ==========================================
st.set_page_config(page_title="Sabaq Al-Salihin", page_icon="🕌", layout="wide", initial_sidebar_state="collapsed")

# Palette de couleurs "Jeu"
COLOR_PRIMARY = "#009688"
COLOR_ACCENT = "#FFD700" # Or pour les trophées
COLOR_DANGER = "#FF5252"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Cairo', sans-serif; direction: rtl; }}
    
    /* CARTES DE STATS */
    .game-card {{
        background: white;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
        border-bottom: 4px solid {COLOR_PRIMARY};
        transition: transform 0.2s;
    }}
    .game-card:hover {{ transform: scale(1.02); }}
    .game-card h3 {{ color: #7f8c8d; font-size: 0.9em; margin: 0; }}
    .game-card .value {{ color: {COLOR_PRIMARY}; font-size: 1.8em; font-weight: bold; }}
    
    /* BADGE NIVEAU */
    .level-badge {{
        background: linear-gradient(45deg, #FFD700, #FFA500);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }}

    /* BARRE DE PROGRESSION */
    .stProgress > div > div > div > div {{
        background-color: {COLOR_PRIMARY};
    }}
    
    /* BOUTONS */
    .stButton>button {{
        background: linear-gradient(135deg, {COLOR_PRIMARY} 0%, #00796b 100%);
        color: white !important;
        border-radius: 12px;
        font-weight: bold;
        border: none;
        height: 50px;
        width: 100%;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SYSTÈME DE POINTS (LE MOTEUR DU JEU)
# ==========================================
# C'est ici qu'on définit les règles du jeu
SCORING_RULES = {
    "Fajr": {"Mosquée": 50, "Heure": 30, "Retard": 5, "Raté": -20}, # Punition sévère
    "Prieres": {"Mosquée": 20, "Heure": 15, "Retard": 5, "Raté": -10},
    "Coran": {"Hizb": 30, "Demi-Hizb": 20, "Lecture": 10, "0": 0},
    "Qiyam": {"Long": 40, "Court": 20, "0": 0},
    "Bonus": 10, # Pour les Sunan
    "Jeune": 100
}

GROUPS_CONFIG = {
    "مجموعة السائرين": "Saerin@2025",
    "الإدارة": "Admin@MasterKey99!"
}

# Colonnes du fichier Excel
HEADERS = [
    "Date", "Nom", "Pin", "Groupe",
    "Fajr", "Dhuhr", "Asr", "Maghreb", "Isha",
    "Sunan_Rawatib", "Adhkar", "Quran", "Qiyam", "Jeune",
    "Score_Jour", "Score_Total"
]

# ==========================================
# 3. CONNEXION
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
        else: st.error("❌ Credentials manquants."); st.stop()
        return gspread.authorize(creds)
    except: st.error("Erreur connexion"); st.stop()

client = get_client()
# REMPLACEZ PAR VOTRE LIEN
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1XqSb4DmiUEd-mt9WMlVPTow7VdeYUI2O870fsgrZx-0/edit?gid=0#gid=0"
try:
    sh = client.open_by_url(spreadsheet_url)
    sheet_data = sh.get_worksheet(0)
except: st.error("Erreur accès feuille"); st.stop()

# ==========================================
# 4. LOGIQUE MÉTIER
# ==========================================
if "auth" not in st.session_state: st.session_state["auth"] = False

def check_login():
    u = str(st.session_state.login_user).strip()
    p = str(st.session_state.login_pin).strip()
    pwd = str(st.session_state.login_pass).strip()
    
    grp = next((g for g, pw in GROUPS_CONFIG.items() if pw == pwd), None)
    if grp and u and p:
        st.session_state.update({"auth": True, "user": u, "pin": p, "grp": grp})
    else: st.error("Données incorrectes")

def calculate_daily_points(data):
    score = 0
    
    # Fajr
    fajr_status = data.get("Fajr")
    if fajr_status == "🕌 جماعة (Mosquée)": score += SCORING_RULES["Fajr"]["Mosquée"]
    elif fajr_status == "🏠 في الوقت (Heure)": score += SCORING_RULES["Fajr"]["Heure"]
    elif fajr_status == "⏰ قضاء (Retard)": score += SCORING_RULES["Fajr"]["Retard"]
    else: score += SCORING_RULES["Fajr"]["Raté"] # Pénalité

    # Autres prières
    for p in ["Dhuhr", "Asr", "Maghreb", "Isha"]:
        stat = data.get(p)
        if stat == "🕌 جماعة": score += SCORING_RULES["Prieres"]["Mosquée"]
        elif stat == "🏠 في الوقت": score += SCORING_RULES["Prieres"]["Heure"]
        elif stat == "⏰ قضاء": score += SCORING_RULES["Prieres"]["Retard"]
        else: score += SCORING_RULES["Prieres"]["Raté"] # Pénalité

    # Bonus / Malus autres actions
    if data.get("Sunan_Rawatib"): score += SCORING_RULES["Bonus"]
    if data.get("Adhkar"): score += SCORING_RULES["Bonus"]
    
    quran = data.get("Quran")
    if "Hizb" in quran: score += SCORING_RULES["Coran"]["Hizb"]
    elif "Lecture" in quran: score += SCORING_RULES["Coran"]["Lecture"]
    
    if data.get("Qiyam"): score += SCORING_RULES["Qiyam"]["Long"]
    if data.get("Jeune"): score += SCORING_RULES["Jeune"]

    return score

def get_rank_badge(total_score):
    if total_score < 500: return "🌱 Débutant", 500
    elif total_score < 1500: return "🛡️ Soldat", 1500
    elif total_score < 3000: return "⚔️ Combattant", 3000
    elif total_score < 5000: return "👑 Commandant", 5000
    else: return "💎 Légende", 10000

# ==========================================
# 5. PAGE LOGIN
# ==========================================
if not st.session_state["auth"]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><h1 style='text-align:center; color:#009688;'>⚔️ سباق الصالحين</h1><p style='text-align:center'>Le RPG spirituel</p>", unsafe_allow_html=True)
        st.text_input("Pseudo (Nom):", key="login_user")
        st.text_input("Code Pin:", type="password", key="login_pin")
        st.text_input("Code Groupe:", type="password", key="login_pass")
        st.button("🎮 Commencer", on_click=check_login)
    st.stop()

# ==========================================
# 6. CHARGEMENT DONNÉES
# ==========================================
c_user = st.session_state["user"]
c_pin = st.session_state["user"] # Simplification pour demo
c_grp = st.session_state["grp"]

try:
    data = sheet_data.get_all_records()
    df = pd.DataFrame(data)
except: df = pd.DataFrame(columns=HEADERS)

# Nettoyage
if not df.empty:
    for col in HEADERS: 
        if col not in df.columns: df[col] = ""
    df['Score_Jour'] = pd.to_numeric(df['Score_Jour'], errors='coerce').fillna(0)
    df['DateObj'] = pd.to_datetime(df['Date'], errors='coerce')

# ==========================================
# 7. INTERFACE PRINCIPALE
# ==========================================
col_h1, col_h2 = st.columns([6, 1])
with col_h1: st.markdown(f"### 🏰 {c_grp} | Joueur: **{c_user}**")
with col_h2: 
    if st.button("Déconnexion"):
        st.session_state["auth"] = False
        st.rerun()

# --- ADMIN DASHBOARD ---
if c_grp == "الإدارة":
    st.markdown("## 👮‍♂️ Tour de Contrôle (Admin)")
    
    if df.empty:
        st.warning("Aucune donnée disponible.")
    else:
        # 1. Vue Globale
        st.markdown("### 📊 Classement Général")
        leaderboard = df.groupby('Nom')['Score_Jour'].sum().sort_values(ascending=False).reset_index()
        leaderboard.columns = ['Joueur', 'Score Total']
        st.dataframe(leaderboard, use_container_width=True)

        # 2. Surveillance Individuelle (Drill-down)
        st.markdown("---")
        st.markdown("### 🕵️‍♂️ Surveillance de l'Évolution")
        
        users = df['Nom'].unique().tolist()
        selected_user = st.selectbox("Sélectionner un joueur à analyser :", users)
        
        if selected_user:
            user_data = df[df['Nom'] == selected_user].sort_values('DateObj')
            
            # Graphique d'évolution
            chart = alt.Chart(user_data).mark_line(point=True).encode(
                x='DateObj:T',
                y='Score_Jour:Q',
                tooltip=['Date', 'Score_Jour']
            ).properties(title=f"Performance quotidienne de {selected_user}")
            
            st.altair_chart(chart, use_container_width=True)
            
            # Détails des fautes (Pénalités)
            st.markdown("#### ⚠️ Analyse des faiblesses")
            missed_fajr = len(user_data[user_data['Fajr'].str.contains("Raté|Retard")])
            st.write(f"🛑 Fajr ratés/retard : **{missed_fajr}** fois")

# --- USER DASHBOARD ---
else:
    # --- CALCUL STATS JOUEUR ---
    my_total_score = 0
    if not df.empty:
        my_data = df[(df['Nom'] == c_user)]
        my_total_score = my_data['Score_Jour'].sum()
    
    badge_name, next_level_score = get_rank_badge(my_total_score)
    progress_pct = min(1.0, my_total_score / next_level_score)

    # HEADER GAMIFIÉ
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"<div class='game-card'><h3>Niveau Actuel</h3><div class='level-badge'>{badge_name}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='game-card'><h3>Score Total XP</h3><div class='value'>{int(my_total_score)}</div></div>", unsafe_allow_html=True)
    with c3: 
        # Calcul Rang Jour
        today_str = datetime.now().strftime("%Y-%m-%d")
        if not df.empty:
            daily_df = df[df['Date'] == today_str]
            if not daily_df.empty:
                ranks = daily_df.groupby('Nom')['Score_Jour'].sum().sort_values(ascending=False).reset_index()
                if c_user in ranks['Nom'].values:
                    my_daily_rank = ranks[ranks['Nom'] == c_user].index[0] + 1
                    rank_display = f"#{my_daily_rank}"
                else: rank_display = "-"
            else: rank_display = "-"
        else: rank_display = "-"
        st.markdown(f"<div class='game-card'><h3>Classement Jour</h3><div class='value'>{rank_display}</div></div>", unsafe_allow_html=True)

    st.markdown(f"**Progression vers le prochain rang :**")
    st.progress(progress_pct)
    
    # ONGLETS
    tab1, tab2, tab3 = st.tabs(["🎮 Jouer (Enregistrer)", "🏆 Classement du Jour", "📜 Mon Histoire"])

    with tab1:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Vérification si déjà joué
        has_played = False
        if not df.empty:
            if not df[(df['Nom'] == c_user) & (df['Date'] == today)].empty:
                has_played = True
        
        if has_played:
            st.success(f"✅ Mission du jour ({today}) accomplie ! Reviens demain pour plus d'XP.")
        else:
            with st.form("game_form"):
                st.markdown("### 📝 Rapport de Mission")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**🕌 La Prière de l'Aube (Fajr)**")
                    fajr = st.selectbox("État", ["🕌 جماعة (Mosquée)", "🏠 في الوقت (Heure)", "⏰ قضاء (Retard)", "❌ فات (Raté)"], key="fajr")
                    st.caption("⚠️ Rater le Fajr enlève 20 points !")
                
                with c2:
                    st.markdown("**📖 Le Saint Coran**")
                    quran = st.selectbox("Lecture", ["0", "Lecture", "Demi-Hizb", "Hizb"], key="quran")

                st.markdown("---")
                st.markdown("**⚔️ Les 4 Piliers (Dhuhr, Asr, Maghreb, Isha)**")
                cols = st.columns(4)
                prayers_res = {}
                for idx, p in enumerate(["Dhuhr", "Asr", "Maghreb", "Isha"]):
                    prayers_res[p] = cols[idx].selectbox(p, ["🕌 جماعة", "🏠 في الوقت", "⏰ قضاء", "❌ فات"], label_visibility="collapsed")

                st.markdown("---")
                st.markdown("**🛡️ Bonus & Quêtes Secondaires**")
                cc1, cc2, cc3 = st.columns(3)
                sunan = cc1.checkbox("Sunan Rawatib (+10 XP)")
                adhkar = cc2.checkbox("Adhkar Matin/Soir (+10 XP)")
                qiyam = cc3.checkbox("Qiyam Layl (+40 XP)")
                jeune = st.checkbox("Jeûne aujourd'hui (+100 XP !!)")

                submit = st.form_submit_button("🔥 Valider mes actions")
            
            if submit:
                # Préparer les données
                row_data = {
                    "Fajr": fajr, "Dhuhr": prayers_res["Dhuhr"], "Asr": prayers_res["Asr"],
                    "Maghreb": prayers_res["Maghreb"], "Isha": prayers_res["Isha"],
                    "Sunan_Rawatib": sunan, "Adhkar": adhkar, "Quran": quran,
                    "Qiyam": qiyam, "Jeune": jeune
                }
                
                day_score = calculate_daily_points(row_data)
                
                # Sauvegarde
                new_row = [
                    today, c_user, "123", c_grp, # Pin simplifié
                    fajr, prayers_res["Dhuhr"], prayers_res["Asr"], prayers_res["Maghreb"], prayers_res["Isha"],
                    "Oui" if sunan else "Non", "Oui" if adhkar else "Non", quran, "Oui" if qiyam else "Non", "Oui" if jeune else "Non",
                    day_score, 0 # Placeholder pour total
                ]
                
                try:
                    sheet_data.append_row(new_row)
                    st.balloons()
                    
                    # Feedback Gamifié
                    if day_score > 100: msg = "🔥 INCROYABLE ! Performance Légendaire !"
                    elif day_score > 50: msg = "✨ Excellent travail, continue !"
                    elif day_score > 0: msg = "👍 Bien joué, mais tu peux faire mieux."
                    else: msg = "⚠️ Attention ! Score négatif. Reprends-toi demain !"
                    
                    st.success(f"{msg} (Score: {day_score} XP)")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur réseau: {e}")

    with tab2:
        st.markdown(f"### 🏆 Podiums du Jour ({datetime.now().strftime('%d/%m')})")
        if not df.empty:
            today_str = datetime.now().strftime("%Y-%m-%d")
            daily_df = df[df['Date'] == today_str]
            
            if not daily_df.empty:
                ranking = daily_df[['Nom', 'Score_Jour']].sort_values('Score_Jour', ascending=False).reset_index(drop=True)
                ranking.index += 1
                st.dataframe(ranking, use_container_width=True)
                
                # Le vainqueur
                winner = ranking.iloc[0]
                st.info(f"🥇 Champion du jour : **{winner['Nom']}** avec {winner['Score_Jour']} XP !")
            else:
                st.info("Personne n'a encore enregistré aujourd'hui. Sois le premier !")
        else: st.info("Aucune donnée.")

    with tab3:
        st.markdown("### 📜 Ton Évolution")
        if not df.empty and not df[df['Nom'] == c_user].empty:
            my_hist = df[df['Nom'] == c_user].sort_values('DateObj')
            
            # Graphique d'évolution
            st.area_chart(my_hist.set_index('DateObj')['Score_Jour'], color=COLOR_PRIMARY)
            
            st.markdown("#### Historique Détaillé")
            st.dataframe(my_hist[['Date', 'Score_Jour', 'Fajr', 'Quran']].sort_values('Date', ascending=False), use_container_width=True)
