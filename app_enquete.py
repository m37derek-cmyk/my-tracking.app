import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

def get_gspread_client():
    json_path = r"c:\Users\darka\Downloads\my-project-enquete-490718-7b1be08f8312.json"
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1oOAu3a1lIhlau74RY5wbFj1jMjspX0X7HJt9g_gj66Y/edit?gid=0#gid=0"
    
    if not SHEET_URL:
        st.error("⚠️ URL du Google Sheet non configurée !")
        return None, None
        
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = None
        import os
        
        if "gcp_service_account" in st.secrets:
            try:
                credentials_dict = dict(st.secrets["gcp_service_account"])
                if "\\n" in credentials_dict.get("private_key", ""):
                    credentials_dict["private_key"] = credentials_dict["private_key"].replace("\\n", "\n")
                credentials = Credentials.from_service_account_info(
                    credentials_dict, scopes=scopes
                )
            except Exception as e:
                st.warning(f"Impossible de lire vos secrets (format invalide). Raison : {e}")
                
        if credentials is None:
            fichier_json_local = "my-project-enquete-490718-7b1be08f8312.json"
            if os.path.exists(fichier_json_local):
                credentials = Credentials.from_service_account_file(fichier_json_local, scopes=scopes)
            elif os.path.exists(json_path):
                credentials = Credentials.from_service_account_file(json_path, scopes=scopes)
            else:
                st.error(f"Fichier secret introuvable. Placez le fichier {fichier_json_local} dans votre répertoire GitHub.")
                return None, None
                
        gc = gspread.authorize(credentials)
        sh = gc.open_by_url(SHEET_URL)
        return gc, sh
    except Exception as e:
        st.error(f"Erreur d'authentification Google Sheets : {e}")
        return None, None

def exporter_vers_gsheets(data, dfs, data_exploitation=None):
    gc, sh = get_gspread_client()
    if sh is None:
        return
        
    try:
        import time
        
        import time
        
        def retry_api(func, *args, **kwargs):
            """Exécute un appel API GSheets avec backoff exponentiel pour éviter l'erreur 429."""
            max_retries = 5
            for i in range(max_retries):
                try:
                    res = func(*args, **kwargs)
                    time.sleep(1.5) # Pause systémique après chaque écriture réussie
                    return res
                except Exception as e:
                    if "429" in str(e) or "Quota" in str(e):
                        if i < max_retries - 1:
                            time.sleep((2 ** i) + 2)
                        else:
                            raise e
                    else:
                        raise e

        def formater_onglet(onglet):
            try:
                retry_api(onglet.freeze, rows=1)
                retry_api(onglet.format, "A1:AZ1", {
                    "backgroundColor": {"red": 0.15, "green": 0.45, "blue": 0.3},
                    "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True}
                })
            except Exception:
                pass # Erreur de formatage non critique
        
        def ecrire_plate(nom_onglet, dictionnaire):
            try:
                onglet = retry_api(sh.worksheet, nom_onglet)
                header_exists = len(retry_api(onglet.get, 'A1:B1')) > 0
            except gspread.exceptions.WorksheetNotFound:
                onglet = retry_api(sh.add_worksheet, title=nom_onglet, rows="1000", cols="50")
                header_exists = False
                
            if not header_exists:
                try:
                    retry_api(onglet.update, 'A1', [list(dictionnaire.keys())])
                except Exception:
                    retry_api(onglet.append_row, list(dictionnaire.keys()))
                formater_onglet(onglet)
                
            rows_to_insert = [[str(v) for v in dictionnaire.values()]]
            retry_api(onglet.append_rows, rows_to_insert)
                
        def ecrire_df(nom_onglet, df, code_fiche):
            if df is None or df.empty: return
            
            try:
                onglet = retry_api(sh.worksheet, nom_onglet)
                header_exists = len(retry_api(onglet.get, 'A1:B1')) > 0
            except gspread.exceptions.WorksheetNotFound:
                onglet = retry_api(sh.add_worksheet, title=nom_onglet, rows="1000", cols="50")
                header_exists = False
                
            df_to_save = df.copy()
            df_to_save.insert(0, 'Code fiche', code_fiche)
            
            if not header_exists:
                try:
                    retry_api(onglet.update, 'A1', [df_to_save.columns.tolist()])
                except Exception:
                    retry_api(onglet.append_row, df_to_save.columns.tolist())
                formater_onglet(onglet)
                
            rows_to_insert = []
            valeurs = df_to_save.astype(str).values.tolist()
            for row in valeurs:
                if any(str(v).strip() != "" and str(v).strip() != "0.0" and str(v).strip() != "0" and str(v).strip() != "nan" for v in row[1:]):
                    rows_to_insert.append(row)
            
            if len(rows_to_insert) > 0:
                retry_api(onglet.append_rows, rows_to_insert)

        with st.spinner("Synchronisation avec Google Sheets en cours..."):
            ecrire_plate("Global", data)
            
            # Onglet dédié pour l'identification de l'exploitation
            if data_exploitation:
                ecrire_plate("Identification Exploitation", data_exploitation)
            
            ecrire_df("Bloc B - Variétés Framb", dfs.get("framboisier"), code_fiche)
            ecrire_df("Bloc B - Variétés Myrti", dfs.get("myrtillier"), code_fiche)
            ecrire_df("Bloc B - Variétés Mûrier", dfs.get("murier"), code_fiche)
            ecrire_df("Bloc B - Substrat", dfs.get("substrat"), code_fiche)
            
            ecrire_df("Bloc D - Eau", dfs.get("eau"), code_fiche)
            ecrire_df("Bloc D - Volumes", dfs.get("volumes"), code_fiche)
            
            # BLOC E Framboisier
            if "Framboisier" in cultures:
                ecrire_df("Bloc E - Fertigation Framb", dfs.get("fert_framb"), code_fiche)
                ecrire_df("Bloc E - Engrais Framb", dfs.get("eng_framb"), code_fiche)
                ecrire_df("Bloc E - Foliaires Framb", dfs.get("fol_framb"), code_fiche)
            
            # BLOC E Myrtillier
            if "Myrtillier" in cultures:
                ecrire_df("Bloc E - Fertigation Myrti", dfs.get("fert_myrt"), code_fiche)
                ecrire_df("Bloc E - Engrais Myrti", dfs.get("eng_myrt"), code_fiche)
                ecrire_df("Bloc E - Foliaires Myrti", dfs.get("fol_myrt"), code_fiche)
                
            # BLOC E Mûrier
            if "Mûrier" in cultures:
                ecrire_df("Bloc E - Fertigation Mûrier", dfs.get("fert_mur"), code_fiche)
                ecrire_df("Bloc E - Engrais Mûrier", dfs.get("eng_mur"), code_fiche)
                ecrire_df("Bloc E - Foliaires Mûrier", dfs.get("fol_mur"), code_fiche)
            
            # BLOC G et H Framboisier
            if "Framboisier" in cultures:
                ecrire_df("Bloc G - Phyto Framb", dfs.get("phyto_framb"), code_fiche)
                ecrire_df("Bloc G - Trait. Framb", dfs.get("trait_framb"), code_fiche)
                ecrire_df("Bloc G - Auxil. Framb", dfs.get("aux_framb"), code_fiche)
                ecrire_df("Bloc H - Rdt Framb", dfs.get("rend_framb"), code_fiche)
            
            # BLOC G et H Myrtillier
            if "Myrtillier" in cultures:
                ecrire_df("Bloc G - Phyto Myrti", dfs.get("phyto_myrt"), code_fiche)
                ecrire_df("Bloc G - Trait. Myrti", dfs.get("trait_myrt"), code_fiche)
                ecrire_df("Bloc G - Auxil. Myrti", dfs.get("aux_myrt"), code_fiche)
                ecrire_df("Bloc H - Rdt Myrti", dfs.get("rend_myrt"), code_fiche)
                
            # BLOC G et H Mûrier
            if "Mûrier" in cultures:
                ecrire_df("Bloc G - Phyto Mûrier", dfs.get("phyto_mur"), code_fiche)
                ecrire_df("Bloc G - Trait. Mûrier", dfs.get("trait_mur"), code_fiche)
                ecrire_df("Bloc G - Auxil. Mûrier", dfs.get("aux_mur"), code_fiche)
                ecrire_df("Bloc H - Rdt Mûrier", dfs.get("rend_mur"), code_fiche)
            
            ecrire_df("Bloc J - Personnel", dfs.get("personnel"), code_fiche)
            ecrire_df("Bloc J - JT", dfs.get("jt"), code_fiche)
            
            ecrire_df("Bloc M - Axes", dfs.get("axes"), code_fiche)

        st.success("✅ Données synchronisées avec Google Sheets !")
        
    except Exception as e:
        st.error(f"Erreur lors de la synchronisation GSheets: {e}")

