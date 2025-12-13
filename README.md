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
- Refonte de la vue détail d’offre avec édition de lettre intégrée
- Personnalisation fine des lettres (sections modifiables avant génération)
- Génération et édition de lettres directement depuis la vue offre
- Gestion améliorée des cartes (offres / lettres) avec interactions claires

### 🔧 Améliorations techniques

- Séparation claire **UI / Services / Modèles**
- Centralisation de la logique métier (offers, candidatures, letters, profile)
- Navigation basée sur `QStackedLayout`
- Refonte complète du style **QSS** (clair, lisible, professionnel)
- Amélioration du moteur de génération de lettres (séparation données / template)
- Correction et sécurisation des templates Jinja2
- Meilleure gestion des événements UI (clics cartes vs boutons)
- Nettoyage et stabilisation de `main_window` et des pages associées

### 🐛 Correctifs notables

- Correction des erreurs QSS non supportées par Qt
- Résolution des problèmes de rendu des templates de lettres
- Correction des imports PySide6 et des comportements de sélection Qt
- Stabilisation de la base SQLite / SQLAlchemy
- Correction des erreurs de rendu Jinja2
- Correction des comportements inattendus lors de l’édition des lettres
- Amélioration de la cohérence UI/QSS sur les pages de détail

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

La roadmap ci-dessous présente les évolutions envisagées pour CV Manager, par ordre de priorité fonctionnelle et produit.

---

### 🚀 Priorité 1 — Productivité & valeur utilisateur

* [ ] Éditeur de lettres de motivation avant génération (par paragraphe)
* [ ] Sauvegarde des contenus personnalisés par offre
* [ ] Historique et versionning des lettres de motivation
* [ ] Recherche globale dans les offres et candidatures
* [ ] Filtres avancés (statut, entreprise, date, source)

---

### 🎯 Priorité 2 — Import & automatisation

* [ ] Import d’annonces par URL (Jobup, LinkedIn, Indeed…)
* [ ] Détection automatique du type de page (listing vs annonce)
* [ ] Extraction structurée : poste, entreprise, lieu, contrat, description
* [ ] Mapping par site (providers d’import)
* [ ] Sauvegarde de l’annonce originale (HTML / TXT)

---

### 🎨 Priorité 3 — UX & interface

* [ ] Amélioration des cartes (offres / lettres)
* [ ] Timeline visuelle des candidatures
* [ ] Notifications internes (succès, erreurs, actions)
* [ ] Raccourcis clavier
* [ ] Mode sombre

---

### 📄 Priorité 4 — Export & livrables

* [ ] Export PDF des lettres de motivation
* [ ] Choix du template lors de l’export
* [ ] Génération d’un dossier de candidature complet (ZIP)
* [ ] Nommage automatique des fichiers

---

### 🧱 Priorité 5 — Robustesse & configuration

* [ ] Paramètres avancés (chemins, modèles par défaut)
* [ ] Sauvegarde / restauration de la base de données
* [ ] Validation des données utilisateur
* [ ] Gestion des erreurs centralisée

---

### 📦 Priorité 6 — Distribution & plateformes

* [ ] Packaging macOS (PyInstaller)
* [ ] Icône et identité visuelle de l’application
* [ ] Version Windows
* [ ] Version Linux
* [ ] Mise à jour automatique (long terme)

---

## 👨‍💻 Auteur

Projet développé par **PyTechSolutions**. Contributions et retours bienvenus.
