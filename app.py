import json
import re
import numpy as np
import pandas as pd
import streamlit as st
from openai import OpenAI

# ==============================================================================
# CONFIGURATION DE LA PAGE
# ==============================================================================
st.set_page_config(
    page_title=" DTLA Audit Qualité de Données & IA",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==============================================================================
# 1. MOTEUR D'AUDIT TECHNIQUE (PANDAS PUR)
# ==============================================================================
class DataAuditor:
    """Analyse un DataFrame Pandas et génère un rapport d'anomalies structuré."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.total_rows, self.total_cols = df.shape
        self.total_cells = self.total_rows * self.total_cols

    def check_missing_values(self) -> dict:
        """Détecte les cellules nulles/vides."""
        missing_per_col = self.df.isnull().sum()
        missing_cols = {}
        for col, count in missing_per_col.items():
            if count > 0:
                missing_cols[col] = {
                    "count": int(count),
                    "percentage": round(float((count / self.total_rows) * 100), 2),
                }

        total_missing = int(missing_per_col.sum())
        missing_rate = (
            round((total_missing / self.total_cells) * 100, 2)
            if self.total_cells > 0
            else 0
        )
        return {
            "total_missing_cells": total_missing,
            "overall_missing_rate_pct": missing_rate,
            "columns_affected": missing_cols,
        }

    def check_duplicates(self) -> dict:
        """Détecte les lignes strictement identiques."""
        duplicate_rows_count = int(self.df.duplicated().sum())
        dup_rate = (
            round((duplicate_rows_count / self.total_rows) * 100, 2)
            if self.total_rows > 0
            else 0
        )
        return {
            "duplicate_rows_count": duplicate_rows_count,
            "duplicate_rate_pct": dup_rate,
        }

    def check_format_inconsistencies(self) -> dict:
        """Détecte des anomalies de types (ex: nombres ou dates masqués sous forme de texte)."""
        issues = {}
        # Pattern pour détecter des devises ou nombres stockés comme chaînes (ex: "1 250 €", "99.99$")
        numeric_like_pattern = re.compile(
            r"^\s*[-+]?[\d\s]+([,\.]\d+)?\s*[$€£%]?\s*$"
        )

        for col in self.df.columns:
            if self.df[col].dtype == "object":
                non_null_series = self.df[col].dropna().astype(str).str.strip()
                if non_null_series.empty:
                    continue

                # 1. Vérifie si une colonne texte est majoritairement composée de chiffres
                numeric_matches = non_null_series.apply(
                    lambda x: bool(numeric_like_pattern.match(x))
                ).sum()
                if (
                    numeric_matches > 0
                    and (numeric_matches / len(non_null_series)) > 0.6
                ):
                    issues[col] = {
                        "detected_issue": "Colonne textuelle ressemblant à des nombres/devises.",
                        "sample_values": non_null_series.head(3).tolist(),
                    }
                    continue

                # 2. Vérifie si une colonne texte contient des dates au format hétérogène
                # On tente une conversion partielle
                try:
                    parsed_dates = pd.to_datetime(
                        non_null_series, errors="coerce", format="mixed"
                    )
                    valid_dates_count = parsed_dates.notnull().sum()
                    if (valid_dates_count / len(non_null_series)) > 0.6:
                        issues[col] = {
                            "detected_issue": "Dates détectées au format texte non standardisé.",
                            "sample_values": non_null_series.head(3).tolist(),
                        }
                except Exception:
                    pass

        return issues

    def check_outliers_iqr(self) -> dict:
        """Détecte les valeurs aberrantes sur les colonnes numériques via la méthode IQR."""
        outliers_report = {}
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = self.df[col].dropna()
            if len(series) < 5:
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1

            if iqr == 0:
                continue

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outliers = series[(series < lower_bound) | (series > upper_bound)]
            count = int(outliers.count())

            if count > 0:
                outliers_report[col] = {
                    "outliers_count": count,
                    "percentage": round(float((count / len(series)) * 100), 2),
                    "lower_threshold": round(float(lower_bound), 2),
                    "upper_threshold": round(float(upper_bound), 2),
                    "extreme_min": round(float(outliers.min()), 2),
                    "extreme_max": round(float(outliers.max()), 2),
                }

        return outliers_report

    def calculate_health_score(
        self, missing_dict: dict, dup_dict: dict, format_dict: dict, outlier_dict: dict
    ) -> int:
        """Calcule un score global de santé de 0 à 100."""
        score = 100.0

        # Pénalité valeurs manquantes (jusqu'à -35 points)
        missing_rate = missing_dict.get("overall_missing_rate_pct", 0)
        score -= min(missing_rate * 1.5, 35)

        # Pénalité doublons (jusqu'à -25 points)
        dup_rate = dup_dict.get("duplicate_rate_pct", 0)
        score -= min(dup_rate * 2.5, 25)

        # Pénalité formats incohérents (5 points par colonne problématique, max 20)
        score -= min(len(format_dict) * 5, 20)

        # Pénalité valeurs aberrantes (jusqu'à -20 points)
        outlier_cols_count = len(outlier_dict)
        score -= min(outlier_cols_count * 4, 20)

        return max(0, int(round(score)))

    def generate_full_audit(self) -> dict:
        """Assemble l'ensemble du rapport JSON."""
        missing = self.check_missing_values()
        duplicates = self.check_duplicates()
        formats = self.check_format_inconsistencies()
        outliers = self.check_outliers_iqr()
        health_score = self.calculate_health_score(
            missing, duplicates, formats, outliers
        )

        return {
            "dataset_overview": {
                "total_rows": self.total_rows,
                "total_columns": self.total_cols,
                "health_score": health_score,
            },
            "anomalies": {
                "missing_values": missing,
                "duplicates": duplicates,
                "format_inconsistencies": formats,
                "outliers_iqr": outliers,
            },
        }


# ==============================================================================
# 2. MODULE IA (EXPLICATION & VULGARISATION MÉTIER)
# ==============================================================================

def get_ai_explanation_groq(audit_summary: dict, api_key: str) -> str:
    """Appel à Groq 100% gratuit avec détection automatique du modèle actif."""
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )

    # 1. On interroge Groq pour récupérer les modèles disponibles sur votre compte
    try:
        all_models = [m.id for m in client.models.list().data]
        # On garde les modèles de discussion textuelle (on écarte l'audio/whisper)
        chat_models = [
            m for m in all_models 
            if not any(bad in m.lower() for bad in ["whisper", "guard", "audio", "orpheus"])
        ]
        
        if not chat_models:
            return "⚠️ Aucun modèle de texte n'est actif sur cette clé Groq."

        # On privilégie gpt-oss-20b, sinon on prend le premier disponible
        selected_model = "openai/gpt-oss-20b" if "openai/gpt-oss-20b" in chat_models else chat_models[0]
        
    except Exception as e:
        return f"⚠️ Erreur de connexion avec votre clé Groq : {str(e)}"

    # 2. Préparation du prompt métier

    system_prompt = (
        "Tu es un Lead Data Analyst pédagogue et bienveillant. Ton rôle est d'expliquer "
        "à un analyste débutant ou à un responsable métier les anomalies trouvées dans un jeu de données.\n"
        "Règles impératives :\n"
        "1. Exprime-toi en français clair, sans jargon mathématique excessif.\n"
        "2. Structure ta réponse en 3 sections bien distinctes :\n"
        "   - 🩺 Diagnostic Global & Impact Métier (Pourquoi ces anomalies faussent les analyses)\n"
        "   - 🔍 Zoom sur les Anomalies Critiques (Explique simplement les cas détectés)\n"
        "   - 🛠️ Plan d'action recommandé étape par étape pour nettoyer la donnée (avec Pandas ou Excel)\n"
        "3. Sois concret, concis et actionnable."
    )

    user_prompt = f"""Voici le rapport d'audit technique d'un jeu de données au format JSON :
:\n```json
{json.dumps(audit_summary, indent=2, ensure_ascii=False)}\n```

Rédige une analyse claire pour un utilisateur non-expert."""
    
    # 3. Génération de la réponse
    try:
        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        return f"*(Modèle utilisé avec succès : `{selected_model}`)*\n\n" + response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Erreur lors de la génération avec Groq ({selected_model}) : {str(e)}"