st.set_page_config(
    page_title="Enquête Terrain - Fruits Rouges",
    page_icon="🍓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ═══════════════════════════════════════════════════════════════
# CUSTOM CSS - Professional Theme
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
    /* ─── Google Fonts ─── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&display=swap');

    /* ─── Root Variables ─── */
    :root {
        --primary: #1B6B3A;
        --primary-light: #2D8F4E;
        --primary-dark: #0F4D28;
        --accent: #E8453C;
        --accent-light: #FF6B63;
        --bg-dark: #F8FAFC;          /* Light gray main background */
        --bg-card: #FFFFFF;          /* Pure white cards */
        --bg-card-hover: #F1F5F9;
        --surface: #FFFFFF;
        --text-primary: #1E293B;     /* Deep slate for clear reading */
        --text-secondary: #64748B;   /* Neutral slate for secondary texts */
        --border: #E2E8F0;           /* Soft border */
        --border-hover: #CBD5E1;
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.05);
        --shadow-md: 0 4px 6px rgba(0,0,0,0.05);
        --shadow-lg: 0 10px 15px rgba(0,0,0,0.05);
        --gradient-primary: linear-gradient(135deg, #1B6B3A 0%, #2D8F4E 50%, #1B6B3A 100%);
        --gradient-accent: linear-gradient(135deg, #E8453C 0%, #FF6B63 100%);
        --gradient-hero: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 50%, #F0FDF4 100%); /* Very light refreshing green */
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --radius-xl: 20px;
    }

    /* ─── Global Reset ─── */
    .stApp {
        background: var(--bg-dark) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--text-primary) !important;
    }

    /* ─── Scrollbar ─── */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: var(--bg-dark); }
    ::-webkit-scrollbar-thumb { background: var(--primary); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--primary-light); }

    /* ─── Main Container ─── */
    .block-container {
        padding: 2rem 3rem 4rem !important;
        max-width: 1400px !important;
    }

    /* ─── Hero Card ─── */
    .hero-container {
        background: var(--gradient-hero);
        border-radius: var(--radius-xl);
        padding: 2.5rem 3rem;
        margin-bottom: 2rem;
        border: 1px solid var(--border);
        position: relative;
        overflow: hidden;
        box-shadow: var(--shadow-lg);
    }
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(45,143,78,0.15) 0%, transparent 70%);
        border-radius: 50%;
        animation: pulse-glow 6s ease-in-out infinite;
    }
    .hero-container::after {
        content: '';
        position: absolute;
        bottom: -30%;
        left: -10%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(232,69,60,0.08) 0%, transparent 70%);
        border-radius: 50%;
        animation: pulse-glow 8s ease-in-out infinite reverse;
    }
    @keyframes pulse-glow {
        0%, 100% { transform: scale(1); opacity: 0.6; }
        50% { transform: scale(1.15); opacity: 1; }
    }
    .hero-title {
        font-family: 'Outfit', sans-serif !important;
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #0F4D28 0%, #1B6B3A 100%); /* Dark green gradient for text */
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.3rem;
        position: relative;
        z-index: 1;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #166534; /* Darker green for subtitle reading clearly on light background */
        font-weight: 400;
        position: relative;
        z-index: 1;
        letter-spacing: 0.3px;
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #FFFFFF;
        border: 1px solid rgba(45, 143, 78, 0.3);
        border-radius: 50px;
        padding: 6px 16px;
        font-size: 0.8rem;
        color: #15803D;
        font-weight: 600;
        margin-top: 1rem;
        position: relative;
        z-index: 1;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* ─── Info Cards ─── */
    .info-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: var(--shadow-sm);
    }
    .info-card:hover {
        border-color: var(--border-hover);
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }
    .info-card-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1rem;
        font-weight: 600;
        color: var(--primary-light);
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* ─── Section Headers (st.header / st.subheader) ─── */
    h1 {
        font-family: 'Outfit', sans-serif !important;
        color: var(--text-primary) !important;
        font-weight: 700 !important;
        letter-spacing: -0.3px !important;
    }
    h2 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1.6rem !important;
        color: var(--text-primary) !important;
        padding-bottom: 0.5rem !important;
        border-bottom: 2px solid var(--border) !important;
        margin-top: 1rem !important;
    }
    h3 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        font-size: 1.15rem !important;
        color: var(--primary-light) !important;
        margin-top: 1rem !important;
    }
    p, span, label, .stMarkdown {
        font-family: 'Inter', sans-serif !important;
    }

    /* ─── Tabs ─── */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--bg-card);
        border-radius: var(--radius-lg);
        padding: 6px;
        gap: 4px;
        border: 1px solid var(--border);
        overflow-x: auto;
        box-shadow: var(--shadow-sm);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-md) !important;
        padding: 10px 18px !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        font-family: 'Inter', sans-serif !important;
        color: var(--text-secondary) !important;
        background: transparent !important;
        border: none !important;
        transition: all 0.25s ease !important;
        white-space: nowrap !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(45, 143, 78, 0.1) !important;
        color: var(--primary-light) !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--gradient-primary) !important;
        color: white !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 12px rgba(27, 107, 58, 0.4) !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }

    /* ─── Inputs (text, number, date, selectbox, multiselect) ─── */
    .stTextInput > div > div,
    .stNumberInput > div > div > input,
    .stDateInput > div > div,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s ease !important;
    }
    .stTextInput > div > div:focus-within,
    .stNumberInput > div > div:focus-within,
    .stDateInput > div > div:focus-within,
    .stSelectbox > div > div:focus-within,
    .stMultiSelect > div > div:focus-within {
        border-color: var(--primary-light) !important;
        box-shadow: 0 0 0 3px rgba(45, 143, 78, 0.15) !important;
    }
    .stTextInput input,
    .stNumberInput input {
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextInput label,
    .stNumberInput label,
    .stDateInput label,
    .stSelectbox label,
    .stMultiSelect label {
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* ─── Radio Buttons ─── */
    .stRadio > label {
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
    }
    .stRadio [data-baseweb="radio"] {
        background: transparent !important;
    }
    .stRadio div[role="radiogroup"] label {
        color: var(--text-primary) !important;
        font-weight: 400 !important;
    }

    /* ─── Buttons ─── */
    .stButton > button {
        background: var(--gradient-primary) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        padding: 0.7rem 2.5rem !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.3px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(27, 107, 58, 0.3) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 25px rgba(27, 107, 58, 0.5) !important;
        filter: brightness(1.1) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* ─── Data Editor ─── */
    .stDataFrame, [data-testid="stDataEditor"] {
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--border) !important;
        overflow: hidden;
    }
    [data-testid="stDataEditor"] [data-testid="glide-cell"] {
        font-family: 'Inter', sans-serif !important;
    }

    /* ─── Dividers ─── */
    hr {
        border-color: var(--border) !important;
        margin: 1.5rem 0 !important;
    }

    /* ─── Success / Warning / Error messages ─── */
    .stSuccess {
        background: rgba(45, 143, 78, 0.1) !important;
        border-left: 4px solid var(--primary) !important;
        border-radius: var(--radius-sm) !important;
    }
    .stWarning {
        background: rgba(255, 193, 7, 0.1) !important;
        border-left: 4px solid #FFC107 !important;
        border-radius: var(--radius-sm) !important;
    }
    .stError {
        background: rgba(232, 69, 60, 0.1) !important;
        border-left: 4px solid var(--accent) !important;
        border-radius: var(--radius-sm) !important;
    }

    /* ─── Spinner ─── */
    .stSpinner > div > div {
        border-top-color: var(--primary) !important;
    }

    /* ─── Column gaps ─── */
    [data-testid="column"] {
        padding: 0 0.5rem !important;
    }

    /* ─── Expander ─── */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-primary) !important;
        font-weight: 500 !important;
    }

    /* ─── JSON display ─── */
    .stJson {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
    }

    /* ─── Multiselect tags ─── */
    .stMultiSelect [data-baseweb="tag"] {
        background: rgba(45, 143, 78, 0.2) !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
        color: var(--primary-light) !important;
    }

    /* ─── Sidebar (if ever expanded) ─── */
    [data-testid="stSidebar"] {
        background: var(--bg-card) !important;
        border-right: 1px solid var(--border) !important;
    }

    /* ─── Hide Streamlit branding ─── */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)



# ═══════════════════════════════════════════════════════════════
# VUE UTILISATEUR (FORMULAIRE D'ENQUÊTE)
# ═══════════════════════════════════════════════════════════════

# HERO HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero-container">
    <div class="hero-title">🍓 Questionnaire d'Enquête Terrain</div>
    <div class="hero-subtitle">Élaboration d'un Référentiel Technique de Production des Fruits Rouges</div>
    <div class="hero-badge">
        <span>📋</span>
        <span>Souss-Massa — Campagne 2025/2026</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# INFORMATIONS GÉNÉRALES (above all tabs)
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<div class="info-card">
    <div class="info-card-title">📌 Informations Générales de l'Enquête</div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    code_fiche = st.text_input("🏷️ Code fiche")
    date_enquete = st.date_input("📅 Date enquête", value=date.today())
    enqueteur = st.text_input("👤 Enquêteur")

with col2:
    cultures = st.multiselect("🌱 Culture(s) enquêtée(s)", ["Framboisier", "Myrtillier", "Mûrier"])
    duree = st.number_input("⏱️ Durée (h)", min_value=0.0, step=0.5)

# --- Initialisation par défaut (évite les NameError pour variables manquantes dans UI) ---
ift_fong_framb = ift_ins_framb = ift_tot_framb = cout_phyto_framb = 0.0
ift_fong_myrt = ift_ins_myrt = ift_tot_myrt = cout_phyto_myrt = 0.0
ift_fong_mur = ift_ins_mur = ift_tot_mur = cout_phyto_mur = 0.0
# ----------------------------------------------------------------------------------------

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# TABS — Navigation par bloc
# ═══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
    "🏠 A · Identification",
    "🌿 B · Matériel Végétal",
    "🏗️ C · Infrastructure",
    "💧 D · Irrigation",
    "🧪 E · Fertigation",
    "✂️ F · Taille & Conduite",
    "🛡️ G · Protection",
    "📦 H · Récolte",
    "❄️ I · Post-Récolte",
    "👷 J · Main-d'Œuvre",
    "📊 M · Standardisation"
])


with tab1:
    st.markdown('<div class="info-card"><div class="info-card-title">🏠 BLOC A — Identification de l\'Exploitation et du Producteur</div></div>', unsafe_allow_html=True)

    st.subheader("Q1. Informations de l'enquêté")
    col3, col4 = st.columns(2)
