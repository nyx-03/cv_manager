from pathlib import Path
import os
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
    QMessageBox,
    QInputDialog,
    QPlainTextEdit,
    QTextEdit,
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices


# Database helpers
from db import get_db_path, reset_database

# Templates management
from services.letters_service import (
    ensure_user_templates_dir,
    list_user_templates,
    import_user_template,
    validate_template_file,
)
from services.profile_service import ensure_profile, update_profile, ProfileUpdateData


class SettingsWidget(QWidget):
    """Page de paramètres pour le CV Manager.

    V1 : uniquement interface et logique basique, sans persistance réelle.
    La persistance (JSON, base, etc.) pourra être branchée plus tard.
    """

    def __init__(self, session=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session
        self._templates: list[str] = []
        self._default_template: str = ""

        self._setup_ui()
        self.load_settings()
        self._refresh_db_path_ui()
        self._refresh_logs_path_ui()
        self._logs_timer = QTimer(self)
        self._logs_timer.setInterval(1000)
        self._logs_timer.timeout.connect(self._on_refresh_logs_view)
        self._logs_timer.start()
        self._on_refresh_logs_view()

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

        # --- Card : Templates (Jinja2) ---
        templates_card = QFrame(self)
        templates_card.setObjectName("Card")
        templates_layout = QVBoxLayout(templates_card)
        templates_layout.setContentsMargins(12, 12, 12, 12)
        templates_layout.setSpacing(8)

        templates_title = QLabel("Templates de lettres")
        templates_title.setProperty("heading", True)
        templates_layout.addWidget(templates_title)

        templates_help = QLabel(
            "Importe tes templates personnalisés (.j2 / .html.j2). Ils seront copiés dans data/templates et proposés lors de la génération."
        )
        templates_help.setWordWrap(True)
        templates_help.setProperty("muted", True)
        templates_layout.addWidget(templates_help)

        row_tpl = QHBoxLayout()
        label_tpl = QLabel("Template par défaut :")
        self.combo_default_template = QComboBox()
        self.combo_default_template.setMinimumWidth(280)
        row_tpl.addWidget(label_tpl)
        row_tpl.addWidget(self.combo_default_template, 1)
        templates_layout.addLayout(row_tpl)

        row_tpl_btns = QHBoxLayout()

        self.btn_tpl_import = QPushButton("Importer")
        self.btn_tpl_import.setObjectName("PrimaryButton")
        self.btn_tpl_import.clicked.connect(self._on_import_template)
        row_tpl_btns.addWidget(self.btn_tpl_import)

        self.btn_tpl_delete = QPushButton("Supprimer")
        self.btn_tpl_delete.setObjectName("SecondaryButton")
        self.btn_tpl_delete.clicked.connect(self._on_delete_template)
        row_tpl_btns.addWidget(self.btn_tpl_delete)

        self.btn_tpl_open_dir = QPushButton("Ouvrir le dossier")
        self.btn_tpl_open_dir.setObjectName("SecondaryButton")
        self.btn_tpl_open_dir.clicked.connect(self._on_open_templates_dir)
        row_tpl_btns.addWidget(self.btn_tpl_open_dir)

        row_tpl_btns.addStretch(1)

        self.btn_tpl_set_default = QPushButton("Définir comme défaut")
        self.btn_tpl_set_default.setObjectName("SecondaryButton")
        self.btn_tpl_set_default.clicked.connect(self._on_set_default_template)
        row_tpl_btns.addWidget(self.btn_tpl_set_default)

        templates_layout.addLayout(row_tpl_btns)

        self.tpl_status = QLabel("")
        self.tpl_status.setObjectName("formInfo")
        self.tpl_status.setProperty("kind", "info")
        self.tpl_status.setVisible(False)
        templates_layout.addWidget(self.tpl_status)

        root_layout.addWidget(templates_card)

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

        # --- Card : Maintenance ---
        maintenance_card = QFrame(self)
        maintenance_card.setObjectName("Card")
        maintenance_layout = QVBoxLayout(maintenance_card)
        maintenance_layout.setContentsMargins(12, 12, 12, 12)
        maintenance_layout.setSpacing(8)

        maintenance_title = QLabel("Maintenance")
        maintenance_title.setProperty("heading", True)
        maintenance_layout.addWidget(maintenance_title)

        maintenance_help = QLabel(
            "⚠️ Cette action est destructive et supprimera toutes les données locales.\n"
            "Après réinitialisation, l'application devra être redémarrée."
        )
        maintenance_help.setWordWrap(True)
        maintenance_help.setProperty("muted", True)
        maintenance_layout.addWidget(maintenance_help)

        # --- Emplacement de la base de données ---
        row_db_path = QHBoxLayout()
        label_db_path = QLabel("Base de données :")
        self.db_path_value = QLineEdit()
        self.db_path_value.setReadOnly(True)
        self.db_path_value.setPlaceholderText("Chemin de la base de données…")

        btn_open_db_folder = QPushButton("Ouvrir le dossier")
        btn_open_db_folder.setObjectName("SecondaryButton")
        btn_open_db_folder.clicked.connect(self._on_open_db_folder)

        btn_reveal_db_file = QPushButton("Révéler le fichier")
        btn_reveal_db_file.setObjectName("SecondaryButton")
        btn_reveal_db_file.clicked.connect(self._on_reveal_db_file)

        row_db_path.addWidget(label_db_path)
        row_db_path.addWidget(self.db_path_value, 1)
        row_db_path.addWidget(btn_open_db_folder)
        row_db_path.addWidget(btn_reveal_db_file)
        maintenance_layout.addLayout(row_db_path)

        # --- Logs ---
        row_logs_path = QHBoxLayout()
        label_logs_path = QLabel("Logs :")
        self.logs_path_value = QLineEdit()
        self.logs_path_value.setReadOnly(True)
        self.logs_path_value.setPlaceholderText("Chemin du fichier de log…")

        btn_open_logs_folder = QPushButton("Ouvrir le dossier")
        btn_open_logs_folder.setObjectName("SecondaryButton")
        btn_open_logs_folder.clicked.connect(self._on_open_logs_folder)

        btn_open_log_file = QPushButton("Ouvrir le fichier")
        btn_open_log_file.setObjectName("SecondaryButton")
        btn_open_log_file.clicked.connect(self._on_open_log_file)

        row_logs_path.addWidget(label_logs_path)
        row_logs_path.addWidget(self.logs_path_value, 1)
        row_logs_path.addWidget(btn_open_logs_folder)
        row_logs_path.addWidget(btn_open_log_file)
        maintenance_layout.addLayout(row_logs_path)

        # Vue logs (lecture seule)
        self.logs_view = QPlainTextEdit()
        self.logs_view.setReadOnly(True)
        self.logs_view.setPlaceholderText("Les logs s’afficheront ici…")
        self.logs_view.setObjectName("LogsViewer")
        self.logs_view.setMinimumHeight(180)
        maintenance_layout.addWidget(self.logs_view)

        row_logs_actions = QHBoxLayout()

        btn_refresh_logs = QPushButton("Rafraîchir")
        btn_refresh_logs.setObjectName("SecondaryButton")
        btn_refresh_logs.clicked.connect(self._on_refresh_logs_view)
        row_logs_actions.addWidget(btn_refresh_logs)

        btn_clear_logs = QPushButton("Vider le fichier")
        btn_clear_logs.setObjectName("SecondaryButton")
        btn_clear_logs.clicked.connect(self._on_clear_log_file)
        row_logs_actions.addWidget(btn_clear_logs)

        row_logs_actions.addStretch(1)
        maintenance_layout.addLayout(row_logs_actions)

        btn_delete_log = QPushButton("Supprimer le fichier de log")
        btn_delete_log.setObjectName("DangerButton")
        btn_delete_log.clicked.connect(self._on_delete_log_file)
        maintenance_layout.addWidget(btn_delete_log)

        btn_reset_db = QPushButton("Réinitialiser la base de données")
        btn_reset_db.setObjectName("DangerButton")
        btn_reset_db.clicked.connect(self._on_reset_database_clicked)
        maintenance_layout.addWidget(btn_reset_db)

        root_layout.addWidget(maintenance_card)

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
    def _browse_letters_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choisir le dossier des lettres")
        if directory:
            self.input_letters_dir.setText(directory)

    def _browse_templates_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choisir le dossier des modèles")
        if directory:
            self.input_templates_dir.setText(directory)

    def _require_session(self) -> bool:
        if self.session is None:
            self._show_status_message("Erreur : aucune session DB disponible.")
            return False
        return True

    def load_settings(self) -> None:
        if not self._require_session():
            return
        profil = ensure_profile(self.session)

        self.input_name.setText(getattr(profil, "nom", "") or "")
        self.input_firstname.setText(getattr(profil, "prenom", "") or "")
        self.input_email.setText(getattr(profil, "email", "") or "")
        self.input_phone.setText(getattr(profil, "telephone", "") or "")
        self.input_city.setText(getattr(profil, "ville", "") or "")
        self.input_target_title.setText(getattr(profil, "titre", "") or "")
        self.input_resume.setText(getattr(profil, "resume", "") or "")
        self.input_linkedin.setText(getattr(profil, "linkedin", "") or "")
        self.input_github.setText(getattr(profil, "github", "") or "")
        self.input_portfolio.setText(getattr(profil, "portfolio", "") or "")

        # Templates
        # Lecture d'un éventuel template par défaut depuis le profil
        self._default_template = ""
        for field in ("template_lettre", "template_letter", "default_template", "default_letter_template"):
            if hasattr(profil, field):
                self._default_template = getattr(profil, field) or ""
                break
        self._refresh_templates()

        # Defaults for non-profile settings
        self.input_letters_dir.setText("")
        self.input_templates_dir.setText("")
        self.combo_theme.setCurrentIndex(0)
        self.spin_recent_count.setValue(10)
        if hasattr(self, "db_path_value"):
            self._refresh_db_path_ui()
        self._refresh_logs_path_ui()

    def save_settings(self) -> None:
        if not self._require_session():
            return

        profil = update_profile(
            self.session,
            ProfileUpdateData(
                nom=self.input_name.text().strip(),
                prenom=self.input_firstname.text().strip(),
                email=self.input_email.text().strip(),
                telephone=self.input_phone.text().strip(),
                ville=self.input_city.text().strip(),
                titre=self.input_target_title.text().strip(),
                linkedin=self.input_linkedin.text().strip(),
                github=self.input_github.text().strip(),
                portfolio=self.input_portfolio.text().strip(),
            ),
        )

        # Champ optionnel (peut ne pas exister dans le modèle)
        if hasattr(profil, "resume"):
            profil.resume = self.input_resume.toPlainText().strip()
            self.session.commit()

        self._show_status_message("Paramètres enregistrés.")

    def reset_settings(self) -> None:
        self.load_settings()

    def _show_status_message(self, message: str, duration_ms: int = 3000) -> None:
        self.status_label.setText(message)
        self.status_label.setVisible(True)
        QTimer.singleShot(duration_ms, lambda: self.status_label.setVisible(False))




    def _refresh_db_path_ui(self) -> None:
        """Met à jour l'affichage du chemin de la DB dans la carte Maintenance."""
        try:
            db_path = get_db_path()
            self.db_path_value.setText(str(db_path))
            self.db_path_value.setToolTip(str(db_path))
        except Exception:
            self.db_path_value.setText("(chemin DB indisponible)")
            self.db_path_value.setToolTip("")

    def _get_app_base_dir(self) -> Path:
        """Retourne le dossier racine de données de l'app (même base que la DB)."""
        db_path = get_db_path()
        # Si la DB est dans .../<AppName>/data/<file>.sqlite, base = .../<AppName>
        if db_path.parent.name.lower() == "data":
            return db_path.parent.parent
        return db_path.parent

    def _get_logs_dir(self) -> Path:
        """Dossier des logs (créé si nécessaire)."""
        base_dir = self._get_app_base_dir()
        logs_dir = base_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir

    def _get_log_file_path(self) -> Path:
        """Chemin du fichier log principal."""
        # Si une variable d'environnement est définie, elle prime
        env_path = os.environ.get("CV_MANAGER_LOG_FILE", "").strip()
        if env_path:
            return Path(env_path).expanduser()
        return self._get_logs_dir() / "cv_manager.log"

    def _refresh_logs_path_ui(self) -> None:
        """Met à jour l'affichage du chemin des logs."""
        if not hasattr(self, "logs_path_value"):
            return
        try:
            log_path = self._get_log_file_path()
            self.logs_path_value.setText(str(log_path))
            self.logs_path_value.setToolTip(str(log_path))
        except Exception:
            self.logs_path_value.setText("(chemin logs indisponible)")
            self.logs_path_value.setToolTip("")

    def _on_open_logs_folder(self) -> None:
        """Ouvre le dossier des logs."""
        try:
            folder = self._get_log_file_path().parent
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        except Exception as e:
            QMessageBox.warning(self, "Ouverture du dossier", f"Impossible d'ouvrir le dossier :\n\n{e}")

    def _on_open_log_file(self) -> None:
        """Ouvre le fichier de log dans l'application par défaut (si existant)."""
        try:
            log_path = self._get_log_file_path()
            if not log_path.exists():
                QMessageBox.information(self, "Logs", "Aucun fichier de log trouvé pour le moment.")
                return
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_path)))
        except Exception as e:
            QMessageBox.warning(self, "Logs", f"Impossible d'ouvrir le fichier :\n\n{e}")

    def _on_delete_log_file(self) -> None:
        """Supprime le fichier de log (action destructive)."""
        try:
            log_path = self._get_log_file_path()
            if not log_path.exists():
                self._show_status_message("Aucun fichier de log à supprimer.")
                self._refresh_logs_path_ui()
                return

            confirm = QMessageBox.question(
                self,
                "Supprimer le fichier de log",
                "Cette action va supprimer le fichier de log actuel.\n\n"
                "Voulez-vous continuer ?",
                QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
                QMessageBox.StandardButton.Cancel,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

            log_path.unlink(missing_ok=True)
            self._on_refresh_logs_view()
            self._show_status_message("Fichier de log supprimé.", duration_ms=4000)
            self._refresh_logs_path_ui()
        except Exception as e:
            QMessageBox.warning(self, "Logs", f"Suppression impossible :\n\n{e}")

    def _on_refresh_logs_view(self) -> None:
        """Recharge le contenu du fichier de log dans la vue."""
        if not hasattr(self, "logs_view"):
            return
        try:
            log_path = self._get_log_file_path()
            if not log_path.exists():
                self.logs_view.setPlainText("")
                self.logs_view.setPlaceholderText("Aucun fichier de log pour le moment.")
                return

            # Lecture robuste (évite crash sur caractères bizarres)
            text = log_path.read_text(encoding="utf-8", errors="replace")

            # Garde uniquement les dernières lignes pour éviter de surcharger l'UI
            max_chars = 200_000
            if len(text) > max_chars:
                text = text[-max_chars:]
                # on coupe au prochain retour à la ligne pour éviter une ligne tronquée au début
                nl = text.find("\n")
                if nl != -1:
                    text = text[nl + 1 :]

            # Ne met à jour que si ça a changé (évite de perdre la sélection/scroll)
            current = self.logs_view.toPlainText()
            if current != text:
                at_bottom = self.logs_view.verticalScrollBar().value() >= self.logs_view.verticalScrollBar().maximum() - 2
                self.logs_view.setPlainText(text)
                if at_bottom:
                    sb = self.logs_view.verticalScrollBar()
                    sb.setValue(sb.maximum())
        except Exception as e:
            # Ne pas spammer de popups; on affiche dans la zone et on garde l'app stable
            try:
                self.logs_view.setPlainText(f"Impossible de lire les logs: {e}")
            except Exception:
                pass

    def _on_clear_log_file(self) -> None:
        """Vide le fichier de log sans le supprimer (action destructive)."""
        try:
            log_path = self._get_log_file_path()
            if not log_path.exists():
                self._show_status_message("Aucun fichier de log à vider.")
                self._on_refresh_logs_view()
                return

            confirm = QMessageBox.question(
                self,
                "Vider le fichier de log",
                "Cette action va vider le fichier de log actuel.\n\nVoulez-vous continuer ?",
                QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
                QMessageBox.StandardButton.Cancel,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

            # Truncate
            log_path.write_text("", encoding="utf-8")
            self._show_status_message("Fichier de log vidé.", duration_ms=4000)
            self._on_refresh_logs_view()
        except Exception as e:
            QMessageBox.warning(self, "Logs", f"Impossible de vider le fichier :\n\n{e}")

    def _on_open_db_folder(self) -> None:
        """Ouvre le dossier contenant la base de données dans l'explorateur."""
        try:
            db_path = get_db_path()
            folder = db_path.parent
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        except Exception as e:
            QMessageBox.warning(self, "Ouverture du dossier", f"Impossible d'ouvrir le dossier :\n\n{e}")

    def _on_reveal_db_file(self) -> None:
        """Révèle le fichier DB dans l'explorateur (macOS: Finder sélectionne généralement le fichier)."""
        try:
            db_path = get_db_path()
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(db_path)))
        except Exception as e:
            QMessageBox.warning(self, "Révéler la DB", f"Impossible de révéler le fichier :\n\n{e}")

    def _on_reset_database_clicked(self) -> None:
        """Action dangereuse : supprime le fichier sqlite et invite à relancer l'app."""
        if not self._require_session():
            return

        db_path = get_db_path()
        if db_path is None:
            QMessageBox.warning(self, "Réinitialisation", "Impossible de déterminer le chemin de la base de données.")
            return

        if not db_path.exists():
            QMessageBox.information(
                self,
                "Réinitialisation",
                f"Aucune base de données trouvée à cet emplacement :\n{db_path}",
            )
            return

        # 1) Confirmation standard
        confirm = QMessageBox.question(
            self,
            "Réinitialiser la base de données",
            "Cette action va SUPPRIMER la base de données locale.\n\n"
            "Toutes les offres, candidatures et lettres enregistrées seront perdues.\n\n"
            "Voulez-vous continuer ?",
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        # 2) Confirmation par saisie
        text, ok = QInputDialog.getText(
            self,
            "Confirmation requise",
            "Tapez SUPPRIMER pour confirmer :",
        )
        if not ok or text.strip().upper() != "SUPPRIMER":
            self._show_status_message("Réinitialisation annulée.")
            return

        try:
            reset_database()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Réinitialisation",
                f"La suppression a rencontré une erreur :\n\n{e}",
            )
            return

        QMessageBox.information(
            self,
            "Réinitialisation terminée",
            "Base de données supprimée.\n\n"
            "Pour repartir sur une base propre, relance l'application.",
        )
        if hasattr(self, "db_path_value"):
            self._refresh_db_path_ui()
        self._refresh_logs_path_ui()
        try:
            self.session = None
        except Exception:
            pass
        self._show_status_message("Base de données supprimée. Relance l'application.", duration_ms=6000)


    # ---------------------------------------------------------
    # Templates (Jinja2)
    # ---------------------------------------------------------
    def _refresh_templates(self) -> None:
        """Recharge la liste des templates utilisateur et met à jour le combo."""
        try:
            ensure_user_templates_dir()
            paths = list_user_templates()
            self._templates = [p.name for p in paths]
        except Exception as e:
            self._templates = []
            self._show_tpl_message(f"Impossible de charger les templates: {e}", kind="error")

        current = self.combo_default_template.currentText().strip() if hasattr(self, "combo_default_template") else ""
        self.combo_default_template.blockSignals(True)
        self.combo_default_template.clear()
        self.combo_default_template.addItem("(Aucun)")
        for name in self._templates:
            self.combo_default_template.addItem(name)
        # Restaure la sélection
        if self._default_template and self._default_template in self._templates:
            self.combo_default_template.setCurrentText(self._default_template)
        elif current and current in self._templates:
            self.combo_default_template.setCurrentText(current)
        else:
            self.combo_default_template.setCurrentIndex(0)
        self.combo_default_template.blockSignals(False)

    def _show_tpl_message(self, message: str, *, kind: str = "info", duration_ms: int = 5000) -> None:
        if not hasattr(self, "tpl_status"):
            self._show_status_message(message, duration_ms=duration_ms)
            return
        self.tpl_status.setText(message)
        self.tpl_status.setProperty("kind", kind)
        self.tpl_status.style().unpolish(self.tpl_status)
        self.tpl_status.style().polish(self.tpl_status)
        self.tpl_status.setVisible(True)
        QTimer.singleShot(duration_ms, lambda: self.tpl_status.setVisible(False))

    def _on_open_templates_dir(self) -> None:
        d = ensure_user_templates_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def _on_import_template(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importer un template",
            "",
            "Templates (*.j2 *.html *.html.j2);;Tous les fichiers (*)",
        )
        if not file_path:
            return

        try:
            dest = import_user_template(file_path, overwrite=False)
            # Validation plus stricte et message clair
            try:
                validate_template_file(dest)
            except Exception as e:
                self._show_tpl_message(f"Template importé mais invalide: {e}", kind="warning")
            else:
                self._show_tpl_message(f"Template importé: {dest.name}", kind="success")
            self._refresh_templates()
            # Sélectionne le nouveau template
            if dest.name in self._templates:
                self.combo_default_template.setCurrentText(dest.name)
        except Exception as e:
            self._show_tpl_message(str(e), kind="error")

    def _selected_template_name(self) -> str:
        if not hasattr(self, "combo_default_template"):
            return ""
        name = self.combo_default_template.currentText().strip()
        if not name or name == "(Aucun)":
            return ""
        return name

    def _on_delete_template(self) -> None:
        name = self._selected_template_name()
        if not name:
            self._show_tpl_message("Aucun template sélectionné.", kind="warning")
            return

        # Suppression simple (sans popup pour rester minimal)
        try:
            p = ensure_user_templates_dir() / name
            if p.exists():
                p.unlink()
            if self._default_template == name:
                self._default_template = ""
            self._refresh_templates()
            self._show_tpl_message(f"Template supprimé: {name}", kind="success")
        except Exception as e:
            self._show_tpl_message(f"Impossible de supprimer: {e}", kind="error")

    def _on_set_default_template(self) -> None:
        """Définit le template par défaut.

        Si le modèle ProfilCandidat a un champ compatible, on persiste.
        Sinon, on conserve le choix côté UI (persistance à implémenter ensuite).
        """
        name = self._selected_template_name()
        self._default_template = name

        if not self._require_session():
            self._show_tpl_message("Template par défaut défini (non persisté : pas de session DB).", kind="warning")
            return

        profil = ensure_profile(self.session)

        # Champs possibles (on s'adapte au modèle)
        candidate_fields = [
            "template_lettre",
            "template_letter",
            "default_template",
            "default_letter_template",
        ]

        saved = False
        for field in candidate_fields:
            if hasattr(profil, field):
                setattr(profil, field, name)
                try:
                    self.session.commit()
                    saved = True
                except Exception:
                    self.session.rollback()
                    saved = False
                break

        if saved:
            self._show_tpl_message("Template par défaut enregistré.", kind="success")
        else:
            self._show_tpl_message(
                "Template par défaut défini, mais non persisté (champ manquant dans le modèle).",
                kind="warning",
            )