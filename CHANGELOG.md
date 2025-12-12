# Changelog

Tous les changements notables de ce projet sont documentés dans ce fichier.  
Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/)  
et le versioning suit [Semantic Versioning](https://semver.org/lang/fr/).

---

## [Unreleased]

### Added
- Refonte en cours de la page d’ajout d’offre (intégration au `QStackedLayout`)
- Amélioration continue de l’import d’offres depuis URL (Jobup, parsing ciblé)
- Préparation d’un système de templates multiples pour les lettres de motivation

---

## [0.3.0] – 2025-12-12

### Added
- Génération de lettres de motivation en **HTML/CSS** à partir de templates Jinja2
- Template moderne par défaut (`lettre_modern.html.j2`)
- Prévisualisation des lettres générées dans le navigateur
- Service dédié `letters_service` (logique métier isolée)
- Import d’offres depuis une URL (Jobup – extraction progressive)
- Dump de debug texte pour analyser le contenu HTML importé
- Bouton de suppression d’une offre
- Bouton “Marquer comme envoyée” pour les candidatures
- Page **Dashboard** (statistiques globales)
- Page **Statistiques**
- Page **Paramètres** (incluant désormais le profil candidat)
- Sidebar latérale connectée à la navigation principale
- Vue détaillée d’une offre avec ses lettres associées
- Système de cartes (offers / lettres)

### Changed
- Refonte complète de `main_window` (factorisation, découpage logique)
- Passage à une navigation centralisée via `QStackedLayout`
- Intégration de tous les services métier (`offers_service`, `letters_service`, `profile_service`, etc.)
- Refonte visuelle globale (QSS clair, professionnel et coloré)
- Déplacement de la gestion du profil dans les paramètres
- Amélioration UX (feedback visuel, hiérarchie claire, lisibilité)

### Fixed
- Problèmes de rendu QSS non supportés par Qt
- Erreurs de parsing QSS (syntaxe, propriétés invalides)
- Erreurs Jinja2 dues à des templates corrompus ou incomplets
- Mauvaise résolution des chemins de templates
- Gestion des colonnes manquantes en base SQLite
- Erreurs de sélection (`SelectRows` → `QAbstractItemView.SelectRows`)
- Gestion incorrecte des imports Python (`QAction`, `QScrollArea`, etc.)
- Problèmes de génération de lettres avec mauvais templates
- Conflits Git liés aux dépendances Python commitées par erreur

---

## [0.2.0] – 2025-12-08

### Added
- Gestion complète des candidatures (CRUD)
- Association offres ↔ lettres de motivation
- Ouverture directe des lettres HTML depuis l’application
- Statuts de candidatures avec code couleur
- Système de base de données SQLite via SQLAlchemy
- Services métier dédiés (séparation UI / logique)

### Changed
- Amélioration de la structure du projet
- Centralisation de la session SQLAlchemy
- Refonte progressive des fenêtres (`candidatures_window`, dialogs)

### Fixed
- Erreurs d’import de modules (`database`, services)
- Problèmes de layout Qt (largeur, scroll, sélection)
- Bugs liés aux relations SQLAlchemy

---

## [0.1.0] – 2025-12-01

### Added
- Initialisation du projet **CV Manager**
- Application desktop PySide6
- Gestion des offres d’emploi (CRUD)
- Gestion manuelle des lettres de motivation
- Interface plein écran
- Structure de projet modulaire
- Dépôt GitHub public