with col3:
    nom_prenom = st.text_input("Nom & Prénom")
    email = st.text_input("Email")
    telephone = st.text_input("Téléphone")
    fonction = st.selectbox("Fonction", ["Propriétaire", "Directeur technique", "Chef de culture", "Technicien"])

with col4:
    formation = st.selectbox("Formation", ["Sans formation", "Technicien agricole", "Ingénieur agronome", "Autre"])
    formation_autre = ""
    if formation == "Autre":
        formation_autre = st.text_input("Précisez la formation")
    experience = st.number_input("Expérience en fruits rouges (ans)", min_value=0, step=1)

st.subheader("Q2. Identification de l'exploitation")
col5, col6 = st.columns(2)
with col5:
    nom_exploitation = st.text_input("Nom exploitation")
    commune = st.text_input("Commune / Douar")
    zone = st.selectbox("Zone", ["Ait Amira", "Biougra", "Belfaa-Massa", "Sidi Bibi", "Oulad Teima", "Tifnit", "Autre"])
    zone_autre = ""
    if zone == "Autre":
        zone_autre = st.text_input("Précisez la zone")

with col6:
    reseau = st.selectbox("Réseau commercial", ["Driscoll's", "Atlas Farming", "Coopérative", "Indépendant", "Autre"])
    reseau_autre = ""
    if reseau == "Autre":
        reseau_autre = st.text_input("Précisez le réseau (lequel)")

st.subheader("Q3. Certifications détenues")
certifications = st.multiselect(
    "Certifications", 
    ["GlobalG.A.P.", "BRCGS Food Safety", "SMETA / GRASP", "Aucune", "En cours d'obtention"]
)

col7, col8 = st.columns(2)
with col7:
    date_audit = st.date_input("Dernière date d'audit", value=date.today())
with col8:
    organisme_certif = st.text_input("Organisme certificateur")

st.subheader("Q4. Consentement")
consentement = st.radio("Consentement à l'utilisation des données pour le référentiel technique", ["Oui", "Non"])

with tab2:
    st.markdown('<div class="info-card"><div class="info-card-title">🌿 BLOC B — Matériel Végétal, Variétés et Implantation</div></div>', unsafe_allow_html=True)
    
    st.subheader("B1. Variétés et superficies")
    st.write("Q5. Pour chaque espèce cultivée, indiquer les variétés et superficies :")
    
    # Initialize variables to avoid NameError if not all cultures are selected
    df_framboisier = pd.DataFrame()
    df_myrtillier = pd.DataFrame()
    df_murier = pd.DataFrame()
    
    if "Framboisier" in cultures:
        st.write("**Framboisier**")
        df_framboisier = st.data_editor(
            pd.DataFrame([{"Variété": "", "Superficie (ha)": 0.0, "Fournisseur plants": "", "Origine plants": "", "Coût plant (DH)": 0.0, "Âge plantation (ans)": 0}]),
            num_rows="dynamic",
            key="grid_framboisier"
        )
    if "Myrtillier" in cultures:
        st.write("**Myrtillier**")
        df_myrtillier = st.data_editor(
            pd.DataFrame([{"Variété": "", "Superficie (ha)": 0.0, "Fournisseur plants": "", "Origine plants": "", "Coût plant (DH)": 0.0, "Âge plantation (ans)": 0}]),
            num_rows="dynamic",
            key="grid_myrtillier"
        )
    if "Mûrier" in cultures:
        st.write("**Mûrier**")
        df_murier = st.data_editor(
            pd.DataFrame([{"Variété": "", "Superficie (ha)": 0.0, "Fournisseur plants": "", "Origine plants": "", "Coût plant (DH)": 0.0, "Âge plantation (ans)": 0}]),
            num_rows="dynamic",
            key="grid_murier"
        )

    st.subheader("Q6. Qualité sanitaire et stade des plants à la plantation")
    qualite_sanitaire = st.radio("Qualité sanitaire", ["Plants certifiés", "Non certifiés", "Contrôle visuel seulement"])
    stade_plants = st.selectbox("Stade", ["Plants en mottes", "Tray plants", "Long canes vernalisés", "Bare root"])
    
    vernalisation_temp, vernalisation_duree, vernalisation_type = None, None, None
    if stade_plants == "Long canes vernalisés":
        st.write("Framboisier long canes — Vernalisation :")
        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            vernalisation_temp = st.number_input("T° (°C)", format="%.1f")
        with col_v2:
            vernalisation_duree = st.number_input("Durée (semaines)", min_value=0, step=1)
        with col_v3:
            vernalisation_type = st.radio("Type de vernalisation", ["Externalisée", "Interne"])

    st.divider()

    st.subheader("B2. Système de culture et substrat")
    st.write("Q7. Mode de culture par espèce")
    
    mode_framboisier = None
    if "Framboisier" in cultures:
        mode_framboisier = st.radio("Framboisier :", ["Plein sol", "Hors-sol"], key="mode_fram")
    mode_myrtillier = None
    if "Myrtillier" in cultures:
        mode_myrtillier = st.radio("Myrtillier :", ["Hors-sol", "Plein sol"], key="mode_myrt")
    mode_murier = None
    if "Mûrier" in cultures:
        mode_murier = st.radio("Mûrier :", ["Hors-sol", "Plein sol"], key="mode_mur")

    st.write("Q8. Composition détaillée du substrat utilisé (% volumique)")
    df_substrat = pd.DataFrame(
        [
            {"Composant": "Fibre de coco (coir)", "Framboisier (%)": 0, "Myrtillier (%)": 0, "Mûrier (%)": 0, "Fournisseur": "", "Coût (DH/m³)": 0},
            {"Composant": "Perlite", "Framboisier (%)": 0, "Myrtillier (%)": 0, "Mûrier (%)": 0, "Fournisseur": "", "Coût (DH/m³)": 0},
            {"Composant": "Tourbe blonde (Sphagnum)", "Framboisier (%)": 0, "Myrtillier (%)": 0, "Mûrier (%)": 0, "Fournisseur": "", "Coût (DH/m³)": 0},
            {"Composant": "Autre", "Framboisier (%)": 0, "Myrtillier (%)": 0, "Mûrier (%)": 0, "Fournisseur": "", "Coût (DH/m³)": 0}
        ]
    )
    edited_substrat = st.data_editor(df_substrat, hide_index=True)

    st.write("Q9. Caractéristiques physico-chimiques du substrat à la mise en place :")
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.write("**Framboisier**")
        ph_framboisier = st.number_input("pH substrat Framboisier", min_value=0.0, max_value=14.0, format="%.1f")
        ce_framboisier = st.number_input("CE substrat (dS/m) Framboisier", min_value=0.0, format="%.2f")
        vol_framboisier = st.selectbox("Volume des contenants Framboisier", ["4,5 L", "7 L", "Autre"], key="vol_fram")
        if vol_framboisier == "Autre":
            vol_framboisier = st.text_input("Précisez volume (Framboisier)", key="vol_fram_autre")

    with col_c2:
        st.write("**Myrtillier**")
        ph_myrtillier = st.number_input("pH substrat Myrtillier", min_value=0.0, max_value=14.0, format="%.1f")
        ce_myrtillier = st.number_input("CE substrat (dS/m) Myrtillier", min_value=0.0, format="%.2f")
        vol_myrtillier = st.selectbox("Volume des contenants Myrtillier", ["20 L", "30 L", "40 L", "Autre"], key="vol_myrt")
        if vol_myrtillier == "Autre":
            vol_myrtillier = st.text_input("Précisez volume (Myrtillier)", key="vol_myrt_autre")

    with col_c3:
        st.write("**Mûrier**")
        ph_murier = st.number_input("pH substrat Mûrier", min_value=0.0, max_value=14.0, format="%.1f")
        ce_murier = st.number_input("CE substrat (dS/m) Mûrier", min_value=0.0, format="%.2f")
        vol_murier = st.number_input("Volume contenants Mûrier (L)", min_value=0.0, format="%.1f")

    col_c4, col_c5 = st.columns(2)
    with col_c4:
        porosite = st.number_input("Porosité totale (%)", min_value=0.0, max_value=100.0)
    with col_c5:
        retention_eau = st.number_input("Capacité de rétention eau (%)", min_value=0.0, max_value=100.0)

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        renouvellement_substrat = st.selectbox("Renouvellement substrat", ["Chaque cycle", "Tous les 2 ans", "Non renouvelé"])
    with col_r2:
        cout_renouvellement = st.number_input("Coût renouvellement (DH/ha)", min_value=0.0)

    st.divider()

    st.subheader("B3. Densités de plantation et période")
    st.write("Q10. Densités pratiquées et période de plantation :")
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        densite_framboisier_ml = st.number_input("Framboisier : cannes/mètre linéaire", min_value=0.0)
        densite_myrtillier_ha = st.number_input("Myrtillier : plants/ha", min_value=0)
        densite_myrtillier_m2 = st.number_input("Myrtillier : pots/m²", min_value=0.0)
        densite_murier_ha = st.number_input("Mûrier : plants/ha", min_value=0)

    with col_d2:
        periode_framboisier = st.text_input("Période plantation Framboisier")
        periode_myrtillier = st.text_input("Période plantation Myrtillier")
        periode_murier = st.text_input("Période plantation Mûrier")

