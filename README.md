# 📄 CV Manager

![Python](https://img.shields.io/badge/Python-3.13-blue)
![PySide6](https://img.shields.io/badge/PySide6-Qt%20GUI-orange)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)

### Application locale pour gérer vos candidatures, CV et lettres de motivation

CV Manager est une application de bureau développée en **Python + PySide6** permettant de centraliser et d’organiser efficacement vos démarches de recherche d’emploi. Elle offre une interface moderne et intuitive pour gérer vos offres, candidatures, profil personnel, modèles HTML, ainsi que des tableaux de bord et statistiques.

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
 │   ├── main_window.py
 │   ├── settings_widget.py
 │   ├── dashboard_widget.py
 │   ├── stats_widget.py
 │   ├── candidatures_window.py
 │   └── offer_form_dialog.py
 │
 ├── models.py
 ├── services/
 ├── templates/
 ├── style.qss
 ├── main.py
 └── README.md
```

---

## 📝 Feuille de route (Roadmap)

* [ ] Export PDF des lettres
* [ ] Système de modèles multiples
* [ ] Mode sombre
* [ ] Recherche avancée dans les offres
* [ ] Intégration IA (résumé d’offres, génération personnalisée de lettres)

---

## 👨‍💻 Auteur

Projet développé par **Ludo**. Contributions bienvenues !
