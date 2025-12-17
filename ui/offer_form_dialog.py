# ui/offer_form_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QHBoxLayout, QFrame, QLabel, QWidget
)
from PySide6.QtCore import Signal

try:
    # Optionnel: utilisé uniquement si disponible (mode navigateur intégré)
    from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
    HAS_QTWEBENGINE = True
except Exception:
    HAS_QTWEBENGINE = False


class OfferFormDialog(QDialog):
    importRequested = Signal(str)
    importRequestedBrowser = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.setWindowTitle("Nouvelle offre")
        self.resize(500, 600)

        # --- Champs du formulaire ---
        self.titre_input = QLineEdit()
        self.entreprise_input = QLineEdit()
        self.source_input = QLineEdit()
        self.url_input = QLineEdit()

        self.import_btn = QPushButton("Pré-remplir")
        self.import_btn.setObjectName("SecondaryButton")
        self.import_btn.setToolTip("Pré-remplir le formulaire à partir de l'URL")

        self.import_status = QLabel("")
        self.import_status.setWordWrap(True)
        self.import_status.setObjectName("HelpText")

        self.import_btn_browser = QPushButton("Pré-remplir (navigateur)")
        self.import_btn_browser.setObjectName("SecondaryButton")
        self.import_btn_browser.setToolTip(
            "Utilise un navigateur intégré (JS/cookies) — recommandé pour Jobup/Hellowork"
        )
        self.import_btn_browser.setEnabled(HAS_QTWEBENGINE)
        if not HAS_QTWEBENGINE:
            self.import_btn_browser.setToolTip(
                "QtWebEngine n'est pas installé. Installe PySide6-QtWebEngine puis relance l'application."
            )

        self.localisation_input = QLineEdit()
        self.type_contrat_input = QLineEdit()

        self.texte_annonce_input = QTextEdit()
        self.texte_annonce_input.setPlaceholderText("Colle ici le texte complet de l'annonce")

        # --- Layout formulaire ---
        form_layout = QFormLayout()
        form_layout.addRow("Titre du poste :", self.titre_input)
        form_layout.addRow("Entreprise :", self.entreprise_input)
        form_layout.addRow("Source :", self.source_input)
        url_row = QHBoxLayout()
        url_row.addWidget(self.url_input)
        url_row.addWidget(self.import_btn)
        url_row.addWidget(self.import_btn_browser)
        form_layout.addRow("URL :", url_row)
        form_layout.addRow("", self.import_status)
        form_layout.addRow("Localisation :", self.localisation_input)
        form_layout.addRow("Type contrat :", self.type_contrat_input)
        form_layout.addRow("Texte annonce :", self.texte_annonce_input)

        # --- Boutons ---
        btn_save = QPushButton("Enregistrer")
        btn_cancel = QPushButton("Annuler")
        btn_save.setObjectName("PrimaryButton")
        btn_cancel.setObjectName("SecondaryButton")

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)

        # Boutons connectés
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self.accept)
        self.import_btn.clicked.connect(self._on_import_clicked)
        self.import_btn_browser.clicked.connect(self._on_import_clicked_browser)

        # --- Layout global avec Card ---
        form_card = QFrame(self)
        form_card.setObjectName("Card")
        form_layout_card = QVBoxLayout(form_card)
        form_layout_card.setContentsMargins(12, 12, 12, 12)
        form_layout_card.setSpacing(8)

        title_label = QLabel("Nouvelle offre")
        title_label.setProperty("heading", True)
        form_layout_card.addWidget(title_label)

        form_layout_card.addLayout(form_layout)

        layout = QVBoxLayout(self)
        layout.addWidget(form_card)
        layout.addLayout(btn_layout)

    def get_data(self) -> dict[str, str]:
        """Retourne un dict avec toutes les infos saisies."""
        return {
            "titre_poste": self.titre_input.text(),
            "entreprise": self.entreprise_input.text(),
            "source": self.source_input.text(),
            "url": self.url_input.text(),
            "localisation": self.localisation_input.text(),
            "type_contrat": self.type_contrat_input.text(),
            "texte_annonce": self.texte_annonce_input.toPlainText(),
        }

    def _on_import_clicked(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            self._set_import_status("Veuillez d'abord coller une URL.", kind="warning")
            return
        self._set_import_status("Import en cours…", kind="info")
        self.importRequested.emit(url)

    def _on_import_clicked_browser(self) -> None:
        if not HAS_QTWEBENGINE:
            self._set_import_status(
                "QtWebEngine n'est pas installé (pip install PySide6-QtWebEngine).",
                kind="warning",
            )
            return

        url = self.url_input.text().strip()
        if not url:
            self._set_import_status("Veuillez d'abord coller une URL.", kind="warning")
            return

        self._set_import_status("Import navigateur en cours…", kind="info")
        self.importRequestedBrowser.emit(url)

    def set_prefill_data(self, data: dict[str, str]) -> None:
        """Pré-remplit le formulaire avec des données issues d'un import.

        Clés attendues (optionnelles):
        - titre_poste, entreprise, source, url, localisation, type_contrat, texte_annonce
        """
        if not isinstance(data, dict):
            return

        def s(key: str) -> str:
            v = data.get(key, "")
            return v.strip() if isinstance(v, str) else str(v)

        if s("titre_poste"):
            self.titre_input.setText(s("titre_poste"))
        if s("entreprise"):
            self.entreprise_input.setText(s("entreprise"))
        if s("source"):
            self.source_input.setText(s("source"))
        if s("url"):
            self.url_input.setText(s("url"))
        if s("localisation"):
            self.localisation_input.setText(s("localisation"))
        if s("type_contrat"):
            self.type_contrat_input.setText(s("type_contrat"))
        if s("texte_annonce"):
            self.texte_annonce_input.setPlainText(s("texte_annonce"))

        self._set_import_status("Formulaire pré-rempli. Vérifie et complète si nécessaire.", kind="success")

    def set_import_error(self, message: str) -> None:
        self._set_import_status(message or "Erreur lors de l'import.", kind="error")

    def _set_import_status(self, message: str, *, kind: str = "info") -> None:
        # kind: info | success | warning | error
        self.import_status.setText(message)
        self.import_status.setProperty("kind", kind)
        self.import_status.style().unpolish(self.import_status)
        self.import_status.style().polish(self.import_status)
