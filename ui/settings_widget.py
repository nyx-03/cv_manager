from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QComboBox,
    QSpinBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QTextEdit
from models import ProfilCandidat


class SettingsWidget(QWidget):
    """Page de paramètres pour le CV Manager.

    V1 : uniquement interface et logique basique, sans persistance réelle.
    La persistance (JSON, base, etc.) pourra être branchée plus tard.
    """

    def __init__(self, session=None, parent=None):
        super().__init__(parent)
        self.session = session

        self._setup_ui()
        self.load_settings()

    # ---------------------------------------------------------
    # UI SETUP
    # ---------------------------------------------------------
    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        # --- Card : Profil utilisateur ---
        profile_card = QFrame(self)
        profile_card.setObjectName("Card")
        profile_layout = QVBoxLayout(profile_card)
        profile_layout.setContentsMargins(12, 12, 12, 12)
        profile_layout.setSpacing(8)

        profile_title = QLabel("Profil utilisateur")
        profile_title.setProperty("heading", True)
        profile_layout.addWidget(profile_title)

        # Nom complet
        row_name = QHBoxLayout()
        label_name = QLabel("Nom complet :")
        self.input_name = QLineEdit()
        row_name.addWidget(label_name)
        row_name.addWidget(self.input_name)
        profile_layout.addLayout(row_name)

        # Email
        row_email = QHBoxLayout()
        label_email = QLabel("Email de contact :")
        self.input_email = QLineEdit()
        row_email.addWidget(label_email)
        row_email.addWidget(self.input_email)
        profile_layout.addLayout(row_email)

        # Prénom
        row_firstname = QHBoxLayout()
        label_firstname = QLabel("Prénom :")
        self.input_firstname = QLineEdit()
        row_firstname.addWidget(label_firstname)
        row_firstname.addWidget(self.input_firstname)
        profile_layout.addLayout(row_firstname)

        # Téléphone
        row_phone = QHBoxLayout()
        label_phone = QLabel("Téléphone :")
        self.input_phone = QLineEdit()
        row_phone.addWidget(label_phone)
        row_phone.addWidget(self.input_phone)
        profile_layout.addLayout(row_phone)

        # Ville
        row_city = QHBoxLayout()
        label_city = QLabel("Ville :")
        self.input_city = QLineEdit()
        row_city.addWidget(label_city)
        row_city.addWidget(self.input_city)
        profile_layout.addLayout(row_city)

        # Résumé / description (multi‑ligne)
        row_resume = QVBoxLayout()
        label_resume = QLabel("Résumé :")
        self.input_resume = QTextEdit()
        row_resume.addWidget(label_resume)
        row_resume.addWidget(self.input_resume)
        profile_layout.addLayout(row_resume)

        # Liens externes
        row_linkedin = QHBoxLayout()
        label_linkedin = QLabel("LinkedIn :")
        self.input_linkedin = QLineEdit()
        row_linkedin.addWidget(label_linkedin)
        row_linkedin.addWidget(self.input_linkedin)
        profile_layout.addLayout(row_linkedin)

        row_github = QHBoxLayout()
        label_github = QLabel("GitHub :")
        self.input_github = QLineEdit()
        row_github.addWidget(label_github)
        row_github.addWidget(self.input_github)
        profile_layout.addLayout(row_github)

        row_portfolio = QHBoxLayout()
        label_portfolio = QLabel("Portfolio :")
        self.input_portfolio = QLineEdit()
        row_portfolio.addWidget(label_portfolio)
        row_portfolio.addWidget(self.input_portfolio)
        profile_layout.addLayout(row_portfolio)

        # Poste cible
        row_title = QHBoxLayout()
        label_title = QLabel("Poste cible :")
        self.input_target_title = QLineEdit()
        self.input_target_title.setPlaceholderText("Ex. Développeur Python, Data Analyst...")
        row_title.addWidget(label_title)
        row_title.addWidget(self.input_target_title)
        profile_layout.addLayout(row_title)

        root_layout.addWidget(profile_card)

        # --- Card : Dossiers ---
        paths_card = QFrame(self)
        paths_card.setObjectName("Card")
        paths_layout = QVBoxLayout(paths_card)
        paths_layout.setContentsMargins(12, 12, 12, 12)
        paths_layout.setSpacing(8)

        paths_title = QLabel("Dossiers")
        paths_title.setProperty("heading", True)
        paths_layout.addWidget(paths_title)

        # Dossier des lettres
        row_letters = QHBoxLayout()
        label_letters = QLabel("Dossier des lettres :")
        self.input_letters_dir = QLineEdit()
        btn_letters_browse = QPushButton("Parcourir")
        btn_letters_browse.setObjectName("SecondaryButton")
        btn_letters_browse.clicked.connect(self._browse_letters_dir)

        row_letters.addWidget(label_letters)
        row_letters.addWidget(self.input_letters_dir)
        row_letters.addWidget(btn_letters_browse)
        paths_layout.addLayout(row_letters)

        # Dossier des modèles
        row_templates = QHBoxLayout()
        label_templates = QLabel("Dossier des modèles :")
        self.input_templates_dir = QLineEdit()
        btn_templates_browse = QPushButton("Parcourir")
        btn_templates_browse.setObjectName("SecondaryButton")
        btn_templates_browse.clicked.connect(self._browse_templates_dir)

        row_templates.addWidget(label_templates)
        row_templates.addWidget(self.input_templates_dir)
        row_templates.addWidget(btn_templates_browse)
        paths_layout.addLayout(row_templates)

        root_layout.addWidget(paths_card)

        # --- Card : Préférences ---
        prefs_card = QFrame(self)
        prefs_card.setObjectName("Card")
        prefs_layout = QVBoxLayout(prefs_card)
        prefs_layout.setContentsMargins(12, 12, 12, 12)
        prefs_layout.setSpacing(8)

        prefs_title = QLabel("Préférences")
        prefs_title.setProperty("heading", True)
        prefs_layout.addWidget(prefs_title)

        # Thème (placeholder pour l'instant)
        row_theme = QHBoxLayout()
        label_theme = QLabel("Thème :")
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Clair (par défaut)", "Sombre (à venir)"])
        self.combo_theme.setCurrentIndex(0)
        row_theme.addWidget(label_theme)
        row_theme.addWidget(self.combo_theme)
        prefs_layout.addLayout(row_theme)

        # Nombre de candidatures récentes à afficher sur le dashboard
        row_recent_count = QHBoxLayout()
        label_recent = QLabel("Dernières candidatures sur le dashboard :")
        self.spin_recent_count = QSpinBox()
        self.spin_recent_count.setMinimum(5)
        self.spin_recent_count.setMaximum(50)
        self.spin_recent_count.setValue(10)
        row_recent_count.addWidget(label_recent)
        row_recent_count.addWidget(self.spin_recent_count)
        prefs_layout.addLayout(row_recent_count)

        root_layout.addWidget(prefs_card)

        # --- Message de statut ---
        self.status_label = QLabel("")
        self.status_label.setObjectName("SettingsStatusLabel")
        self.status_label.setVisible(False)
        root_layout.addWidget(self.status_label)

        # --- Boutons en bas ---
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        btn_reset = QPushButton("Réinitialiser")
        btn_reset.setObjectName("SecondaryButton")
        btn_reset.clicked.connect(self.reset_settings)
        buttons_layout.addWidget(btn_reset)

        btn_save = QPushButton("Enregistrer les paramètres")
        btn_save.setObjectName("PrimaryButton")
        btn_save.clicked.connect(self.save_settings)
        buttons_layout.addWidget(btn_save)

        root_layout.addLayout(buttons_layout)

        root_layout.addStretch()

    # ---------------------------------------------------------
    # ACTIONS / LOGIQUE
    # ---------------------------------------------------------
    def _browse_letters_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Choisir le dossier des lettres")
        if directory:
            self.input_letters_dir.setText(directory)

    def _browse_templates_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Choisir le dossier des modèles")
        if directory:
            self.input_templates_dir.setText(directory)

    def _get_or_create_profile(self):
        profil = self.session.query(ProfilCandidat).first()
        if not profil:
            profil = ProfilCandidat()
            self.session.add(profil)
            self.session.commit()
        return profil

    def load_settings(self):
        profil = self._get_or_create_profile()

        self.input_name.setText(profil.nom or "")
        self.input_firstname.setText(profil.prenom or "")
        self.input_email.setText(profil.email or "")
        self.input_phone.setText(profil.telephone or "")
        self.input_city.setText(profil.ville or "")
        self.input_target_title.setText(profil.titre or "")
        self.input_resume.setText(profil.resume or "")
        self.input_linkedin.setText(profil.linkedin or "")
        self.input_github.setText(profil.github or "")
        self.input_portfolio.setText(profil.portfolio or "")

        # Defaults for non-profile settings
        self.input_letters_dir.setText("")
        self.input_templates_dir.setText("")
        self.combo_theme.setCurrentIndex(0)
        self.spin_recent_count.setValue(10)

    def save_settings(self):
        profil = self._get_or_create_profile()

        profil.nom = self.input_name.text().strip()
        profil.prenom = self.input_firstname.text().strip()
        profil.email = self.input_email.text().strip()
        profil.telephone = self.input_phone.text().strip()
        profil.ville = self.input_city.text().strip()
        profil.titre = self.input_target_title.text().strip()
        profil.resume = self.input_resume.toPlainText().strip()
        profil.linkedin = self.input_linkedin.text().strip()
        profil.github = self.input_github.text().strip()
        profil.portfolio = self.input_portfolio.text().strip()

        self.session.commit()
        self._show_status_message("Paramètres enregistrés.")

    def reset_settings(self):
        self.load_settings()

    def _show_status_message(self, message: str, duration_ms: int = 3000):
        self.status_label.setText(message)
        self.status_label.setVisible(True)
        QTimer.singleShot(duration_ms, lambda: self.status_label.setVisible(False))