with tab3:
    st.markdown('<div class="info-card"><div class="info-card-title">🏗️ BLOC C — Infrastructure : Abris, Irrigation et Équipements</div></div>', unsafe_allow_html=True)
    
    st.subheader("Q11. Type et caractéristiques des abris")
    type_abri = st.radio(
        "Type :", 
        ["Serre canarienne", "Tunnel plastique", "Serre multichapelle", "Combinaison"]
    )
    
    st.subheader("Q12. Gestion climatique sous abri")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        ventilation = st.radio("Ventilation :", ["Ouverture latérale manuelle", "Automatisée"])
    with col_g2:
        capteurs_climato = st.selectbox(
            "Capteurs climatiques :", 
            ["Thermomètre simple", "Station météo automatisée", "Sondes HR+T°", "Aucun"]
        )

    st.subheader("Q13. Équipement d'irrigation")
    col_i1, col_i2, col_i3 = st.columns(3)
    with col_i1:
        nb_goutteurs = st.number_input("Nb goutteurs/plant :", min_value=0.0, step=1.0)
    with col_i2:
        debit_goutteur = st.number_input("Débit goutteur (L/h) :", min_value=0.0, format="%.2f")
    with col_i3:
        marque_goutteur = st.text_input("Marque/type :")

    col_i4, col_i5 = st.columns(2)
    with col_i4:
        station_fertigation = st.radio(
            "Station de fertigation :", 
            ["Automatisée", "Programmateur simple", "Manuel"]
        )
        nb_tetes = st.number_input("Nb têtes d'injection :", min_value=0, step=1)
    with col_i5:
        marque_station = st.text_input("Marque station :")
        erp_connecte = st.radio("ERP connecté :", ["Oui", "Non"])

with tab4:
    st.markdown('<div class="info-card"><div class="info-card-title">💧 BLOC D — Pilotage de l\'Irrigation</div></div>', unsafe_allow_html=True)
    
    st.subheader("D1. Sources d'eau")
    st.write("Q14. Origine et qualité de l'eau d'irrigation :")
    df_eau = pd.DataFrame(
        [
            {"Type": "Forage", "Débit (m³/h)": 0.0, "CE brute (dS/m)": 0.0, "pH brut": 0.0, "Coût (DH/m³)": 0.0, "Part mélange (%)": 0},
            {"Type": "Dessalée", "Débit (m³/h)": 0.0, "CE brute (dS/m)": 0.0, "pH brut": 0.0, "Coût (DH/m³)": 0.0, "Part mélange (%)": 0},
            {"Type": "Barrage", "Débit (m³/h)": 0.0, "CE brute (dS/m)": 0.0, "pH brut": 0.0, "Coût (DH/m³)": 0.0, "Part mélange (%)": 0}
        ]
    )
    edited_eau = st.data_editor(df_eau, hide_index=True)

    st.write("Q15. Gestion du Bore et post-traitement eau dessalée :")
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        post_traitement_bore = st.radio("Post-traitement appliqué :", ["Oui", "Non"])
        if post_traitement_bore == "Oui":
            type_traitement_bore = st.text_input("Lequel :")
        else:
            type_traitement_bore = ""
    with col_b2:
        st.write("Ratio blending :")
        ratio_dessalee = st.number_input("Dessalée (%)", min_value=0.0, max_value=100.0)
        ratio_forage = st.number_input("Forage (%)", min_value=0.0, max_value=100.0)
    with col_b3:
        bore_mesure = st.number_input("Bore mesuré après ttt (mg/L)", min_value=0.0)
        freq_mesure_bore = st.number_input("Fréquence (fois/semaine)", min_value=0)

    st.divider()
    st.subheader("D2. Coefficients culturaux et volumes")
    st.write("Q16. Volumes d'eau appliqués par stade phénologique (m³/ha/jour) :")

    cols_stades = ["Installation", "Végétatif", "Floraison", "Gross. baies", "Récolte (pic)", "Post-récolte", "Dormance", "Volume annuel total (m³/ha)", "Fraction lessivage (%)", "Nb apports/j", "Durée apport (min)"]
    
    df_volumes = pd.DataFrame({
        "Paramètre / Stade": ["Volume/j Framb. (m³/ha)", "Volume/j Myrtil.", "Volume/j Mûrier"],
        **{col: [0.0, 0.0, 0.0] for col in cols_stades}
    })
    
    edited_volumes = st.data_editor(df_volumes, hide_index=True)

    st.write("Q17. Méthode de déclenchement et pilotage de l'irrigation :")
    methodes_irrigation = st.multiselect(
        "Méthode :", 
        ["Tensiomètres", "Sonde capacitive", "Calcul ETP", "Autre"]
    )
    
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        ce_solution = st.number_input("CE solution nutritive appliquée (dS/m)", min_value=0.0)
    with col_p2:
        fraction_lessivage = st.number_input("Fraction de lessivage appliquée (%)", min_value=0.0, max_value=100.0)
    with col_p3:
        ce_drainage = st.number_input("CE du drainage (dS/m)", min_value=0.0)
        freq_mesure_drainage = st.number_input("Fréquence mesure drainage (fois/semaine)", min_value=0)

with tab5:
    st.markdown('<div class="info-card"><div class="info-card-title">🧪 BLOC E — Pilotage de la Fertigation</div></div>', unsafe_allow_html=True)
    
    st.write("Veuillez renseigner les programmes pour chaque culture enquêtée :")
    cols_q18 = ["CE (dS/m)", "pH", "NH₄/NO₃", "N (kg/ha)", "P₂O₅", "K₂O", "CaO", "MgO", "Fe (g/ha)", "B (g/ha)", "Coût (DH/ha)"]
    stades = ["Dormance/Taille", "Végétatif", "Floraison/Nouaison", "Grossissement/Récolte", "Post-récolte", "TOTAL annuel"]
    
    df_fert_vide = pd.DataFrame({"Stade": stades, **{col: [0.0]*len(stades) for col in cols_q18}})
    df_engrais_vide = pd.DataFrame({"Engrais commercial": [""], "Formule NPK": [""], "Dose annuelle (kg/ha)": [0.0], "Stade principal": [""], "Mode application": [""], "Coût (DH/kg)": [0.0]})
    df_fol_vide = pd.DataFrame({"Produit (nom)": [""], "Type": [""], "Dose (cc ou g/hl)": [""], "Vol. bouillie (L/ha)": [0.0], "Fréq. (fois/cycle)": [0], "Période/stade": [""], "Objectif": [""]})
    
    edited_fert_framb, edited_eng_framb, edited_fol_framb = None, None, None
    edited_fert_myrt, edited_eng_myrt, edited_fol_myrt = None, None, None
    edited_fert_mur, edited_eng_mur, edited_fol_mur = None, None, None

    if "Framboisier" in cultures:
        st.subheader("🍓 FRAMBOISIER - Fertigation")
        st.write("Q18. Paramètres cibles (Framboisier) :")
        edited_fert_framb = st.data_editor(df_fert_vide, hide_index=True, key="fert_framb")
        st.write("Q19. Engrais commerciaux (Framboisier) :")
        edited_eng_framb = st.data_editor(df_engrais_vide, num_rows="dynamic", key="eng_framb", hide_index=True)
        st.write("Q20. Foliaires / Bio-stimulants (Framboisier) :")
        edited_fol_framb = st.data_editor(df_fol_vide, num_rows="dynamic", key="fol_framb", hide_index=True)
        st.divider()
        
    if "Myrtillier" in cultures:
        st.subheader("🫐 MYRTILLIER - Fertigation")
        st.write("Q18. Paramètres cibles (Myrtillier) :")
        edited_fert_myrt = st.data_editor(df_fert_vide, hide_index=True, key="fert_myrt")
        st.write("Q19. Engrais commerciaux (Myrtillier) :")
        edited_eng_myrt = st.data_editor(df_engrais_vide, num_rows="dynamic", key="eng_myrt", hide_index=True)
        st.write("Q20. Foliaires / Bio-stimulants (Myrtillier) :")
        edited_fol_myrt = st.data_editor(df_fol_vide, num_rows="dynamic", key="fol_myrt", hide_index=True)
        st.divider()

    if "Mûrier" in cultures:
        st.subheader("🍇 MÛRIER - Fertigation")
        st.write("Q18. Paramètres cibles (Mûrier) :")
        edited_fert_mur = st.data_editor(df_fert_vide, hide_index=True, key="fert_mur")
        st.write("Q19. Engrais commerciaux (Mûrier) :")
        edited_eng_mur = st.data_editor(df_engrais_vide, num_rows="dynamic", key="eng_mur", hide_index=True)
        st.write("Q20. Foliaires / Bio-stimulants (Mûrier) :")
        edited_fol_mur = st.data_editor(df_fol_vide, num_rows="dynamic", key="fol_mur", hide_index=True)

with tab6:
    st.markdown('<div class="info-card"><div class="info-card-title">✂️ BLOC F — Taille, Palissage et Conduite de la Culture</div></div>', unsafe_allow_html=True)
    
    st.subheader("Q21. Conduite du framboisier")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        cannes_ml = st.number_input("Cannes maintenues après éclaircissage (cannes/ml)", min_value=0.0)
        palissage_framb = st.selectbox("Palissage", ["En I (filet vertical)", "En T (floricanes — Adelita, Carmina)", "En T inversé (primocanes)"])
        hauteur_fils = st.number_input("Hauteur fils hauts (m)", min_value=0.0)
    with col_f2:
        cannes_pot = st.number_input("Cannes/pot", min_value=0.0)
        recepage_total = st.radio("Recépage total post-récolte", ["Oui", "Non"])
        espacement_poteaux = st.number_input("Espacement poteaux (m)", min_value=0.0)

    st.subheader("Q22. Conduite du myrtillier")
    col_f3, col_f4 = st.columns(2)
    with col_f3:
        tiges_prod_myrt = st.number_input("Nb tiges productives maintenues / plant", min_value=0)
        taille_rajeunissement = st.radio("Taille de rajeunissement", ["Oui", "Non"])
        si_oui_ans = st.number_input("Si oui, tous les (ans)", min_value=0)
    with col_f4:
        reduc_biomasse = st.number_input("Réduction biomasse phase formation (%)", min_value=0.0, max_value=100.0)
        tiges_rabattues = st.number_input("Tiges rabattues / plant / an", min_value=0)

    st.subheader("Q23. Conduite du mûrier")
    col_f5, col_f6 = st.columns(2)
    with col_f5:
        tiges_palissees_murier = st.number_input("Tiges palissées / plant", min_value=0)
        largeur_haie = st.number_input("Largeur haie (cm)", min_value=0.0)
    with col_f6:
        hauteur_ecimage = st.number_input("Hauteur écimage apical (m)", min_value=0.0)
        hauteur_haie = st.number_input("Hauteur haie maintenue (m)", min_value=0.0)

    st.subheader("Q24. Pollinisation")
    col_f7, col_f8 = st.columns(2)
    with col_f7:
        st.write("**Abeilles**")
        abeilles = st.radio("Utilisation abeilles", ["Oui", "Non"])
        densite_abeilles = st.number_input("Densité (ruches /ha)", min_value=0.0)
        periode_abeilles = st.text_input("Période introduction (abeilles)")
        cout_abeilles = st.number_input("Coût (DH/ruches)", min_value=0.0)
    with col_f8:
        st.write("**Bourdons**")
        bourdons = st.radio("Utilisation bourdons", ["Oui", "Non"])
        densite_bourdons = st.number_input("Densité (colonies/ha)", min_value=0.0)
        cout_bourdons = st.number_input("Coût (DH/colonie)", min_value=0.0)

