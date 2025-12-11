# ui/offer_form_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QHBoxLayout, QFrame, QLabel
)


class OfferFormDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Nouvelle offre")
        self.resize(500, 600)

        # --- Champs du formulaire ---
        self.titre_input = QLineEdit()
        self.entreprise_input = QLineEdit()
        self.source_input = QLineEdit()
        self.url_input = QLineEdit()
        self.localisation_input = QLineEdit()
        self.type_contrat_input = QLineEdit()

        self.texte_annonce_input = QTextEdit()
        self.texte_annonce_input.setPlaceholderText("Colle ici le texte complet de l'annonce")

        # --- Layout formulaire ---
        form_layout = QFormLayout()
        form_layout.addRow("Titre du poste :", self.titre_input)
        form_layout.addRow("Entreprise :", self.entreprise_input)
        form_layout.addRow("Source :", self.source_input)
        form_layout.addRow("URL :", self.url_input)
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

    def get_data(self):
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
