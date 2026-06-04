import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

# ═══════════════════════════════════════════════════════════════
# CONNEXION GOOGLE SHEETS
# ═══════════════════════════════════════════════════════════════
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

        try:
            if hasattr(st, 'secrets') and "gcp_service_account" in st.secrets:
                try:
                    credentials_dict = dict(st.secrets["gcp_service_account"])
                    if "\\n" in credentials_dict.get("private_key", ""):
                        credentials_dict["private_key"] = credentials_dict["private_key"].replace("\\n", "\n")
                    credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
                except Exception as e:
                    st.warning(f"Impossible de lire vos secrets : {e}")
        except Exception:
            pass

        if credentials is None:
            fichier_json_local = "my-project-enquete-490718-7b1be08f8312.json"
            if os.path.exists(fichier_json_local):
                credentials = Credentials.from_service_account_file(fichier_json_local, scopes=scopes)
            elif os.path.exists(json_path):
                credentials = Credentials.from_service_account_file(json_path, scopes=scopes)
            else:
                st.error(f"Fichier secret introuvable.")
                return None, None

        gc = gspread.authorize(credentials)
        sh = gc.open_by_url(SHEET_URL)
        return gc, sh
    except Exception as e:
        st.error(f"Erreur d'authentification Google Sheets : {e}")
        return None, None