with tab7:
    st.markdown('<div class="info-card"><div class="info-card-title">🛡️ BLOC G — Protection Phytosanitaire et Indicateurs ESG</div></div>', unsafe_allow_html=True)
    
    maladies_liste = [
        "Pourriture grise (Botrytis cinerea)", "Cladosporiose (Cladosporium herbarum)", 
        "Oïdium (Podosphaera aphanis)", "Phytophthora (Phytophthora fragariae)", 
        "Alternariose (Alternaria alternata)", "Acariens tétranyques (Tetranychus urticae)", 
        "Acariens tarsonèmes (Phytonemus pallidus)", "Thrips (Frankliniella occidentalis)", 
        "Drosophile tachetée (Drosophila suzukii)", "Cécidomyie (Dasineura oxycoccana)", 
        "Pucerons (Aphis spp.)", "Cochenilles (Divers)"
    ]
    df_phyto_vide = pd.DataFrame({"Bioagresseur": maladies_liste, "Intensité (0-3)": [0]*12, "Période (mois)": [""]*12, "Organe atteint": [""]*12})
    df_trait_vide = pd.DataFrame({"Nom commercial": [""], "Matière active": [""], "Cible": [""], "Dose (cc/g/hl)": [0.0], "Vol. bouillie (L/ha)": [0.0], "Nb passages": [0], "Stade appli": [""], "Mode": [""], "DAR (j)": [0], "Coût DH/ha": [0.0]})
    df_aux_vide = pd.DataFrame([
        {"Auxiliaire": "Phytoseiulus persimilis", "Ravageur ciblé": "", "Dose (ind./m²)": 0.0, "Nb lâchers/cycle": 0, "Période": "", "Format": "", "Coût (DH/ha)": 0.0},
        {"Auxiliaire": "Amblyseius swirskii", "Ravageur ciblé": "", "Dose (ind./m²)": 0.0, "Nb lâchers/cycle": 0, "Période": "", "Format": "", "Coût (DH/ha)": 0.0},
        {"Auxiliaire": "Neoseiulus cucumeris", "Ravageur ciblé": "", "Dose (ind./m²)": 0.0, "Nb lâchers/cycle": 0, "Période": "", "Format": "", "Coût (DH/ha)": 0.0},
        {"Auxiliaire": "Orius laevigatus", "Ravageur ciblé": "", "Dose (ind./m²)": 0.0, "Nb lâchers/cycle": 0, "Période": "", "Format": "", "Coût (DH/ha)": 0.0},
        {"Auxiliaire": "Steinernema feltiae", "Ravageur ciblé": "", "Dose (ind./m²)": 0.0, "Nb lâchers/cycle": 0, "Période": "", "Format": "", "Coût (DH/ha)": 0.0},
        {"Auxiliaire": "Bacillus thuringiensis", "Ravageur ciblé": "", "Dose (ind./m²)": 0.0, "Nb lâchers/cycle": 0, "Période": "", "Format": "", "Coût (DH/ha)": 0.0},
        {"Auxiliaire": "Autre", "Ravageur ciblé": "", "Dose (ind./m²)": 0.0, "Nb lâchers/cycle": 0, "Période": "", "Format": "", "Coût (DH/ha)": 0.0}
    ])
    
    edited_phyto_framb, edited_trait_framb, edited_aux_framb = None, None, None
    edited_phyto_myrt, edited_trait_myrt, edited_aux_myrt = None, None, None
    edited_phyto_mur, edited_trait_mur, edited_aux_mur = None, None, None

    st.write("Veuillez renseigner les programmes phytosanitaires pour chaque culture :")
    
    if "Framboisier" in cultures:
        st.subheader("🍓 FRAMBOISIER - Protection")
        st.write("Q25. Pressions phytosanitaires (Framboisier) :")
        edited_phyto_framb = st.data_editor(df_phyto_vide, hide_index=True, key="phyto_framb")
        st.write("Q26. Traitements chimiques (Framboisier) :")
        edited_trait_framb = st.data_editor(df_trait_vide, num_rows="dynamic", hide_index=True, key="trait_framb")
        st.write("Q28. Auxiliaires bio (Framboisier) :")
        edited_aux_framb = st.data_editor(df_aux_vide, hide_index=True, key="aux_framb")
        st.divider()

    if "Myrtillier" in cultures:
        st.subheader("🫐 MYRTILLIER - Protection")
        st.write("Q25. Pressions phytosanitaires (Myrtillier) :")
        edited_phyto_myrt = st.data_editor(df_phyto_vide, hide_index=True, key="phyto_myrt")
        st.write("Q26. Traitements chimiques (Myrtillier) :")
        edited_trait_myrt = st.data_editor(df_trait_vide, num_rows="dynamic", hide_index=True, key="trait_myrt")
        st.write("Q28. Auxiliaires bio (Myrtillier) :")
        edited_aux_myrt = st.data_editor(df_aux_vide, hide_index=True, key="aux_myrt")
        st.divider()

    if "Mûrier" in cultures:
        st.subheader("🍇 MÛRIER - Protection")
        st.write("Q25. Pressions phytosanitaires (Mûrier) :")
        edited_phyto_mur = st.data_editor(df_phyto_vide, hide_index=True, key="phyto_mur")
        st.write("Q26. Traitements chimiques (Mûrier) :")
        edited_trait_mur = st.data_editor(df_trait_vide, num_rows="dynamic", hide_index=True, key="trait_mur")
        st.write("Q28. Auxiliaires bio (Mûrier) :")
        edited_aux_mur = st.data_editor(df_aux_vide, hide_index=True, key="aux_mur")
        st.divider()
    
    col_g3a, col_g3b, col_g3c = st.columns(3)
    with col_g3a:
        part_lutte_bio_framb = st.number_input("Part lutte biol. (%) Framb.", min_value=0.0, max_value=100.0)
    with col_g3b:
        part_lutte_bio_myrt = st.number_input("Part lutte biol. (%) Myrt.", min_value=0.0, max_value=100.0)
    with col_g3c:
        part_lutte_bio_mur = st.number_input("Part lutte biol. (%) Mûr.", min_value=0.0, max_value=100.0)

    st.subheader("G4. Indicateurs ESG environnementaux")
    st.write("Q29. Water footprint et conformité réglementaire :")
    col_g4a, col_g4b = st.columns(2)
    with col_g4a:
        conso_eau_framb = st.number_input("Conso eau (m³/t) Framb.", min_value=0.0)
        conso_eau_myrt = st.number_input("Conso eau (m³/t) Myrt.", min_value=0.0)
        conso_eau_mur = st.number_input("Conso eau (m³/t) Mûr.", min_value=0.0)
        taux_drainage = st.number_input("Taux drainage recyclé (%)", min_value=0.0, max_value=100.0)
    with col_g4b:
        taux_lmr_100 = st.radio("Taux conformité LMR 100%", ["Oui", "Non"])
        nb_analyses = st.number_input("Nb analyses résidus/campagne", min_value=0)
        alertes_detectees = st.number_input("Alertes détectées", min_value=0)
        plan_esg = st.radio("Plan de gestion environnemental formalisé", ["Oui", "Non"])
        gestion_dechets = st.selectbox("Gestion déchets plastiques", ["Recyclé", "Décharge", "Brûlé"])
        
    st.write("Q30. Indicateurs ESG sociaux :")
    col_g4c, col_g4d = st.columns(2)
    with col_g4c:
        smag_respecte = st.radio("SMAG respecté", ["Oui", "Non"])
        salaire_journalier = st.number_input("Salaire journalier moyen (DH/j)", min_value=0.0)
        epi_portes = st.selectbox("EPI portés lors des traitements", ["Systématiquement", "Partiellement", "Non"])
    with col_g4d:
        formation_bpa = st.number_input("Formation BPA (h/ouvrier/an)", min_value=0.0)
        registre_formation = st.radio("Registre formation tenu", ["Oui", "Non"])
        protocole_hygiene = st.radio("Protocole hygiène récolte", ["Oui", "Non"])

