# NOTE: Ce dialogue est désormais remplacé par la page Paramètres (SettingsWidget).
# ui/profile_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QHBoxLayout
)


class ProfileDialog(QDialog):
    def __init__(self, profil=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Profil candidat")
        self.resize(500, 600)

        self.profil = profil

        # --- Champs ---
        self.nom_input = QLineEdit()
        self.prenom_input = QLineEdit()
        self.email_input = QLineEdit()
        self.telephone_input = QLineEdit()
        self.ville_input = QLineEdit()
        self.titre_input = QLineEdit()
        self.resume_input = QTextEdit()
        self.resume_input.setPlaceholderText("Résumé / pitch professionnel")

        self.linkedin_input = QLineEdit()
        self.github_input = QLineEdit()
        self.portfolio_input = QLineEdit()

        # Si un profil existe déjà, pré-remplir
        if self.profil is not None:
            self.nom_input.setText(self.profil.nom or "")
            self.prenom_input.setText(self.profil.prenom or "")
            self.email_input.setText(self.profil.email or "")
            self.telephone_input.setText(self.profil.telephone or "")
            self.ville_input.setText(self.profil.ville or "")
            self.titre_input.setText(self.profil.titre or "")
            self.resume_input.setPlainText(self.profil.resume or "")
            self.linkedin_input.setText(self.profil.lien_linkedin or "")
            self.github_input.setText(self.profil.lien_github or "")
            self.portfolio_input.setText(self.profil.lien_portfolio or "")

        # --- Layout formulaire ---
        form_layout = QFormLayout()
        form_layout.addRow("Nom :", self.nom_input)
        form_layout.addRow("Prénom :", self.prenom_input)
        form_layout.addRow("Email :", self.email_input)
        form_layout.addRow("Téléphone :", self.telephone_input)
        form_layout.addRow("Ville :", self.ville_input)
        form_layout.addRow("Titre :", self.titre_input)
        form_layout.addRow("Résumé :", self.resume_input)
        form_layout.addRow("LinkedIn :", self.linkedin_input)
        form_layout.addRow("GitHub :", self.github_input)
        form_layout.addRow("Portfolio :", self.portfolio_input)

        # --- Boutons ---
        btn_save = QPushButton("Enregistrer")
        btn_cancel = QPushButton("Annuler")

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)

        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self.accept)

        # --- Layout global ---
        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addLayout(btn_layout)

    def apply_to_model(self, profil):
        """Copie les valeurs des champs dans l'objet ProfilCandidat passé."""
        profil.nom = self.nom_input.text().strip()
        profil.prenom = self.prenom_input.text().strip()
        profil.email = self.email_input.text().strip()
        profil.telephone = self.telephone_input.text().strip()
        profil.ville = self.ville_input.text().strip()
        profil.titre = self.titre_input.text().strip()
        profil.resume = self.resume_input.toPlainText().strip()
        profil.lien_linkedin = self.linkedin_input.text().strip()
        profil.lien_github = self.github_input.text().strip()
        profil.lien_portfolio = self.portfolio_input.text().strip()