def get_simulated_explanation(audit_summary: dict) -> str:
    """Génération locale sans clé API."""
    anomalies = audit_summary["anomalies"]
    score = audit_summary["dataset_overview"]["health_score"]

    return f"""### 🩺 Diagnostic Global & Risques Métier (Mode Démo)
Le jeu de données présente un score de santé de **{score}/100**. Plusieurs anomalies techniques risquent de fausser vos KPI et vos analyses statistiques.

### 🔍 Analyse détaillée des anomalies détectées :
- **Cases vides :** {anomalies['missing_values']['total_missing_cells']} cellule(s) manquante(s).
- **Lignes en double :** {anomalies['duplicates']['duplicate_rows_count']} doublon(s) strict(s).
- **Incohérences de formats :** {len(anomalies['format_inconsistencies'])} colonne(s) problématique(s).
- **Valeurs aberrantes (IQR) :** {len(anomalies['outliers_iqr'])} variable(s) avec des valeurs extrêmes.

### 🛠️ Plan d'action recommandé :
1. **Supprimer les doublons** : Utiliser `df.drop_duplicates()`.
2. **Nettoyer les devises et textes** : Retirer les symboles et convertir en type numérique.
3. **Harmoniser les dates** : Standardiser au format `AAAA-MM-JJ`.
4. **Traiter les valeurs extrêmes** : Filtrer les valeurs impossibles (ex: âge aberrant).
"""