with tab8:
    st.markdown('<div class="info-card"><div class="info-card-title">📦 BLOC H — Récolte et Performance</div></div>', unsafe_allow_html=True)
    
    st.subheader("H1. Rendements obtenus par culture")
    df_rend_vide = pd.DataFrame([{"Variété": "", "Rendement total (t/ha)": 0.0, "Rdt export Cat. I (t/ha)": 0.0, "Rdt Cat. II (t/ha)": 0.0, "Pertes champ (%)": 0.0, "Objectif initial (t/ha)": 0.0, "Écart / réel (%)": 0.0, "% export": 0.0}])
    
    edited_rend_framb, edited_rend_myrt, edited_rend_mur = None, None, None
    
    if "Framboisier" in cultures:
        st.write("🍓 **Rendements Framboisier** : (Q31)")
        edited_rend_framb = st.data_editor(df_rend_vide, num_rows="dynamic", hide_index=True, key="rend_framb")
    if "Myrtillier" in cultures:
        st.write("🫐 **Rendements Myrtillier** : (Q31)")
        edited_rend_myrt = st.data_editor(df_rend_vide, num_rows="dynamic", hide_index=True, key="rend_myrt")
    if "Mûrier" in cultures:
        st.write("🍇 **Rendements Mûrier** : (Q31)")
        edited_rend_mur = st.data_editor(df_rend_vide, num_rows="dynamic", hide_index=True, key="rend_mur")
    
    st.write("Q32. Qualité physico-chimique des fruits :")
    col_h1a, col_h1b, col_h1c = st.columns(3)
    with col_h1a:
        st.write("**Framboisier**")
        brix_framb = st.number_input("Brix Framb.", min_value=0.0)
        fermete_framb = st.number_input("Fermeté (N) Framb.", min_value=0.0)
        calibre_framb = st.number_input("Calibre (mm) Framb.", min_value=0.0)
        conformite_framb = st.number_input("Conformité Cat. I (%) Framb.", min_value=0.0, max_value=100.0)
    with col_h1b:
        st.write("**Myrtillier**")
        brix_myrt = st.number_input("Brix Myrt.", min_value=0.0)
        fermete_myrt = st.number_input("Fermeté (N) Myrt.", min_value=0.0)
        calibre_myrt = st.number_input("Calibre (mm) Myrt.", min_value=0.0)
        conformite_myrt = st.number_input("Conformité Cat. I (%) Myrt.", min_value=0.0, max_value=100.0)
    with col_h1c:
        st.write("**Mûrier**")
        brix_mur = st.number_input("Brix Mûr.", min_value=0.0)
        fermete_mur = st.number_input("Fermeté (N) Mûr.", min_value=0.0)
        calibre_mur = st.number_input("Calibre (mm) Mûr.", min_value=0.0)
        conformite_mur = st.number_input("Conformité Cat. I (%) Mûr.", min_value=0.0, max_value=100.0)

    st.subheader("H2. Performance de récolte — Main-d'œuvre")
    st.write("Q33. Rendement main-d'œuvre à la récolte :")
    col_h2a, col_h2b, col_h2c = st.columns(3)
    with col_h2a:
        st.write("**Framboisier**")
        rdt_mo_framb = st.number_input("Rendement (kg/ouv/h) Framb.", min_value=0.0)
        duree_recolte_framb = st.number_input("Durée campagne (sem) Framb.", min_value=0.0)
    with col_h2b:
        st.write("**Myrtillier**")
        rdt_mo_myrt = st.number_input("Rendement (kg/ouv/h) Myrt.", min_value=0.0)
        duree_recolte_myrt = st.number_input("Durée campagne (sem) Myrt.", min_value=0.0)
    with col_h2c:
        st.write("**Mûrier**")
        rdt_mo_mur = st.number_input("Rendement (kg/ouv/h) Mûr.", min_value=0.0)
        duree_recolte_mur = st.number_input("Durée campagne (sem) Mûr.", min_value=0.0)
        
    col_h2d, col_h2e = st.columns(2)
    with col_h2d:
        nb_ouvriers_pic = st.number_input("Nb ouvriers récolte / ha (pic)", min_value=0)
    with col_h2e:
        salaire_ouvrier_recolte = st.number_input("Salaire ouvrier récolte (DH/j)", min_value=0.0)

with tab9:
    st.markdown('<div class="info-card"><div class="info-card-title">❄️ BLOC I — Post-Récolte : Chaîne de Froid et Qualité Commerciale</div></div>', unsafe_allow_html=True)
    
    st.subheader("Q34. Gestion post-récolte — 'Time to Cold' et conditions de stockage")
    col_i1, col_i2, col_i3 = st.columns(3)
    with col_i1:
        ttc_framb = st.number_input("Délai cueillette → chambre froide (h) Framb.", min_value=0.0)
    with col_i2:
        ttc_myrt = st.number_input("Délai (h) Myrtil.", min_value=0.0)
    with col_i3:
        ttc_mur = st.number_input("Délai (h) Mûrier", min_value=0.0)

    col_i4, col_i5 = st.columns(2)
    with col_i4:
        temp_stockage = st.number_input("Température stockage chambre froide (°C)", format="%.1f")
        hr_stockage = st.number_input("HR chambre froide (%)", min_value=0.0, max_value=100.0)
    with col_i5:
        format_cond = st.multiselect("Format de conditionnement", ["125 g", "250 g", "500 g", "Vrac"])
        tri_cond = st.radio("Tri et conditionnement", ["Champ (directement à la cueillette)", "Station de conditionnement"])

    st.subheader("Q35. Pertes post-récolte et qualité commerciale")
    col_i6, col_i7, col_i8 = st.columns(3)
    with col_i6:
        st.write("**Framboisier**")
        pertes_pr_framb = st.number_input("Taux pertes post-récolte (%) Framb.", min_value=0.0, max_value=100.0)
        brix_exp_framb = st.number_input("°Brix moyen à l'expédition Framb.", min_value=0.0)
        prix_exp_framb = st.number_input("Prix export (DH/kg) Framb.", min_value=0.0)
        prix_loc_framb = st.number_input("Prix local (DH/kg) Framb.", min_value=0.0)
    with col_i7:
        st.write("**Myrtillier**")
        pertes_pr_myrt = st.number_input("Taux pertes post-récolte (%) Myrt.", min_value=0.0, max_value=100.0)
        brix_exp_myrt = st.number_input("°Brix moyen à l'expédition Myrt.", min_value=0.0)
        prix_exp_myrt = st.number_input("Prix export (DH/kg) Myrt.", min_value=0.0)
        prix_loc_myrt = st.number_input("Prix local (DH/kg) Myrt.", min_value=0.0)
    with col_i8:
        st.write("**Mûrier**")
        pertes_pr_mur = st.number_input("Taux pertes post-récolte (%) Mûr.", min_value=0.0, max_value=100.0)
        prix_exp_mur = st.number_input("Prix export (DH/kg) Mûr.", min_value=0.0)
        prix_loc_mur = st.number_input("Prix local (DH/kg) Mûr.", min_value=0.0)

    st.write("Autres indicateurs :")
    col_i9, col_i10 = st.columns(2)
    with col_i9:
        refus_export = st.number_input("Taux de refus à l'export (%)", min_value=0.0, max_value=100.0)
    with col_i10:
        st.write("Destination production :")
        dest_export = st.number_input("Export frais (%)", min_value=0.0, max_value=100.0)
        dest_surgele = st.number_input("Surgelé (%)", min_value=0.0, max_value=100.0)
        dest_local = st.number_input("Marché local (%)", min_value=0.0, max_value=100.0)

with tab10:
    st.markdown('<div class="info-card"><div class="info-card-title">👷 BLOC J — Main-d\'Œuvre : Journées de Travail par Opération</div></div>', unsafe_allow_html=True)
    
    st.subheader("Q36. Personnel permanent de l'exploitation")
    df_personnel = pd.DataFrame([
        {"Poste": "Gérant / Directeur exploitation", "Nombre": 0, "Salaire (DH/mois)": 0.0},
        {"Poste": "Responsable technique", "Nombre": 0, "Salaire (DH/mois)": 0.0},
        {"Poste": "Chef de culture", "Nombre": 0, "Salaire (DH/mois)": 0.0},
        {"Poste": "Technicien agricole", "Nombre": 0, "Salaire (DH/mois)": 0.0},
        {"Poste": "Magasinier / Logisticien", "Nombre": 0, "Salaire (DH/mois)": 0.0},
        {"Poste": "Chauffeur tracteur / Mécanicien", "Nombre": 0, "Salaire (DH/mois)": 0.0},
        {"Poste": "Caporaux / Chefs d'équipe", "Nombre": 0, "Salaire (DH/mois)": 0.0}
    ])
    edited_personnel = st.data_editor(df_personnel, hide_index=True)

    st.subheader("Q37. Journées de travail saisonnier par opération (JT/ha/an)")
    df_jt = pd.DataFrame([
        {"Opération culturale": "Plantation / implantation", "Framb. (JT/ha)": 0.0, "Myrtil. (JT/ha)": 0.0, "Mûrier (JT/ha)": 0.0, "Période": "", "Salaire JT (DH/j)": 0.0, "Coût total (DH/ha)": 0.0},
        {"Opération culturale": "Installation palissage / substrat", "Framb. (JT/ha)": 0.0, "Myrtil. (JT/ha)": 0.0, "Mûrier (JT/ha)": 0.0, "Période": "", "Salaire JT (DH/j)": 0.0, "Coût total (DH/ha)": 0.0},
        {"Opération culturale": "Taille et palissage", "Framb. (JT/ha)": 0.0, "Myrtil. (JT/ha)": 0.0, "Mûrier (JT/ha)": 0.0, "Période": "", "Salaire JT (DH/j)": 0.0, "Coût total (DH/ha)": 0.0},
        {"Opération culturale": "Surveillance irrigation", "Framb. (JT/ha)": 0.0, "Myrtil. (JT/ha)": 0.0, "Mûrier (JT/ha)": 0.0, "Période": "", "Salaire JT (DH/j)": 0.0, "Coût total (DH/ha)": 0.0},
        {"Opération culturale": "Préparation / contrôle fertigation", "Framb. (JT/ha)": 0.0, "Myrtil. (JT/ha)": 0.0, "Mûrier (JT/ha)": 0.0, "Période": "", "Salaire JT (DH/j)": 0.0, "Coût total (DH/ha)": 0.0},
        {"Opération culturale": "Traitements phytosanitaires", "Framb. (JT/ha)": 0.0, "Myrtil. (JT/ha)": 0.0, "Mûrier (JT/ha)": 0.0, "Période": "", "Salaire JT (DH/j)": 0.0, "Coût total (DH/ha)": 0.0},
        {"Opération culturale": "Récolte", "Framb. (JT/ha)": 0.0, "Myrtil. (JT/ha)": 0.0, "Mûrier (JT/ha)": 0.0, "Période": "", "Salaire JT (DH/j)": 0.0, "Coût total (DH/ha)": 0.0},
        {"Opération culturale": "Triage et conditionnement au champ", "Framb. (JT/ha)": 0.0, "Myrtil. (JT/ha)": 0.0, "Mûrier (JT/ha)": 0.0, "Période": "", "Salaire JT (DH/j)": 0.0, "Coût total (DH/ha)": 0.0},
        {"Opération culturale": "Autres", "Framb. (JT/ha)": 0.0, "Myrtil. (JT/ha)": 0.0, "Mûrier (JT/ha)": 0.0, "Période": "", "Salaire JT (DH/j)": 0.0, "Coût total (DH/ha)": 0.0},
        {"Opération culturale": "TOTAL JT/ha/an", "Framb. (JT/ha)": 0.0, "Myrtil. (JT/ha)": 0.0, "Mûrier (JT/ha)": 0.0, "Période": "", "Salaire JT (DH/j)": 0.0, "Coût total (DH/ha)": 0.0}
    ])
    edited_jt = st.data_editor(df_jt, hide_index=True)

