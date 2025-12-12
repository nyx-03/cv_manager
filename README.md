# 📄 CV Manager

![Python](https://img.shields.io/badge/Python-3.13-blue)
![PySide6](https://img.shields.io/badge/PySide6-Qt%20GUI-orange)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)
![Platform](https://img.shields.io/badge/Platform-macOS-blue)

### Application desktop pour gérer vos candidatures, CV et lettres de motivation

---

## 🏷️ Dernière version – v0.2.0

**v0.2.0** marque une étape majeure dans l’évolution de CV Manager, avec la structuration complète de l’application, une interface modernisée et l’introduction des lettres de motivation HTML.

### ✨ Nouveautés principales

- Génération de **lettres de motivation HTML/CSS** à partir de templates
- Moteur de rendu **Jinja2** (conditions, variables, personnalisation avancée)
- Vue détaillée des offres avec les lettres associées
- Tableau de bord (dashboard) et premières statistiques
- Page **Paramètres** centralisant le profil candidat
- Sidebar de navigation unifiée
- Import initial d’offres depuis une **URL** (Jobup – extraction progressive)

### 🔧 Améliorations techniques

- Séparation claire **UI / Services / Modèles**
- Centralisation de la logique métier (offers, candidatures, letters, profile)
- Navigation basée sur `QStackedLayout`
- Refonte complète du style **QSS** (clair, lisible, professionnel)

### 🐛 Correctifs notables

- Correction des erreurs QSS non supportées par Qt
- Résolution des problèmes de rendu des templates de lettres
- Correction des imports PySide6 et des comportements de sélection Qt
- Stabilisation de la base SQLite / SQLAlchemy

➡️ Voir le détail complet dans le fichier [`CHANGELOG.md`](CHANGELOG.md).

---

## ✨ Fonctionnalités principales

### 🗂 Gestion des offres et candidatures

* Ajout rapide d’une nouvelle offre
* Suivi des statuts : *À faire*, *Envoyée*, *En cours*, *Refusée*, *Entretien*, …
* Visualisation globale via une vue dédiée

### 📝 Génération de lettres de motivation

* Modèles **HTML/CSS** personnalisables
* Prévisualisation dans le navigateur
* Insertion automatique des informations du candidat

### 👤 Page Profil intégrée

* Informations personnelles (nom, prénom, email, téléphone, ville…)
* Liens professionnels (LinkedIn, GitHub, Portfolio)
* Résumé professionnel

### 📊 Tableau de bord

* Dernières candidatures
* Raccourcis vers les fonctionnalités principales

### 📈 Statistiques

* Répartition par statut
* Répartition par entreprise
* Évolution mensuelle

### ⚙️ Paramètres

* Informations du profil utilisateur
* Dossiers des modèles et lettres
* Préférences d’affichage

---

## 🖥 Technologies utilisées

* **Python 3.13**
* **PySide6**
* **SQLAlchemy**
* **HTML / CSS**
* **GitHub** pour la gestion de version
* **Qt Style Sheets (QSS)**
* **Architecture MVC / Services**

---

## 🚀 Installation & lancement

### 1. Cloner le projet

```bash
git clone https://github.com/nyx-03/cv_manager.git
cd cv_manager
```

### 2. Créer un environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate       # macOS / Linux
venv\\Scripts\\activate        # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Lancer l’application

```bash
python main.py
```

---

## 📚 Structure du projet (simplifiée)

```
cv_manager/
 ├── ui/
 │   ├── application_view.py
 │   ├── main_window.py
 │   ├── sidebar.py
 │   ├── offer_list_widget.py
 │   ├── dashboard_widget.py
 │   ├── stats_widget.py
 │   ├── settings_widget.py
 │   └── pages/
 │       ├── offers_page.py
 │       └── offer_detail_page.py
 │
 ├── services/
 │   ├── offers_service.py
 │   ├── candidatures_service.py
 │   ├── letters_service.py
 │   └── profile_service.py
 │
 ├── models.py
 ├── templates/
 ├── style.qss
 ├── main.py
 └── README.md
```

---

## 📝 Feuille de route (Roadmap)

* [ ] Paramètres avancés (chemins, modèles, préférences)
* [ ] Recherche, filtres et tri des offres
* [ ] Pipeline complet de statuts de candidatures
* [ ] Historique et versionning des lettres
* [ ] Export PDF et ZIP des candidatures
* [ ] Import d'annonces par URL
* [ ] Mode sombre
* [ ] Packaging macOS (PyInstaller)
* [ ] Version Windows
* [ ] Version Linux

---

## 👨‍💻 Auteur

Projet développé par **PyTechSolutions**. Contributions et retours bienvenus.