# ==============================================================================
# 3. GÉNÉRATEUR DE DONNÉES TEST (POUR DÉBUTANT)
# ==============================================================================
def generate_sample_dirty_data() -> pd.DataFrame:
# Crée un jeu de données de test réaliste contenant des erreurs classiques.
    return pd.DataFrame({
        "id_client": [101, 102, 103, 104, 105, 105, 107, 108, 109, 110, 111, 112],
        "nom": ["Dupont", "Martin", "Durand", "Leroy", "Moreau", "Moreau", "Petit", np.nan, "Roux", "David", "Bertrand", "Morel"],
        "revenu_mensuel": ["2500", "3100 €", "2800", "N/A", "4200", "4200", "150000", "2900", "-500", "3300", "2700", "3000"],
        "age": [28, 34, 45, np.nan, 52, 52, 19, 145, 31, 29, 41, 38],
        "date_inscription": ["2023-01-15", "15/02/2023", "2023-03-20", "2023-04-10", "12/05/2023", "12/05/2023", "2023/06/01", "2023-07-18", "2023-08-22", "2023-09-05", "non renseigné", "2023-11-12"]
    })

# ==============================================================================
# 4. INTERFACE UTILISATEUR STREAMLIT
# ==============================================================================

def main():
    st.title("🛡️ DTLACheck AI - Audit & Qualité des Données")
    st.markdown("Importez un fichier **CSV** ou **Excel** pour analyser sa conformité, "
"détecter les valeurs suspectes et obtenir des explications simples rédigées par l'IA.")

# --- BARRE LATÉRALE ---
# Ajouter le choix du mode 
    st.sidebar.header("⚙️ Configuration")
    mode = st.sidebar.radio(
    "Moteur d'explication :",
    ["Gratuit : Groq (Llama 3)", "Mode Simulation (Sans clé API)"]
)

    api_key = ""
    if mode == "Gratuit : Groq (Llama 3)":
        api_key = st.sidebar.text_input("Clé API Groq gratuite :", type="password", placeholder="gsk_...")

    st.sidebar.markdown("---")
    st.sidebar.subheader("💡 Tester sans fichier")
    use_demo = st.sidebar.button("Charger un jeu de données démo")
    
# --- ZONE DE CHARGEMENT ---

    uploaded_file = st.file_uploader(
        "Déposez votre fichier ici (CSV ou Excel) :",
        type=["csv", "xlsx", "xls"],
        help="Taille maximale conseillée : 50 Mo.",
    )
    df = None

    if use_demo:
        df = generate_sample_dirty_data()
        st.sidebar.success("Jeu de test chargé !")
    elif uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file, sep=None, engine="python")
            else:
                df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Erreur de lecture du fichier : {e}")
            return

# Si aucune donnée n'est chargée, on s'arrête ici
    if df is None:
        st.info("👆 Veuillez importer un fichier ou cliquer sur le bouton de démo.")
        return

# --- EXÉCUTION DE L'AUDIT PANDAS ---
    auditor = DataAuditor(df)
    audit_results = auditor.generate_full_audit()

    overview = audit_results["dataset_overview"]
    anomalies = audit_results["anomalies"]
    score = overview["health_score"]

    st.markdown("---")