# ═══════════════════════════════════════════════════════════════
# EXPORT VERS GOOGLE SHEETS (pivot filtrable)
# ═══════════════════════════════════════════════════════════════
def exporter_vers_gsheets(data, dfs, data_identification=None):
    gc, sh = get_gspread_client()
    if sh is None:
        return

    try:
        import time
        from datetime import datetime

        code_fiche = data.get("Code Fiche", "Sans_Code")
        date_str = data.get("Date Enquête", datetime.now().strftime("%Y-%m-%d"))

        def retry_api(func, *args, **kwargs):
            max_retries = 5
            for i in range(max_retries):
                try:
                    res = func(*args, **kwargs)
                    time.sleep(1.2)
                    return res
                except Exception as e:
                    if "429" in str(e) or "Quota" in str(e):
                        if i < max_retries - 1:
                            time.sleep((2 ** i) + 2)
                        else:
                            raise e
                    else:
                        raise e

        def formater_entete(onglet):
            try:
                retry_api(onglet.freeze, rows=1)
                retry_api(onglet.format, "A1:ZZ1", {
                    "backgroundColor": {"red": 0.11, "green": 0.42, "blue": 0.24},
                    "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 10},
                    "horizontalAlignment": "CENTER",
                    "wrapStrategy": "WRAP"
                })
            except Exception:
                pass

        def aplatir_df(prefix, df):
            result = {}
            if df is None or df.empty:
                return result
            rows_valides = [row for _, row in df.iterrows()
                            if any(str(v).strip() not in ("", "0", "0.0", "nan", "None") for v in row.values)]
            if not rows_valides:
                return result
            for i, row in enumerate(rows_valides, 1):
                for col in df.columns:
                    key = f"{prefix} | {col}" if len(rows_valides) == 1 else f"{prefix} L{i} | {col}"
                    result[key] = str(row[col]) if str(row[col]) not in ("nan", "None") else ""
            return result

        with st.spinner("📊 Enregistrement en cours..."):

            # Construire ligne pivot
            pivot_row = {}
            if data_identification:
                for k, v in data_identification.items():
                    pivot_row[k] = str(v)
            for k, v in data.items():
                if k not in pivot_row:
                    pivot_row[k] = str(v)

            blocs = [
                ("B-Variétés", dfs.get("varietes")),
                ("B2-Densité", dfs.get("densite")),
                ("C-Substrat", dfs.get("substrat")),
                ("D-Eau", dfs.get("eau")),
                ("D-Volumes", dfs.get("volumes")),
                ("E-Fertigation", dfs.get("fertigation")),
                ("F-Pesticides", dfs.get("pesticides")),
                ("G-MO", dfs.get("mo")),
                ("H-Biostim", dfs.get("biostim")),
                ("I-Regulateurs", dfs.get("regulateurs")),
            ]
            for prefix, df_b in blocs:
                pivot_row.update(aplatir_df(prefix, df_b))

            pivot_row["Date Synchro"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Tableau Récapitulatif (pivot)
            nom_recap = "Tableau Récapitulatif"
            try:
                recap = retry_api(sh.worksheet, nom_recap)
                existing_headers = retry_api(recap.row_values, 1)
                header_exists = len(existing_headers) > 0
            except gspread.exceptions.WorksheetNotFound:
                recap = retry_api(sh.add_worksheet, title=nom_recap, rows="500", cols="500")
                header_exists = False
                existing_headers = []

            if not header_exists:
                headers = list(pivot_row.keys())
                retry_api(recap.update, 'A1', [headers])
                formater_entete(recap)
                existing_headers = headers
            else:
                new_cols = [k for k in pivot_row.keys() if k not in existing_headers]
                if new_cols:
                    existing_headers.extend(new_cols)
                    retry_api(recap.update, 'A1', [existing_headers])

            row_data = [pivot_row.get(h, "") for h in existing_headers]
            retry_api(recap.append_row, row_data)

            try:
                retry_api(recap.set_basic_filter)
            except Exception:
                pass

            # Feuille détaillée par enquête
            nom_feuille = f"{code_fiche} - {date_str}"
            try:
                detail = retry_api(sh.worksheet, nom_feuille)
                retry_api(detail.clear)
            except gspread.exceptions.WorksheetNotFound:
                detail = retry_api(sh.add_worksheet, title=nom_feuille, rows="2000", cols="30")

            detail_rows = []
            detail_rows.append([f"📋 ENQUÊTE FRAMBOISE : {code_fiche}", f"Date : {date_str}"])
            detail_rows.append([""])

            if data_identification:
                detail_rows.append(["── IDENTIFICATION ──"])
                detail_rows.append(list(data_identification.keys()))
                detail_rows.append([str(v) for v in data_identification.values()])
                detail_rows.append([""])

            detail_rows.append(["── DONNÉES ENQUÊTE ──"])
            for k, v in data.items():
                detail_rows.append([str(k), str(v)])

            blocs_labels = [
                ("🌿 BLOC B — Variétés Framboise", dfs.get("varietes")),
                ("📐 BLOC B2 — Densité de Plantation", dfs.get("densite")),
                ("📦 BLOC 0 — Rendements", dfs.get("rendements")),
                ("🌱 BLOC C — Substrat", dfs.get("substrat")),
                ("💧 BLOC D — Eau", dfs.get("eau")),
                ("💧 BLOC D — Volumes Irrigation", dfs.get("volumes")),
                ("🧪 BLOC E — Fertigation", dfs.get("fertigation")),
                ("🛡️ BLOC F — Pesticides", dfs.get("pesticides")),
                ("👷 BLOC G — Main d'Œuvre", dfs.get("mo")),
                ("🌿 BLOC H — Biostimulants", dfs.get("biostim")),
                ("⚗️ BLOC I — Régulateurs", dfs.get("regulateurs")),
            ]

            for titre, df_b in blocs_labels:
                if df_b is not None and not df_b.empty:
                    has_data = any(
                        any(str(v).strip() not in ("", "0", "0.0", "nan", "None") for v in row.values)
                        for _, row in df_b.iterrows()
                    )
                    if has_data:
                        detail_rows.append([""])
                        detail_rows.append([f"── {titre} ──"])
                        detail_rows.append([str(c) for c in df_b.columns.tolist()])
                        for _, row in df_b.iterrows():
                            if any(str(v).strip() not in ("", "0", "0.0", "nan", "None") for v in row.values):
                                detail_rows.append([str(v) if str(v) not in ("nan", "None") else "" for v in row.values])

            if detail_rows:
                max_cols = max(len(r) for r in detail_rows)
                for r in detail_rows:
                    while len(r) < max_cols:
                        r.append("")
                retry_api(detail.update, f"A1:AZ{len(detail_rows)}", detail_rows)

            try:
                retry_api(detail.format, "A1:AZ1", {
                    "backgroundColor": {"red": 0.11, "green": 0.42, "blue": 0.24},
                    "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 12}
                })
            except Exception:
                pass

        st.success(f"✅ Enquête **{code_fiche}** enregistrée — Feuille « {nom_feuille} » + Tableau Récapitulatif mis à jour !")

    except Exception as e:
        st.error(f"Erreur lors de la synchronisation GSheets : {e}")


# ═══════════════════════════════════════════════════════════════
# DONNÉES DE RÉFÉRENCE (issues du fichier enquet refer.xlsx)
# ═══════════════════════════════════════════════════════════════

ENGRAIS_COMPOSITION = {
    "20.20.20":                     {"Composition": "20.0-20.0-20.0", "Unité": "KG"},
    "ACIDE NITRIQUE":               {"Composition": "13.0-0-0",       "Unité": "KG"},
    "ACIDE PHOSPHORIQUE":           {"Composition": "0-61.5-0",       "Unité": "KG"},
    "ACTI FERT MIX EN 5KG":         {"Composition": "20.0-10.0-10.0", "Unité": "KG"},
    "AGRIPOTASSE":                  {"Composition": "0-0-60.0",       "Unité": "L"},
    "AMMONITRATE":                  {"Composition": "33.5-0-0",       "Unité": "KG"},
    "AZOTO 30":                     {"Composition": "30.0-0-0",       "Unité": "litre"},
    "BORAMINE CALCIUM":             {"Composition": "7.0-0-0",        "Unité": "litre"},
    "FLORASTARTE":                  {"Composition": "12.0-52.0-5.0",  "Unité": "KG"},
    "FOLICIST 20L":                 {"Composition": "0-20.0-0",       "Unité": "L"},
    "FOLUR":                        {"Composition": "46.0-0-0",       "Unité": "L"},
    "HIMIFERT 5KG":                 {"Composition": "5.0-15.0-30.0",  "Unité": "KG"},
    "HYDRO GOLD":                   {"Composition": "15.0-5.0-25.0",  "Unité": "U"},
    "KAMASOL BLACK":                {"Composition": "0-0-25.0",       "Unité": "L"},
    "L'UREE":                       {"Composition": "46.0-0-0",       "Unité": "litre"},
    "M.K.P":                        {"Composition": "0-52.0-34.0",    "Unité": "KG"},
    "MAP":                          {"Composition": "12.0-61.0-0",    "Unité": "KG"},
    "MGO":                          {"Composition": "0-0-0",          "Unité": "KG"},
    "NITRATE DE CHAUX":             {"Composition": "15.5-0-0",       "Unité": "KG"},
    "NITRATE MAGNESIE":             {"Composition": "11.0-0-0",       "Unité": "KG"},
    "NITRATE POTASSE":              {"Composition": "13.0-0-46.0",    "Unité": "KG"},
    "NITROSTAR":                    {"Composition": "30.0-0-0",       "Unité": "KG"},
    "NOVATEC 21%":                  {"Composition": "21.0-0-0",       "Unité": "L"},
    "NOVATEC N FLUID":              {"Composition": "28.0-0-0",       "Unité": "unite"},
    "OLIGOMAG (Magnesieum)":        {"Composition": "0-0-0",          "Unité": "KG"},
    "PENALTY":                      {"Composition": "0-21.0-0",       "Unité": "L"},
    "SENIPHOS":                     {"Composition": "3.0-20.0-0",     "Unité": "L"},
    "STAR CAL":                     {"Composition": "5.0-0-0",        "Unité": "L"},
    "STAR SOL":                     {"Composition": "15.0-5.0-30.0",  "Unité": "litre"},
    "SULFATE DAMMONIAQUE":          {"Composition": "21.0-0-0",       "Unité": "KG"},
    "SULFATE DE POTASSE (solucros)":{"Composition": "0-0-51.0",       "Unité": "KG"},
    "VYTEGRIS HI CA 5L":            {"Composition": "6.0-0-0",        "Unité": "L"},
}

PESTICIDES_REF = [
    {"Catégorie": "Acaricide",           "Produit commercial": "ACRAMAIT",            "Matière active": "Abamectine+Clofentézine",      "Unité": "L",      "Dose ONSSA": "0.5–1.0 L/ha",    "DAR": "7 j"},
    {"Catégorie": "Acaricide",           "Produit commercial": "APOLLO",              "Matière active": "Clofentézine 500g/L",           "Unité": "L",      "Dose ONSSA": "0.3–0.5 L/ha",    "DAR": "30 j"},
    {"Catégorie": "Acaricide",           "Produit commercial": "FORMOL EN 34 KG",     "Matière active": "Formaldéhyde 34%",              "Unité": "KG",     "Dose ONSSA": "10–20 L/100m²",   "DAR": "—"},
    {"Catégorie": "Acaricide",           "Produit commercial": "MASAMITE",            "Matière active": "Bifénazate 480g/L",             "Unité": "KG",     "Dose ONSSA": "0.75–1.0 L/ha",   "DAR": "3 j"},
    {"Catégorie": "Acaricide",           "Produit commercial": "MILBEKNOCK 500 CC",   "Matière active": "Milbémectine 9.5g/L",           "Unité": "L",      "Dose ONSSA": "0.5–1.0 L/ha",    "DAR": "3 j"},
    {"Catégorie": "Fongicide",           "Produit commercial": "DIVOSAN",             "Matière active": "Acide peracétique+H2O2",        "Unité": "L",      "Dose ONSSA": "1–2 L/100L",      "DAR": "0 j"},
    {"Catégorie": "Fongicide",           "Produit commercial": "FLINT WG50 EN 1KG",   "Matière active": "Trifloxystrobine 500g/kg",      "Unité": "KG",     "Dose ONSSA": "0.10–0.15 kg/ha", "DAR": "7 j"},
    {"Catégorie": "Fongicide",           "Produit commercial": "LUNA EN 1L",          "Matière active": "Fluopyram 400g/L",              "Unité": "litre",  "Dose ONSSA": "0.5–0.75 L/ha",   "DAR": "7 j"},
    {"Catégorie": "Fongicide",           "Produit commercial": "PHYTOSTEP 10 000",    "Matière active": "Bacillus subtilis QST713",      "Unité": "Flacon", "Dose ONSSA": "1–2 kg/ha",       "DAR": "0 j"},
    {"Catégorie": "Fongicide",           "Produit commercial": "PREVICUR",            "Matière active": "Propamocarbe 722g/L",           "Unité": "litre",  "Dose ONSSA": "1.5–3.0 L/ha",    "DAR": "3 j"},
    {"Catégorie": "Fongicide",           "Produit commercial": "PRIORI TOP EN 1L",    "Matière active": "Azoxystrobine+Difénoconazole",  "Unité": "L",      "Dose ONSSA": "0.5–0.75 L/ha",   "DAR": "14 j"},
    {"Catégorie": "Fongicide",           "Produit commercial": "SIGNUM",              "Matière active": "Boscalide+Pyraclostrobine",     "Unité": "KG",     "Dose ONSSA": "0.5–0.75 kg/ha",  "DAR": "7 j"},
    {"Catégorie": "Fongicide",           "Produit commercial": "SWITCH 62,5 WG",      "Matière active": "Cyprodinil+Fludioxonil",        "Unité": "KG",     "Dose ONSSA": "0.6–0.8 kg/ha",   "DAR": "7 j"},
    {"Catégorie": "Insecticide",         "Produit commercial": "AVAUNT 150 EC-1L",    "Matière active": "Indoxacarbe 150g/L",            "Unité": "L",      "Dose ONSSA": "0.25–0.35 L/ha",  "DAR": "3 j"},
    {"Catégorie": "Insecticide",         "Produit commercial": "BENEVIA",             "Matière active": "Cyantraniliprole 100g/L",       "Unité": "L",      "Dose ONSSA": "0.75–1.0 L/ha",   "DAR": "3 j"},
    {"Catégorie": "Insecticide",         "Produit commercial": "INSECTISIDE 101",     "Matière active": "Pyréthroïde+huile",             "Unité": "L",      "Dose ONSSA": "1.0–1.5 L/ha",    "DAR": "3 j"},
    {"Catégorie": "Insecticide",         "Produit commercial": "KARATE",              "Matière active": "Lambda-cyhalothrine 50g/L",     "Unité": "L",      "Dose ONSSA": "0.1–0.15 L/ha",   "DAR": "7 j"},
    {"Catégorie": "Insecticide",         "Produit commercial": "MOVENTO",             "Matière active": "Spirotétramate 150g/L",         "Unité": "litre",  "Dose ONSSA": "0.5–0.75 L/ha",   "DAR": "21 j"},
    {"Catégorie": "Insecticide",         "Produit commercial": "PYRECRIS",            "Matière active": "Pyréthrine naturelle",          "Unité": "L",      "Dose ONSSA": "0.5–1.0 L/ha",    "DAR": "1 j"},
    {"Catégorie": "Insecticide",         "Produit commercial": "RADIANT",             "Matière active": "Spinetoram 120g/L",             "Unité": "litre",  "Dose ONSSA": "0.15–0.25 L/ha",  "DAR": "3 j"},
    {"Catégorie": "Insecticide",         "Produit commercial": "VERIMARK",            "Matière active": "Cyantraniliprole 200g/L",       "Unité": "L",      "Dose ONSSA": "0.5–0.75 L/ha",   "DAR": "3 j"},
    {"Catégorie": "Insecticide-Acaricide","Produit commercial": "VERTIMEC",           "Matière active": "Abamectine 18g/L",              "Unité": "litre",  "Dose ONSSA": "0.5–1.0 L/ha",    "DAR": "45 j"},
]

BIOSTIMULANTS_LISTE = [
    "A44 ESTIMULANTE", "ACTI FERT MIX EN 5KG", "AGRIPOTASSE", "ALGA 600",
    "ALGABORN EN 5 L", "ALGICROP EN 20L", "ALGOUBAZ", "BASFOLIAR FRUIT SP",
    "BEST AMINO (AA)", "BETAMINE", "BIOFORGE", "BIOROOT POWER", "BLACK JACK",
    "BORAMINE CALCIUM", "BOTCIDE", "CODACIDE 25 L", "DISPER BLOOM GS EN 1KG",
    "DISPER CHLOROPHYL", "DISPER HUMIC EN 20 KG", "ECOVIGOR", "FOLIASTIM MN ZN 5L",
    "FOLIASTIM PURE ALGUE 20L", "FOLICIST 20L", "FOLUR", "GREEN UP", "GREENSTIM",
    "GROW QUICK", "GZ", "HIMIFERT 5KG", "HYDRO GOLD", "ICY ANTISALT", "ICY SILICON",
    "INICIUM EN 20 LT", "ISABION 20L", "KAMASOL BLACK", "KUMULUS", "LEILI 2000 EN 1L",
    "LIOKIL EN 10LT (UV L)", "NO SAL", "NOVATEC 21%", "NOVATEC N FLUID", "NUTRAMIN 20 L",
    "OLIGO MIX", "ORGA MASSI", "PENALTY", "PHYLGREEN 100%", "RAI EN 5 LT",
    "RHIZO AMINE", "RHIZO HUMUS", "ROMBIQUEL ZN/MN EXTRA", "ROOT MOST", "RUTER",
    "SAVON BELDIE", "SENIPHOS", "SEQUESTRINE", "SILI-MAX", "STAR CAL", "STAR SOL",
    "SULFATE DE CUIVRE", "SUP-OXON", "SYPRA", "VYTEGRIS HI CA 5L",
]

REGULATEURS_LISTE = ["ACCEL 40SG", "BERELEX 40 SG EN 2,5 GR", "FALGRO", "PROMALIN"]

MO_OPERATIONS = [
    "Arrachage", "Désherbages", "Emballage", "Entretien Structure", "Extra Pointage",
    "Installation hors sol", "Irrigation", "MO Mensuel_Chargé", "Nettoyage", "Palissage",
    "Plantation", "Récolte", "Traitement phytosanitaire & fertilisation foliaire",
    "Travaux sol", "service générale",
]


# ═══════════════════════════════════════════════════════════════
# PAGE CONFIG & CSS
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Enquête Framboise — Référentiel Technique",
    page_icon="🍓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&display=swap');

:root {
    --primary: #1B6B3A;
    --primary-light: #2D8F4E;
    --primary-dark: #0F4D28;
    --accent: #E8453C;
    --bg: #F8FAFC;
    --card: #FFFFFF;
    --text: #1E293B;
    --text-sec: #64748B;
    --border: #E2E8F0;
    --shadow: 0 4px 6px rgba(0,0,0,0.05);
    --grad: linear-gradient(135deg, #1B6B3A 0%, #2D8F4E 100%);
}

.stApp { background: var(--bg) !important; font-family: 'Inter', sans-serif !important; }
::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-thumb { background: var(--primary); border-radius: 4px; }

.block-container { padding: 1.5rem 2.5rem 4rem !important; max-width: 1500px !important; }

.hero {
    background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 50%, #F0FDF4 100%);
    border-radius: 20px; padding: 2rem 2.5rem; margin-bottom: 1.5rem;
    border: 1px solid #D1FAE5; box-shadow: var(--shadow); position: relative; overflow: hidden;
}
.hero::before {
    content: ''; position: absolute; top: -40%; right: -10%; width: 350px; height: 350px;
    background: radial-gradient(circle, rgba(45,143,78,0.12) 0%, transparent 70%);
    border-radius: 50%; animation: pulse 6s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{transform:scale(1);opacity:.6} 50%{transform:scale(1.1);opacity:1} }
.hero-title { font-family:'Outfit',sans-serif; font-size:2rem; font-weight:800;
    background: linear-gradient(135deg,#0F4D28,#1B6B3A); -webkit-background-clip:text;
    -webkit-text-fill-color:transparent; background-clip:text; margin-bottom:0.3rem; }
.hero-sub { font-size:1rem; color:#166534; font-weight:400; }
.hero-badge {
    display:inline-flex; align-items:center; gap:6px; background:#fff;
    border:1px solid rgba(45,143,78,.3); border-radius:50px; padding:5px 14px;
    font-size:.78rem; color:#15803D; font-weight:600; margin-top:.8rem;
    box-shadow:0 2px 4px rgba(0,0,0,.05);
}

.bloc-header {
    background: var(--grad); border-radius: 12px; padding: 0.8rem 1.2rem;
    margin: 1.2rem 0 0.8rem; color: white; font-family:'Outfit',sans-serif;
    font-size: 1rem; font-weight: 700; display:flex; align-items:center; gap:8px;
}
.bloc-subheader {
    background: #EFF6FF; border-left: 4px solid #3B82F6; border-radius: 0 8px 8px 0;
    padding: 0.6rem 1rem; margin: 0.8rem 0 0.5rem; color: #1D4ED8;
    font-weight: 600; font-size: 0.9rem;
}
.info-card {
    background: var(--card); border: 1px solid var(--border); border-radius: 14px;
    padding: 1.2rem; margin-bottom: 1.2rem; box-shadow: var(--shadow);
}
.info-card-title { font-family:'Outfit',sans-serif; font-size:.95rem; font-weight:700;
    color:var(--primary-light); margin-bottom:.8rem; display:flex; align-items:center; gap:6px; }

h2 { font-family:'Outfit',sans-serif !important; font-weight:700 !important; font-size:1.4rem !important;
    color:var(--text) !important; padding-bottom:.4rem !important; border-bottom:2px solid var(--border) !important; }
h3 { font-family:'Outfit',sans-serif !important; font-weight:600 !important; font-size:1.05rem !important; color:var(--primary-light) !important; }

.stTabs [data-baseweb="tab-list"] {
    background: var(--card); border-radius: 14px; padding: 5px; gap: 3px;
    border: 1px solid var(--border); box-shadow: var(--shadow); flex-wrap: wrap;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important; padding: 8px 14px !important; font-size: .78rem !important;
    font-weight: 500 !important; color: var(--text-sec) !important; background: transparent !important;
    border: none !important; transition: all .2s ease !important; white-space: nowrap !important;
}
.stTabs [data-baseweb="tab"]:hover { background: rgba(45,143,78,.1) !important; color: var(--primary-light) !important; }
.stTabs [aria-selected="true"] { background: var(--grad) !important; color: white !important;
    font-weight: 700 !important; box-shadow: 0 2px 10px rgba(27,107,58,.35) !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none !important; }

.stTextInput > div > div, .stNumberInput > div > div > input,
.stDateInput > div > div, .stSelectbox > div > div, .stMultiSelect > div > div {
    background: #fff !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > div:focus-within, .stSelectbox > div > div:focus-within,
.stMultiSelect > div > div:focus-within {
    border-color: var(--primary-light) !important; box-shadow: 0 0 0 3px rgba(45,143,78,.12) !important;
}

.stButton > button {
    background: var(--grad) !important; color: white !important; border: none !important;
    border-radius: 12px !important; padding: .7rem 2.5rem !important; font-weight: 700 !important;
    font-size: .95rem !important; transition: all .3s ease !important;
    box-shadow: 0 4px 15px rgba(27,107,58,.3) !important;
}
.stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 6px 25px rgba(27,107,58,.5) !important; }

.stDataFrame, [data-testid="stDataEditor"] { border-radius: 10px !important; border: 1px solid var(--border) !important; overflow: hidden; }
.stMultiSelect [data-baseweb="tag"] { background: rgba(45,143,78,.15) !important; color: var(--primary-light) !important; border-radius:6px !important; }
hr { border-color: var(--border) !important; margin: 1.2rem 0 !important; }
#MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# HERO HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
    <div class="hero-title">🍓 Enquête Terrain — Référentiel Framboise</div>
    <div class="hero-sub">Élaboration du Référentiel Technique de Production — Souss-Massa</div>
    <div class="hero-badge"><span>📋</span><span>Campagne 2025/2026</span></div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# EN-TÊTE DE L'ENQUÊTE (hors tabs)
# ═══════════════════════════════════════════════════════════════
st.markdown('<div class="info-card"><div class="info-card-title">📌 Informations Générales</div></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    code_fiche  = st.text_input("🏷️ Code Fiche", placeholder="Ex: FR-001")
    date_enquete = st.date_input("📅 Date Enquête", value=date.today())
with col2:
    enqueteur   = st.text_input("👤 Enquêteur", placeholder="Nom complet")
    cultures    = st.multiselect("🌱 Culture(s)", ["Framboisier"], default=["Framboisier"])
with col3:
    duree       = st.number_input("⏱️ Durée (h)", min_value=0.0, step=0.5)
    profil      = st.selectbox("📂 Profil Exploitation", ["Standard", "Top Performer", "Débutant", "En reconversion"])

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# TABS PRINCIPAUX
# ═══════════════════════════════════════════════════════════════
tab_a, tab_b, tab_c, tab_d, tab_e, tab_f, tab_g, tab_h, tab_i = st.tabs([
    "🏠 A · Identification",
    "🌿 B · Variétés & Plantation",
    "🌱 C · Substrat",
    "💧 D · Eau & Irrigation",
    "🧪 E · Fertigation",
    "🛡️ F · Pesticides",
    "👷 G · Main d'Œuvre",
    "🌿 H · Biostimulants",
    "⚗️ I · Régulateurs",
])


# ══════════════════════════════════════════════════════════════
# TAB A — IDENTIFICATION
# ══════════════════════════════════════════════════════════════
with tab_a:
    st.markdown('<div class="bloc-header">🏠 BLOC A — Identification de l\'Exploitation et du Producteur</div>', unsafe_allow_html=True)

    st.markdown('<div class="bloc-subheader">👤 Informations personnelles</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        nom_prenom  = st.text_input("Nom & Prénom")
        email       = st.text_input("Email")
        telephone   = st.text_input("Téléphone")
    with col2:
        fonction    = st.selectbox("Fonction", ["Propriétaire", "Directeur technique", "Chef de culture", "Technicien"])
        formation   = st.selectbox("Formation", ["Sans formation", "Technicien agricole", "Ingénieur agronome", "Autre"])
        formation_autre = ""
        if formation == "Autre":
            formation_autre = st.text_input("Précisez la formation")
        experience  = st.number_input("Expérience en fruits rouges (ans)", min_value=0, step=1)

    st.markdown('<div class="bloc-subheader">🏡 Identification de l\'exploitation</div>', unsafe_allow_html=True)
    col3, col4 = st.columns(2)
    with col3:
        nom_exploitation = st.text_input("Nom Exploitation")
        commune          = st.text_input("Commune / Douar")
        zone = st.selectbox("Zone", ["Ait Amira", "Biougra", "Belfaa-Massa", "Sidi Bibi", "Oulad Teima", "Tifnit", "Autre"])
        zone_autre = ""
        if zone == "Autre":
            zone_autre = st.text_input("Précisez la zone")
    with col4:
        reseau = st.selectbox("Réseau Commercial", ["Driscoll's", "Atlas Farming", "Coopérative", "Indépendant", "Autre"])
        reseau_autre = ""
        if reseau == "Autre":
            reseau_autre = st.text_input("Précisez le réseau")
        certifications = st.multiselect("Certifications", ["GlobalG.A.P.", "BRCGS Food Safety", "SMETA / GRASP", "Aucune", "En cours"])
        date_audit     = st.date_input("Date Dernier Audit", value=date.today())
        organisme_certif = st.text_input("Organisme Certificateur")

    st.markdown('<div class="bloc-subheader">✅ Consentement</div>', unsafe_allow_html=True)
    consentement = st.radio("Consentement à l'utilisation des données pour le référentiel technique", ["Oui", "Non"], horizontal=True)


# ══════════════════════════════════════════════════════════════
# TAB B — VARIÉTÉS & PLANTATION
# ══════════════════════════════════════════════════════════════
with tab_b:
    st.markdown('<div class="bloc-header">🌿 BLOC B — Variétés Framboise</div>', unsafe_allow_html=True)

    st.write("Saisir les variétés cultivées sur l'exploitation :")
    df_varietes_init = pd.DataFrame([{
        "Variété": "", "Superficie (ha)": 0.0, "Fournisseur plants": "",
        "Origine plants": "", "Coût plant (DH)": 0.0, "Âge plantation (ans)": 0
    }])
    df_varietes = st.data_editor(df_varietes_init, num_rows="dynamic", use_container_width=True, key="varietes")

    st.divider()
    st.markdown('<div class="bloc-header">📐 BLOC B2 — Densité de Plantation</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        densite_ha  = st.number_input("Densité (plants/ha)", min_value=0)
        ecar_inter  = st.number_input("Écartement inter-rang (cm)", min_value=0.0, format="%.1f")
    with col2:
        ecar_rang   = st.number_input("Écartement sur rang (cm)", min_value=0.0, format="%.1f")
        cannes_pot  = st.number_input("Cannes / pot", min_value=0)
    with col3:
        vol_pot     = st.number_input("Volume pot (L)", min_value=0.0, format="%.1f")
        nb_plants   = st.number_input("Nb plants total", min_value=0)

    df_densite = pd.DataFrame([{
        "Densité (plants/ha)": densite_ha,
        "Écart. inter-rang (cm)": ecar_inter,
        "Écart. sur rang (cm)": ecar_rang,
        "Cannes / pot": cannes_pot,
        "Volume pot (L)": vol_pot,
        "Nb plants total": nb_plants
    }])

    st.divider()
    st.markdown('<div class="bloc-header">📦 BLOC 0 — Rendements</div>', unsafe_allow_html=True)

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        rdt_ha      = st.number_input("Rendement (t/ha)", min_value=0.0, format="%.2f")
    with col_r2:
        rdt_plant   = st.number_input("Rendement (kg/plant)", min_value=0.0, format="%.3f")
    with col_r3:
        rdt_export  = st.number_input("% Export", min_value=0.0, max_value=100.0, format="%.1f")

    df_rendements = pd.DataFrame([{
        "RENDEMENT/HA (t/ha)": rdt_ha,
        "Rendement (kg/plant)": rdt_plant,
        "% Export": rdt_export
    }])


# ══════════════════════════════════════════════════════════════
# TAB C — SUBSTRAT
# ══════════════════════════════════════════════════════════════
with tab_c:
    st.markdown('<div class="bloc-header">🌱 BLOC C — Substrat</div>', unsafe_allow_html=True)
    st.write("Composition et coût du substrat utilisé :")

    df_substrat_init = pd.DataFrame([
        {"Composant": "Fibre de coco (coir)", "% Volumique": 0.0, "Coût (DH/m³)": 0.0},
        {"Composant": "Perlite",              "% Volumique": 0.0, "Coût (DH/m³)": 0.0},
        {"Composant": "Tourbe blonde",         "% Volumique": 0.0, "Coût (DH/m³)": 0.0},
        {"Composant": "Autre",                 "% Volumique": 0.0, "Coût (DH/m³)": 0.0},
    ])
    df_substrat = st.data_editor(df_substrat_init, hide_index=True, use_container_width=True, key="substrat")

    st.divider()
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        ph_substrat = st.number_input("pH substrat", min_value=0.0, max_value=14.0, format="%.1f")
        ce_substrat = st.number_input("CE substrat (dS/m)", min_value=0.0, format="%.2f")
    with col_s2:
        renouvellement = st.selectbox("Renouvellement substrat", ["Chaque cycle", "Tous les 2 ans", "Non renouvelé"])
        cout_renouv    = st.number_input("Coût renouvellement (DH/ha)", min_value=0.0)
    with col_s3:
        porosite        = st.number_input("Porosité totale (%)", min_value=0.0, max_value=100.0)
        retention_eau   = st.number_input("Capacité rétention eau (%)", min_value=0.0, max_value=100.0)


# ══════════════════════════════════════════════════════════════
# TAB D — EAU & IRRIGATION
# ══════════════════════════════════════════════════════════════
with tab_d:
    st.markdown('<div class="bloc-header">💧 BLOC D — Sources d\'Eau</div>', unsafe_allow_html=True)

    df_eau_init = pd.DataFrame([
        {"Type": "Forage",   "Débit (m³/h)": 0.0, "CE brute (dS/m)": 0.0, "pH brut": 0.0, "Coût (DH/m³)": 0.0, "Part mélange (%)": 0},
        {"Type": "Dessalée", "Débit (m³/h)": 0.0, "CE brute (dS/m)": 0.0, "pH brut": 0.0, "Coût (DH/m³)": 0.0, "Part mélange (%)": 0},
        {"Type": "Barrage",  "Débit (m³/h)": 0.0, "CE brute (dS/m)": 0.0, "pH brut": 0.0, "Coût (DH/m³)": 0.0, "Part mélange (%)": 0},
    ])
    df_eau = st.data_editor(df_eau_init, hide_index=True, use_container_width=True, key="eau")

    st.divider()
    st.markdown('<div class="bloc-header">💧 Volumes d\'Irrigation par Profil</div>', unsafe_allow_html=True)
    st.write("Volumes annuels (m³/ha) par profil/variété :")

    df_volumes_init = pd.DataFrame([{
        "Profil": "", "Variété": "", "Culture": "Framboisier",
        "Eau Barrage (m³/ha)": 0.0, "Eau Dessalée (m³/ha)": 0.0, "Eau Totale (m³/ha)": 0.0
    }])
    df_volumes = st.data_editor(df_volumes_init, num_rows="dynamic", use_container_width=True, key="volumes")

    st.divider()
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        ce_solution    = st.number_input("CE solution nutritive (dS/m)", min_value=0.0, format="%.2f")
        ce_drainage    = st.number_input("CE drainage (dS/m)", min_value=0.0, format="%.2f")
    with col_d2:
        fraction_les   = st.number_input("Fraction lessivage (%)", min_value=0.0, max_value=100.0)
        nb_apports_j   = st.number_input("Nb apports/jour", min_value=0)
    with col_d3:
        duree_apport   = st.number_input("Durée apport (min)", min_value=0.0)
        freq_drainage  = st.number_input("Fréquence mesure drainage (fois/sem)", min_value=0)


# ══════════════════════════════════════════════════════════════
# TAB E — FERTIGATION
# ══════════════════════════════════════════════════════════════
with tab_e:
    st.markdown('<div class="bloc-header">🧪 BLOC E — Fertigation Framboise</div>', unsafe_allow_html=True)
    st.info("💡 Remplissez uniquement la colonne **Qté (kg ou L/ha)**. La composition N-P-K est pré-remplie depuis le référentiel.")

    # Préparer le DataFrame avec produits prédéfinis
    fert_rows = []
    for produit, info in ENGRAIS_COMPOSITION.items():
        npk = info["Composition"].split("-") if "-" in info["Composition"] else ["0", "0", "0"]
        n_val = float(npk[0]) if len(npk) > 0 else 0.0
        p_val = float(npk[1]) if len(npk) > 1 else 0.0
        k_val = float(npk[2]) if len(npk) > 2 else 0.0
        fert_rows.append({
            "Engrais commercial": produit,
            "Composition (N-P-K)": info["Composition"],
            "Qté (kg ou L/ha)": None,
            "Unité": info["Unité"],
            "N (kg/ha)": n_val,
            "P₂O₅ (kg/ha)": p_val,
            "K₂O (kg/ha)": k_val,
            "CaO (kg/ha)": 0.0,
            "MgO (kg/ha)": 0.0,
            "S (kg/ha)": 0.0,
            "Fe (kg/ha)": 0.0,
            "B (kg/ha)": 0.0,
            "Cu (kg/ha)": 0.0,
            "Zn (kg/ha)": 0.0,
            "Mn (kg/ha)": 0.0,
            "Mo (kg/ha)": 0.0,
        })
    df_fert_init = pd.DataFrame(fert_rows)

    df_fertigation = st.data_editor(
        df_fert_init,
        hide_index=True,
        use_container_width=True,
        key="fertigation",
        column_config={
            "Engrais commercial": st.column_config.TextColumn("Engrais commercial", disabled=True, width="medium"),
            "Composition (N-P-K)": st.column_config.TextColumn("Composition", disabled=True, width="small"),
            "Unité": st.column_config.TextColumn("Unité", disabled=True, width="small"),
            "Qté (kg ou L/ha)": st.column_config.NumberColumn("Qté (kg ou L/ha)", min_value=0.0, format="%.2f"),
        }
    )

    st.markdown('<div class="bloc-subheader">📊 Total apports calculés</div>', unsafe_allow_html=True)
    df_fert_filled = df_fertigation[df_fertigation["Qté (kg ou L/ha)"].notna() & (df_fertigation["Qté (kg ou L/ha)"] > 0)]
    if not df_fert_filled.empty:
        totaux = {col: df_fert_filled[col].sum() for col in ["N (kg/ha)", "P₂O₅ (kg/ha)", "K₂O (kg/ha)", "CaO (kg/ha)", "MgO (kg/ha)", "S (kg/ha)"]}
        cols_tot = st.columns(6)
        for i, (k, v) in enumerate(totaux.items()):
            cols_tot[i].metric(k, f"{v:.1f}")


# ══════════════════════════════════════════════════════════════
# TAB F — PESTICIDES
# ══════════════════════════════════════════════════════════════
with tab_f:
    st.markdown('<div class="bloc-header">🛡️ BLOC F — Pesticides & Protection Phytosanitaire</div>', unsafe_allow_html=True)
    st.info("💡 Saisissez la **Quantité/ha** utilisée. La dose ONSSA et le DAR sont des références. Laissez 0 si produit non utilisé.")

    pest_rows = []
    for p in PESTICIDES_REF:
        pest_rows.append({
            "Culture / Variété / Profil": "",
            "Catégorie": p["Catégorie"],
            "Produit commercial": p["Produit commercial"],
            "Matière active": p["Matière active"],
            "Quantité/ha": None,
            "Unité": p["Unité"],
            "Dose ONSSA": p["Dose ONSSA"],
            "DAR": p["DAR"],
        })
    df_pest_init = pd.DataFrame(pest_rows)

    df_pesticides = st.data_editor(
        df_pest_init,
        hide_index=True,
        use_container_width=True,
        key="pesticides",
        column_config={
            "Catégorie": st.column_config.TextColumn("Catégorie", disabled=True, width="small"),
            "Produit commercial": st.column_config.TextColumn("Produit", disabled=True, width="medium"),
            "Matière active": st.column_config.TextColumn("Matière active", disabled=True, width="medium"),
            "Unité": st.column_config.TextColumn("Unité", disabled=True, width="small"),
            "Dose ONSSA": st.column_config.TextColumn("Dose ONSSA (réf.)", disabled=True, width="small"),
            "DAR": st.column_config.TextColumn("DAR", disabled=True, width="small"),
            "Quantité/ha": st.column_config.NumberColumn("Qté/ha", min_value=0.0, format="%.3f"),
        }
    )

    st.divider()
    # Résumé par catégorie
    df_pest_used = df_pesticides[df_pesticides["Quantité/ha"].notna() & (df_pesticides["Quantité/ha"] > 0)]
    if not df_pest_used.empty:
        st.markdown('<div class="bloc-subheader">📊 Récapitulatif par catégorie</div>', unsafe_allow_html=True)
        recap_pest = df_pest_used.groupby("Catégorie")["Produit commercial"].count().reset_index()
        recap_pest.columns = ["Catégorie", "Nb produits utilisés"]
        st.dataframe(recap_pest, hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# TAB G — MAIN D'ŒUVRE
# ══════════════════════════════════════════════════════════════
with tab_g:
    st.markdown('<div class="bloc-header">👷 BLOC G — Main d\'Œuvre</div>', unsafe_allow_html=True)
    st.info("💡 Renseignez les **jours de travail/ha** et le **% du total** pour chaque opération.")

    mo_rows = [{"Opération": op, "Jours travail/ha": None, "%/total profil": None} for op in MO_OPERATIONS]
    df_mo_init = pd.DataFrame(mo_rows)

    df_mo = st.data_editor(
        df_mo_init,
        hide_index=True,
        use_container_width=True,
        key="mo",
        column_config={
            "Opération": st.column_config.TextColumn("Opération", disabled=True, width="large"),
            "Jours travail/ha": st.column_config.NumberColumn("Jours travail/ha", min_value=0.0, format="%.1f"),
            "%/total profil": st.column_config.NumberColumn("% / total", min_value=0.0, max_value=100.0, format="%.1f"),
        }
    )

    df_mo_filled = df_mo[df_mo["Jours travail/ha"].notna() & (df_mo["Jours travail/ha"] > 0)]
    if not df_mo_filled.empty:
        total_jt = df_mo_filled["Jours travail/ha"].sum()
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Total Jours Travail/ha", f"{total_jt:.1f} j")
        col_m2.metric("Nb opérations renseignées", f"{len(df_mo_filled)}")

    st.divider()
    st.markdown('<div class="bloc-subheader">💰 Coûts de main d\'œuvre</div>', unsafe_allow_html=True)
    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        smig_respecte   = st.radio("SMIG respecté", ["Oui", "Non"], horizontal=True)
        salaire_mo      = st.number_input("Salaire moyen (DH/j)", min_value=0.0)
    with col_g2:
        epi_portes      = st.radio("Port EPI", ["Systématique", "Partiel", "Non"], horizontal=True)
        formation_bpa   = st.number_input("Formation BPA (h/an)", min_value=0.0)
    with col_g3:
        registre_form   = st.radio("Registre formation", ["Oui", "Non"], horizontal=True)
        nb_ouvriers_pic = st.number_input("Nb ouvriers pic récolte", min_value=0)


# ══════════════════════════════════════════════════════════════
# TAB H — BIOSTIMULANTS
# ══════════════════════════════════════════════════════════════
with tab_h:
    st.markdown('<div class="bloc-header">🌿 BLOC H — Biostimulants</div>', unsafe_allow_html=True)
    st.info("💡 Renseignez la **Quantité/ha** utilisée. Laissez vide si produit non utilisé.")

    biostim_rows = [{"Produit": p, "Quantité/ha": None, "Unité": "—", "Min": None, "Max": None} for p in BIOSTIMULANTS_LISTE]
    df_biostim_init = pd.DataFrame(biostim_rows)

    df_biostim = st.data_editor(
        df_biostim_init,
        hide_index=True,
        use_container_width=True,
        key="biostim",
        column_config={
            "Produit": st.column_config.TextColumn("Produit", disabled=True, width="large"),
            "Quantité/ha": st.column_config.NumberColumn("Quantité/ha", min_value=0.0, format="%.3f"),
            "Unité": st.column_config.TextColumn("Unité", width="small"),
            "Min": st.column_config.NumberColumn("Min", min_value=0.0, format="%.3f"),
            "Max": st.column_config.NumberColumn("Max", min_value=0.0, format="%.3f"),
        }
    )

    df_biostim_used = df_biostim[df_biostim["Quantité/ha"].notna() & (df_biostim["Quantité/ha"] > 0)]
    if not df_biostim_used.empty:
        st.success(f"✅ {len(df_biostim_used)} biostimulant(s) utilisé(s)")


# ══════════════════════════════════════════════════════════════
# TAB I — RÉGULATEURS
# ══════════════════════════════════════════════════════════════
with tab_i:
    st.markdown('<div class="bloc-header">⚗️ BLOC I — Régulateurs de Croissance</div>', unsafe_allow_html=True)
    st.info("💡 Renseignez la **Quantité/ha** utilisée.")

    reg_rows = [{"Produit": p, "Quantité/ha": None, "Unité": "", "Min": None, "Max": None} for p in REGULATEURS_LISTE]
    df_reg_init = pd.DataFrame(reg_rows)

    df_regulateurs = st.data_editor(
        df_reg_init,
        hide_index=True,
        use_container_width=True,
        key="regulateurs",
        column_config={
            "Produit": st.column_config.TextColumn("Produit", disabled=True, width="large"),
            "Quantité/ha": st.column_config.NumberColumn("Quantité/ha", min_value=0.0, format="%.3f"),
            "Unité": st.column_config.TextColumn("Unité", width="small"),
            "Min": st.column_config.NumberColumn("Min", min_value=0.0, format="%.3f"),
            "Max": st.column_config.NumberColumn("Max", min_value=0.0, format="%.3f"),
        }
    )


# ═══════════════════════════════════════════════════════════════
# BOUTON D'ENREGISTREMENT
# ═══════════════════════════════════════════════════════════════
st.divider()
st.markdown("<br>", unsafe_allow_html=True)

col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 2])
with col_btn2:
    submit = st.button("💾 Enregistrer l'Enquête", type="primary", use_container_width=True)

if submit:
    if not code_fiche:
        st.warning("⚠️ Veuillez renseigner le **Code Fiche** avant d'enregistrer.")
    elif not nom_prenom:
        st.warning("⚠️ Veuillez renseigner le **Nom & Prénom** de l'enquêté.")
    else:
        # Données d'identification
        data_identification = {
            "Code Fiche": code_fiche,
            "Date Enquête": str(date_enquete),
            "Enquêteur": enqueteur,
            "Culture(s)": ", ".join(cultures),
            "Durée Enquête (h)": duree,
            "Profil Exploitation": profil,
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
            "Date Dernier Audit": str(date_audit),
            "Organisme Certificateur": organisme_certif,
            "Consentement": consentement,
        }

        # Données globales complémentaires (substrat, eau...)
        data = {
            "Code Fiche": code_fiche,
            "Date Enquête": str(date_enquete),
            "pH substrat": ph_substrat,
            "CE substrat (dS/m)": ce_substrat,
            "Renouvellement substrat": renouvellement,
            "Coût renouvellement (DH/ha)": cout_renouv,
            "Porosité totale (%)": porosite,
            "Capacité rétention eau (%)": retention_eau,
            "CE solution nutritive (dS/m)": ce_solution,
            "CE drainage (dS/m)": ce_drainage,
            "Fraction lessivage (%)": fraction_les,
            "Nb apports/j": nb_apports_j,
            "Durée apport (min)": duree_apport,
            "Fréquence mesure drainage": freq_drainage,
            "SMIG respecté": smig_respecte,
            "Salaire moyen (DH/j)": salaire_mo,
            "Port EPI": epi_portes,
            "Formation BPA (h/an)": formation_bpa,
            "Registre formation": registre_form,
            "Nb ouvriers pic récolte": nb_ouvriers_pic,
        }

        # DataFrames
        dfs_to_export = {
            "varietes":    df_varietes    if 'df_varietes'    in locals() else pd.DataFrame(),
            "densite":     df_densite     if 'df_densite'     in locals() else pd.DataFrame(),
            "rendements":  df_rendements  if 'df_rendements'  in locals() else pd.DataFrame(),
            "substrat":    df_substrat    if 'df_substrat'    in locals() else pd.DataFrame(),
            "eau":         df_eau         if 'df_eau'         in locals() else pd.DataFrame(),
            "volumes":     df_volumes     if 'df_volumes'     in locals() else pd.DataFrame(),
            "fertigation": df_fertigation if 'df_fertigation' in locals() else pd.DataFrame(),
            "pesticides":  df_pesticides  if 'df_pesticides'  in locals() else pd.DataFrame(),
            "mo":          df_mo          if 'df_mo'          in locals() else pd.DataFrame(),
            "biostim":     df_biostim     if 'df_biostim'     in locals() else pd.DataFrame(),
            "regulateurs": df_regulateurs if 'df_regulateurs' in locals() else pd.DataFrame(),
        }

        exporter_vers_gsheets(data, dfs_to_export, data_identification)
        st.balloons()
        st.success("🎉 Enquête enregistrée avec succès !")
