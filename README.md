
# 🛡️ DTLACheck AI - Audit Automatisé de Qualité de Données 

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B?logo=streamlit)](https://streamlit.io/)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458?logo=pandas)](https://pandas.pydata.org/)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Cloud-F55036)](https://groq.com/)
[![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/License-PolyForm_Noncommercial_1.0.0-blue.svg)](https://polyformproject.org/licenses/noncommercial/1.0.0/)

Application web interactive d'audit de qualité de données (CSV & Excel) conçue pour accélérer la phase d'exploration (EDA) et vulgariser les anomalies techniques auprès des équipes métier grâce à l'IA générative.

---

## 🎯 Problématique Métier

Dans un projet Data, **près de 80 % du temps est consacré au nettoyage des données**. Les fichiers bruts issus des CRM, ERP ou d'exports Excel comportent couramment :
* Des cellules manquantes invisibles au premier coup d'œil.
* Des doublons qui biaisent les statistiques et les KPI.
* Des incohérences de typage (ex. colonnes de prix contenant des devises sous format texte).
* Des valeurs aberrantes (outliers) faussant les moyennes.

**DTLACheck AI** automatise ce diagnostic en quelques secondes et génère un plan d'action de nettoyage compréhensible, même pour un profil non technique.

---

## 🏗️ Architecture & Choix Techniques (Privacy & Sobriété)

> **Règle d'or de conception : Aucune donnée brute n'est transmise à l'IA.**

Contrairement aux approches naïves consistant à envoyer des fichiers entiers à un LLM, cette application suit une **architecture hybride** :

Fichier CSV / Excel ->  Moteur Python / Pandas (Local) | Détection mathématique (IQR, Regex, Valeurs Nulles, Doublons) | Calcul d'un Score de Santé (0 à 100) -> Résumé Technique JSON Anonymisé  -> Modèle IA via Groq Cloud (API) -> Diagnostic Vulgarisé & Plan d'Action Recommandé.

### Avantages de cette architecture :
1. **Conformité RGPD / Sécurité :** Les données sensibles de vos clients ne quittent jamais votre machine.
2. **Économie de tokens :** Un fichier de 100 000 lignes consomme la même quantité minimale de tokens qu'un fichier de 10 lignes.
3. **Précision déterministe :** Les statistiques sont calculées mathématiquement par Pandas, éliminant tout risque d'hallucination numérique par l'IA.

---

## ✨ Fonctionnalités Principales

* 📊 **Score Global de Santé (0 à 100) :** Évaluation instantanée de la qualité globale du fichier.
* 🔍 **Complétude & Unicité :** Détection des valeurs `NaN` et des lignes strictement dupliquées.
* 🔤 **Analyse des Types & Formats :** Repérage des dates non standardisées et des devises masquées sous forme de texte.
* 📈 **Détection d'Outliers (IQR) :** Identification des valeurs aberrantes basée sur l'écart interquartile ($1.5 \times \text{IQR}$).
* 🤖 **Diagnostic IA (Groq / Llama / OSS) :** Traduction vulgarisée des impacts business et suggestions concrètes de nettoyage.
* 💡 **Mode Démo & Simulation :** Possibilité de tester l'application en un clic sans clé API ni fichier personnel.

---

## 🚀 Installation & Démarrage Rapide

### Prérequis
* Python 3.10 ou supérieur installé.
* Git installé.

### 1. Cloner le dépôt depuis le terminal bash

git clone https://github.com/Audrey-Djomi/dtlacheck-ai.git
cd /projet-dtlacheck

### 2. Créer un environnement virtuel (recommandé)

    # Sous Windows
python -m venv venv
venv\Scripts\activate

    # Sous macOS / Linux
python3 -m venv venv
source venv/bin/activate

### 3. Installer les dépendances

pip install -r requirements.txt

### 4. Lancer l'application

streamlit run app.py

L'application s'ouvrira automatiquement sur http://localhost:8501.

## 🛠️ Stack Technique

Composant	Technologie	Rôle
- Interface Web	Streamlit	Dashboard interactif et visualisation
- Data Processing	Pandas / NumPy	Ingestion de fichiers, calculs matriciels et statistiques
- Parsing Excel	OpenPyXL	Prise en charge des classeurs .xlsx / .xls
- Moteur IA	Groq Cloud API	Inférence ultra-rapide et gratuite pour l'explication textuelle.

## 📜 Licence et droits d'utilisation

© 2026 Audrey Djomi. Tous droits réservés sur ma contribution originale.

Ce projet est mis à disposition sous **PolyForm Noncommercial License 1.0.0**.

Vous êtes autorisé(e) à consulter, cloner, utiliser, modifier et redistribuer ce projet à des fins non commerciales, dans le respect des conditions de la licence.

Toute redistribution doit conserver la mention de copyright, le texte de la licence et les mentions requises.

**Toute utilisation commerciale nécessite une autorisation préalable distincte de l'auteure.**

Consultez le fichier `LICENSE` pour connaître les conditions complètes :
[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0).

## 👤 À propos de l'Auteure

nom: Audrey DJOMI

Projet réalisé dans le cadre de ma reconversion professionnelle en Analyse de Données.

LinkedIn : Audrey DJOMI

GitHub : @Audrey-Djomi