with tab11:
    st.markdown('<div class="info-card"><div class="info-card-title">📊 BLOC M — Perception de la Standardisation et Adhésion au Référentiel</div></div>', unsafe_allow_html=True)
    
    st.write("Q38. L'absence de normes techniques communes nuit-elle à la compétitivité régionale ?")
    q38 = st.radio("Perception", ["Oui, fortement", "Oui, modérément", "Non", "Sans avis"])
    
    st.write("Q39. Seriez-vous prêt à adopter un référentiel technique basé sur les Top Performers de la région ?")
    q39 = st.radio("Adoption", ["Oui, totalement", "Oui, sous conditions", "Non"])
    q39_conditions = ""
    if q39 == "Oui, sous conditions":
        q39_conditions = st.text_input("Précisez vos conditions :")
        
    st.write("Q40. Les 3 axes les plus importants à standardiser en priorité (classer 1, 2, 3) :")
    axes = [
        "Fertigation / nutrition", "Irrigation", "Choix variétal", 
        "Protection intégrée (IPM)", "Chaîne de froid post-récolte", 
        "Gestion substrat", "Densités plantation"
    ]
    df_axes = pd.DataFrame({"Axe": axes, "Classement (1,2,3)": [0]*len(axes)})
    edited_axes = st.data_editor(df_axes, hide_index=True)
    
    st.write("Q41. Principaux obstacles à l'adoption de nouvelles pratiques :")
    obstacles = st.multiselect(
        "Obstacles", 
        ["Coût d'investissement élevé", "Manque de formation technique", 
         "Contraintes opérateur / exportateur", "Accès limité aux intrants certifiés", 
         "Résistance au changement", "Autre"]
    )
    obstacle_autre = ""
    if "Autre" in obstacles:
        obstacle_autre = st.text_input("Précisez l'autre obstacle :")

st.divider()