# --- CARTES DE MÉTRIQUES GLOBALES ---
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if score >= 80:
            st.metric("Score de Santé", f"{score}/100", delta="Excellent", delta_color="normal")
        elif score >= 50:
            st.metric("Score de Santé", f"{score}/100", delta="Moyen", delta_color="off")
        else:
            st.metric("Score de Santé", f"{score}/100", delta="Critique", delta_color="inverse")

    with col2:
            st.metric("Lignes & Colonnes", f"{overview['total_rows']} × {overview['total_columns']}")

    with col3:
            st.metric(
                "Valeurs Manquantes",
                f"{anomalies['missing_values']['total_missing_cells']}",
                help=f"{anomalies['missing_values']['overall_missing_rate_pct']}% des cellules totales",
                )

    with col4:
        st.metric(
            "Lignes en Double",
            f"{anomalies['duplicates']['duplicate_rows_count']}",
            help=f"{anomalies['duplicates']['duplicate_rate_pct']}% du fichier",
        )

    with col5:
        total_outliers = sum(
            col["outliers_count"]
            for col in anomalies["outliers_iqr"].values()
        )
        st.metric("Valeurs Aberrantes", f"{total_outliers}", help="Méthode de l'IQR (Outliers)")

# --- SECTION IA ---
    st.markdown("### 🤖 Diagnostic & Conseils de l'IA")

    if mode == "Mode Simulation (Sans clé API)":
        if st.button("✨ Lancer le diagnostic (Simulation locale)"):
            st.markdown(get_simulated_explanation(audit_results))
    else:
        if not api_key:
            st.warning("🔑 Veuillez renseigner votre clé gratuite Groq (`gsk_...`) dans la barre latérale.")
        else:
            if st.button("✨ Lancer l'analyse avec Groq"):
                with st.spinner("Llama 3 examine le rapport d'audit..."):
                    explanation = get_ai_explanation_groq(audit_results, api_key)
                    st.markdown(explanation)

    st.markdown("---")

# --- ONGLETS DE DÉTAILS TECHNIQUES ---
    tab1, tab2, tab3 = st.columns([1, 1, 1])
    with st.expander("🔍 1. Détail des Valeurs Manquantes & Doublons", expanded=True):
        c_a, c_b = st.columns(2)
        with c_a:
            st.write("**Colonnes avec cellules vides :**")
            missing_cols = anomalies["missing_values"]["columns_affected"]
            if missing_cols:
                missing_df = pd.DataFrame.from_dict(missing_cols, orient="index").reset_index()
                missing_df.columns = ["Colonne", "Cellules Manquantes", "% Manquant"]
                st.dataframe(missing_df, hide_index=True, width="stretch")
            else:
                st.success("✅ Aucune valeur manquante.")
        with c_b:
            st.write("**Doublons :**")
            dup_count = anomalies["duplicates"]["duplicate_rows_count"]
            if dup_count > 0:
                st.warning(f"⚠️ {dup_count} ligne(s) identique(s).")
            else:
                st.success("✅ Aucun doublon.")

    with st.expander("⚠️ 2. Incohérences de Formats / Types", expanded=True):
        format_issues = anomalies["format_inconsistencies"]
        if format_issues:
            for col_name, detail in format_issues.items():
                st.warning(f"**Colonne `{col_name}`** : {detail['detected_issue']}\n\nExemples : `{detail['sample_values']}`")
        else:
            st.success("✅ Formats de dates et de textes conformes.")

    with st.expander("📈 3. Valeurs Aberrantes (IQR)", expanded=True):
        outliers = anomalies["outliers_iqr"]
        if outliers:
            outlier_df = pd.DataFrame.from_dict(outliers, orient="index").reset_index()
            outlier_df.columns = ["Colonne", "Nb Anomalies", "% Colonne", "Seuil Min", "Seuil Max", "Min", "Max"]
            st.dataframe(outlier_df, hide_index=True, use_container_width=True)
        else:
            st.success("✅ Aucune anomalie numérique extrême.")

    with st.expander("👀 4. Aperçu des Données Brutes", expanded=False):
        st.dataframe(df, width="stretch")


if __name__ == "__main__":
    main()


# 3. Comment lancer et tester le projet

## Dans le terminal, placez-vous dans le dossier du projet :
## bash et lancer la commande streamlit run app.py