# Bouton de soumission
if st.button("Enregistrer les données", type="primary"):
    if not code_fiche or not nom_prenom:
        st.warning("Veuillez remplir au moins le 'Code fiche' et le 'Nom & Prénom' avant de sauvegarder.")
    else:
        st.success("Les données ont été enregistrées avec succès ! 🎉")
        
        # Récapitulatif des données saisies
        data = {
            "Code fiche": code_fiche,
            "Date enquête": date_enquete.strftime("%Y-%m-%d"),
            "Enquêteur": enqueteur,
            "Cultures enquêtées": ", ".join(cultures),
            "Durée de l'enquête (h)": duree,
            
            "Nom & Prénom": nom_prenom,
            "Téléphone": telephone,
            "Fonction": fonction,
            "Formation": formation_autre if formation == "Autre" else formation,
            "Expérience en fruits rouges (ans)": experience,
            
            "Nom de l'exploitation": nom_exploitation,
            "Commune / Douar": commune,
            "Zone": zone_autre if zone == "Autre" else zone,
            "Réseau commercial": reseau_autre if reseau == "Autre" else reseau,
            
            "Certifications": ", ".join(certifications),
            "Dernière date d'audit": date_audit.strftime("%Y-%m-%d"),
            "Organisme certificateur": organisme_certif,
            
            "Consentement pour le référentiel": consentement,
            
            "Qualité Sanitaire": qualite_sanitaire,
            "Stade Plants": stade_plants,
            "Vernalisation Température (°C)": vernalisation_temp,
            "Vernalisation Durée (sem)": vernalisation_duree,
            "Vernalisation Type": vernalisation_type,
            
            "Mode de culture Framboisier": mode_framboisier,
            "Mode de culture Myrtillier": mode_myrtillier,
            "Mode de culture Mûrier": mode_murier,
            
            "pH substrat Framboisier": ph_framboisier,
            "CE substrat Framboisier (dS/m)": ce_framboisier,
            "Vol. contenant Framb.": vol_framboisier,
            "pH substrat Myrtillier": ph_myrtillier,
            "CE substrat Myrtillier (dS/m)": ce_myrtillier,
            "Vol. contenant Myrtill.": vol_myrtillier,
            "pH substrat Mûrier": ph_murier,
            "CE substrat Mûrier (dS/m)": ce_murier,
            "Vol. contenant Mûrier": vol_murier,
            "Porosité totale (%)": porosite,
            "Capacité rétention eau (%)": retention_eau,
            "Renouvellement substrat": renouvellement_substrat,
            "Coût renouv. (DH/ha)": cout_renouvellement,
            
            "Densité Framboisier (cannes/ml)": densite_framboisier_ml,
            "Densité Myrtillier (plants/ha)": densite_myrtillier_ha,
            "Densité Myrtillier (pots/m²)": densite_myrtillier_m2,
            "Densité Mûrier (plants/ha)": densite_murier_ha,
            "Période plantation Framb.": periode_framboisier,
            "Période plantation Myrtill.": periode_myrtillier,
            "Période plantation Mûrier": periode_murier,
            
            "Type abri": type_abri,
            "Ventilation": ventilation,
            "Capteurs climatiques": capteurs_climato,
            
            "Nb Goutteurs/plant": nb_goutteurs,
            "Débit goutteur (L/h)": debit_goutteur,
            "Marque goutteur": marque_goutteur,
            
            "Station fertigation": station_fertigation,
            "Nb têtes injection": nb_tetes,
            "Marque station": marque_station,
            "ERP connecté": erp_connecte,
            
            "Post-traitement Bore": post_traitement_bore,
            "Type traitement Bore": type_traitement_bore,
            "Ratio Dessalée (%)": ratio_dessalee,
            "Ratio Forage (%)": ratio_forage,
            "Bore mesuré (mg/L)": bore_mesure,
            "Fréquence mesure Bore": freq_mesure_bore,
            
            "Méthode irrigation": ", ".join(methodes_irrigation),
            "CE sol. nutritive": ce_solution,
            "Fraction lessivage (%)": fraction_lessivage,
            "CE drainage": ce_drainage,
            "Fréq. mesure drainage": freq_mesure_drainage,
            
            "Cannes/ml (Framb)": cannes_ml,
            "Palissage (Framb)": palissage_framb,
            "Hauteur fils hauts (m)": hauteur_fils,
            "Cannes/pot (Framb)": cannes_pot,
            "Recépage post-récolte": recepage_total,
            "Espacement poteaux (m)": espacement_poteaux,
            
            "Nb tiges myrtille": tiges_prod_myrt,
            "Taille rajeunissement": taille_rajeunissement,
            "Taille rajeun. tous les (ans)": si_oui_ans,
            "Réduction biomasse (%)": reduc_biomasse,
            "Tiges rabattues / an": tiges_rabattues,
            
            "Tiges palissées (Mûr)": tiges_palissees_murier,
            "Largeur haie (cm)": largeur_haie,
            "Hauteur écimage (m)": hauteur_ecimage,
            "Hauteur haie (m)": hauteur_haie,
            
            "Utilisation abeilles": abeilles,
            "Densité (ruches/ha)": densite_abeilles,
            "Période abeilles": periode_abeilles,
            "Coût abeilles (DH/ruches)": cout_abeilles,
            "Utilisation bourdons": bourdons,
            "Densité (colonies/ha)": densite_bourdons,
            "Coût bourdons (DH)": cout_bourdons,
            
            "IFT Fongicides Framb.": ift_fong_framb,
            "IFT Insecticides Framb.": ift_ins_framb,
            "IFT Total Framb.": ift_tot_framb,
            "Coût protection (DH/ha) Framb.": cout_phyto_framb,
            "IFT Fongicides Myrtill.": ift_fong_myrt,
            "IFT Insecticides Myrtill.": ift_ins_myrt,
            "IFT Total Myrtill.": ift_tot_myrt,
            "Coût protection (DH/ha) Myrtill.": cout_phyto_myrt,
            "IFT Fongicides Mûrier": ift_fong_mur,
            "IFT Insecticides Mûrier": ift_ins_mur,
            "IFT Total Mûrier": ift_tot_mur,
            "Coût protection (DH/ha) Mûrier": cout_phyto_mur,
            
            "Part lutte bio (%) Framb.": part_lutte_bio_framb,
            "Part lutte bio (%) Myrtill.": part_lutte_bio_myrt,
            "Part lutte bio (%) Mûrier": part_lutte_bio_mur,
            
            "Conso eau (m³/t) Framb.": conso_eau_framb,
            "Conso eau (m³/t) Myrtill.": conso_eau_myrt,
            "Conso eau (m³/t) Mûrier": conso_eau_mur,
            "Taux drainage recyclé (%)": taux_drainage,
            "Taux conformité LMR 100%": taux_lmr_100,
            "Nb analyses résidus": nb_analyses,
            "Alertes détectées": alertes_detectees,
            "Plan ESG formalisé": plan_esg,
            "Gestion déchets plastiques": gestion_dechets,
            
            "SMAG respecté": smag_respecte,
            "Salaire moyen (DH/j)": salaire_journalier,
            "Port EPI": epi_portes,
            "Formation BPA (h/an)": formation_bpa,
            "Registre formation": registre_formation,
            "Protocole hygiène": protocole_hygiene,
            
            "Brix Framboisier": brix_framb,
            "Fermeté (N) Framboisier": fermete_framb,
            "Calibre (mm) Framboisier": calibre_framb,
            "Conformité Cat I (%) Framboisier": conformite_framb,
            "Brix Myrtillier": brix_myrt,
            "Fermeté (N) Myrtillier": fermete_myrt,
            "Calibre (mm) Myrtillier": calibre_myrt,
            "Conformité Cat I (%) Myrtillier": conformite_myrt,
            "Brix Mûrier": brix_mur,
            "Fermeté (N) Mûrier": fermete_mur,
            "Calibre (mm) Mûrier": calibre_mur,
            "Conformité Cat I (%) Mûrier": conformite_mur,
            
            "Rdt Main-d'œuvre (kg/ouv/h) Framboisier": rdt_mo_framb,
            "Durée récolte (semaines) Framboisier": duree_recolte_framb,
            "Rdt Main-d'œuvre (kg/ouv/h) Myrtillier": rdt_mo_myrt,
            "Durée récolte (semaines) Myrtillier": duree_recolte_myrt,
            "Rdt Main-d'œuvre (kg/ouv/h) Mûrier": rdt_mo_mur,
            "Durée récolte (semaines) Mûrier": duree_recolte_mur,
            "Nb ouvriers récolte (pic)": nb_ouvriers_pic,
            "Salaire ouvrier récolte (DH/j)": salaire_ouvrier_recolte,
            
            "Time to Cold (h) Framboisier": ttc_framb,
            "Time to Cold (h) Myrtillier": ttc_myrt,
            "Time to Cold (h) Mûrier": ttc_mur,
            "T° Stockage (°C)": temp_stockage,
            "HR chambre froide (%)": hr_stockage,
            "Format conditionnement": ", ".join(format_cond),
            "Lieu tri conditionnement": tri_cond,
            
            "Taux pertes (%) Framboisier": pertes_pr_framb,
            "°Brix expédition Framboisier": brix_exp_framb,
            "Prix Export (DH/kg) Framboisier": prix_exp_framb,
            "Prix Local (DH/kg) Framboisier": prix_loc_framb,
            
            "Taux pertes (%) Myrtillier": pertes_pr_myrt,
            "°Brix expédition Myrtillier": brix_exp_myrt,
            "Prix Export (DH/kg) Myrtillier": prix_exp_myrt,
            "Prix Local (DH/kg) Myrtillier": prix_loc_myrt,
            
            "Taux pertes (%) Mûrier": pertes_pr_mur,
            "Prix Export (DH/kg) Mûrier": prix_exp_mur,
            "Prix Local (DH/kg) Mûrier": prix_loc_mur,
            
            "Taux refus export (%)": refus_export,
            "Destination Export frais (%)": dest_export,
            "Destination Surgelé (%)": dest_surgele,
            "Destination Marché local (%)": dest_local,
            
            "Manque de normes nuit compétitivité ?": q38,
            "Adoption référentiel Top Performers": q39,
            "Conditions d'adoption": q39_conditions,
            "Principaux obstacles (choix)": ", ".join(obstacles),
            "Autre obstacle précisé": obstacle_autre
        }
        
        # (Tableau récapitulatif supprimé pour la vue Enquêteur comme demandé)
        
        dfs_to_export = {
            "framboisier": df_framboisier if 'df_framboisier' in locals() else pd.DataFrame(),
            "myrtillier": df_myrtillier if 'df_myrtillier' in locals() else pd.DataFrame(),
            "murier": df_murier if 'df_murier' in locals() else pd.DataFrame(),
            "substrat": edited_substrat if 'edited_substrat' in locals() else pd.DataFrame(),
            "eau": edited_eau if 'edited_eau' in locals() else pd.DataFrame(),
            "volumes": edited_volumes if 'edited_volumes' in locals() else pd.DataFrame(),
            
            # Bloc E - Framboisier
            "fert_framb": edited_fert_framb if 'edited_fert_framb' in locals() and edited_fert_framb is not None else pd.DataFrame(),
            "eng_framb": edited_eng_framb if 'edited_eng_framb' in locals() and edited_eng_framb is not None else pd.DataFrame(),
            "fol_framb": edited_fol_framb if 'edited_fol_framb' in locals() and edited_fol_framb is not None else pd.DataFrame(),
            # Bloc E - Myrtillier
            "fert_myrt": edited_fert_myrt if 'edited_fert_myrt' in locals() and edited_fert_myrt is not None else pd.DataFrame(),
            "eng_myrt": edited_eng_myrt if 'edited_eng_myrt' in locals() and edited_eng_myrt is not None else pd.DataFrame(),
            "fol_myrt": edited_fol_myrt if 'edited_fol_myrt' in locals() and edited_fol_myrt is not None else pd.DataFrame(),
            # Bloc E - Mûrier
            "fert_mur": edited_fert_mur if 'edited_fert_mur' in locals() and edited_fert_mur is not None else pd.DataFrame(),
            "eng_mur": edited_eng_mur if 'edited_eng_mur' in locals() and edited_eng_mur is not None else pd.DataFrame(),
            "fol_mur": edited_fol_mur if 'edited_fol_mur' in locals() and edited_fol_mur is not None else pd.DataFrame(),
            
            "phyto_framb": edited_phyto_framb if 'edited_phyto_framb' in locals() and edited_phyto_framb is not None else pd.DataFrame(),
            "trait_framb": edited_trait_framb if 'edited_trait_framb' in locals() and edited_trait_framb is not None else pd.DataFrame(),
            "aux_framb": edited_aux_framb if 'edited_aux_framb' in locals() and edited_aux_framb is not None else pd.DataFrame(),
            "rend_framb": edited_rend_framb if 'edited_rend_framb' in locals() and edited_rend_framb is not None else pd.DataFrame(),
            
            "phyto_myrt": edited_phyto_myrt if 'edited_phyto_myrt' in locals() and edited_phyto_myrt is not None else pd.DataFrame(),
            "trait_myrt": edited_trait_myrt if 'edited_trait_myrt' in locals() and edited_trait_myrt is not None else pd.DataFrame(),
            "aux_myrt": edited_aux_myrt if 'edited_aux_myrt' in locals() and edited_aux_myrt is not None else pd.DataFrame(),
            "rend_myrt": edited_rend_myrt if 'edited_rend_myrt' in locals() and edited_rend_myrt is not None else pd.DataFrame(),
            
            "phyto_mur": edited_phyto_mur if 'edited_phyto_mur' in locals() and edited_phyto_mur is not None else pd.DataFrame(),
            "trait_mur": edited_trait_mur if 'edited_trait_mur' in locals() and edited_trait_mur is not None else pd.DataFrame(),
            "aux_mur": edited_aux_mur if 'edited_aux_mur' in locals() and edited_aux_mur is not None else pd.DataFrame(),
            "rend_mur": edited_rend_mur if 'edited_rend_mur' in locals() and edited_rend_mur is not None else pd.DataFrame(),

            "personnel": edited_personnel if 'edited_personnel' in locals() else pd.DataFrame(),
            "jt": edited_jt if 'edited_jt' in locals() else pd.DataFrame(),
            "axes": edited_axes if 'edited_axes' in locals() else pd.DataFrame()
        }
        
        # Dictionnaire dédié pour l'identification de l'exploitation
        data_exploitation = {
            "Code Fiche": code_fiche,
            "Date Enquête": date_enquete.strftime("%Y-%m-%d"),
            "Enquêteur": enqueteur,
            "Culture(s) Enquêtée(s)": ", ".join(cultures),
            "Durée Enquête (h)": duree,
            "Nom & Prénom": nom_prenom,
            "Email": email,
            "Téléphone": telephone,
            "Fonction": fonction,
            "Formation": formation_autre if formation == "Autre" else formation,
            "Expérience Fruits Rouges (ans)": experience,
            "Nom Exploitation": nom_exploitation,
            "Commune / Douar": commune,
            "Zone": zone_autre if zone == "Autre" else zone,
            "Réseau Commercial": reseau_autre if reseau == "Autre" else reseau,
            "Certifications": ", ".join(certifications),
            "Date Dernier Audit": date_audit.strftime("%Y-%m-%d"),
            "Organisme Certificateur": organisme_certif,
            "Consentement": consentement
        }
        
        # Appel de l'export vers Google Sheets
        exporter_vers_gsheets(data, dfs_to_export, data_exploitation)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.success("🎉 Merci pour votre contribution ! L'enquête a été enregistrée avec succès.", icon="✅")
        st.balloons()
