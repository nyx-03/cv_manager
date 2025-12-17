from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QFrame,
)
from PySide6.QtCore import Qt, QUrl, QSize, QPoint
from PySide6.QtGui import QDesktopServices, QColor

from pathlib import Path
from datetime import date

from models import Offre, Candidature, CandidatureStatut


class CandidaturesWindow(QDialog):
    """
    Fenêtre affichant toutes les candidatures existantes,
    avec recherche, filtre par statut et actions de base.
    """

    def __init__(self, session: object, parent: QDialog | None = None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Toutes les candidatures")
        self.resize(900, 600)

        self._setup_ui()
        self.load_candidatures()

    # ---------------------------------------------------------
    # UI SETUP
    # ---------------------------------------------------------
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # --- Card principale : titre + tableau + boutons ---
        main_card = QFrame(self)
        main_card.setObjectName("Card")
        main_layout = QVBoxLayout(main_card)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Titre de la card
        title_label = QLabel("Toutes les candidatures")
        title_label.setProperty("heading", True)
        main_layout.addWidget(title_label)

        # --- Card secondaire : barre de recherche ---
        search_card = QFrame(self)
        search_card.setObjectName("Card")
        search_layout_card = QVBoxLayout(search_card)
        search_layout_card.setContentsMargins(12, 12, 12, 12)
        search_layout_card.setSpacing(8)

        search_layout = QHBoxLayout()
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Rechercher (entreprise / poste)")
        self.input_search.textChanged.connect(self.apply_filters)

        self.combo_statut = QComboBox()
        statut_labels = ["Tous"] + [s.label() for s in CandidatureStatut]
        self.combo_statut.addItems(statut_labels)
        self.combo_statut.currentIndexChanged.connect(self.apply_filters)

        search_layout.addWidget(QLabel("Recherche :"))
        search_layout.addWidget(self.input_search)
        search_layout.addWidget(QLabel("Statut :"))
        search_layout.addWidget(self.combo_statut)

        search_layout_card.addLayout(search_layout)

        # --- Tableau ---
        self.table = QTableWidget()
        self.table.setObjectName("CandidaturesTable")
        self.table.setColumnCount(5)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setHorizontalHeaderLabels(
            ["Entreprise", "Poste", "Date", "Statut", "Lettre"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.open_letter)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # --- Boutons ---
        buttons_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("Rafraîchir")
        self.btn_refresh.setObjectName("SecondaryButton")
        self.btn_refresh.clicked.connect(self.load_candidatures)

        self.btn_mark_sent = QPushButton("Marquer comme envoyée")
        self.btn_mark_sent.setObjectName("PrimaryButton")
        self.btn_mark_sent.clicked.connect(self.mark_selected_sent)

        self.btn_delete = QPushButton("Supprimer")
        self.btn_delete.setObjectName("DangerButton")
        self.btn_delete.clicked.connect(self.delete_selected)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_refresh)
        buttons_layout.addWidget(self.btn_mark_sent)
        buttons_layout.addWidget(self.btn_delete)

        # Assemblage des cards et contenu
        main_layout.addWidget(search_card)
        main_layout.addWidget(self.table)
        main_layout.addLayout(buttons_layout)

        layout.addWidget(main_card)

    # ---------------------------------------------------------
    # DATA LOADING
    # ---------------------------------------------------------
    def load_candidatures(self) -> None:
        """Charge toutes les candidatures en base."""
        self.all_rows: list[Candidature]
        self.all_rows = (
            self.session.query(Candidature)
            .join(Offre)
            .order_by(Candidature.id.desc())
            .all()
        )
        self.apply_filters()

    def apply_filters(self) -> None:
        search_text = self.input_search.text().lower().strip()
        statut_filter = self.combo_statut.currentText()

        filtered = []
        for cand in self.all_rows:
            entreprise = (cand.offre.entreprise or "").lower()
            poste = (getattr(cand.offre, "titre_poste", None) or "").lower()

            if search_text and search_text not in entreprise and search_text not in poste:
                continue

            if statut_filter != "Tous":
                label = cand.statut.label() if hasattr(cand.statut, "label") else str(cand.statut)
                if label != statut_filter:
                    continue

            filtered.append(cand)

        self.display_rows(filtered)

    def display_rows(self, rows: list[Candidature]) -> None:
        self.table.setRowCount(len(rows))

        for row_idx, cand in enumerate(rows):
            entreprise_item = QTableWidgetItem(cand.offre.entreprise or "")
            poste_item = QTableWidgetItem(getattr(cand.offre, "titre_poste", "") or "")
            date_item = QTableWidgetItem(cand.date_envoi.strftime("%d/%m/%Y") if cand.date_envoi else "-")
            statut_text = cand.statut.label() if hasattr(cand.statut, "label") else str(cand.statut)
            statut_item = QTableWidgetItem(statut_text)
            lettre_item = QTableWidgetItem(cand.chemin_lettre or "-")

            self.table.setItem(row_idx, 0, entreprise_item)
            self.table.setItem(row_idx, 1, poste_item)
            self.table.setItem(row_idx, 2, date_item)
            self.table.setItem(row_idx, 3, statut_item)
            self.table.setItem(row_idx, 4, lettre_item)

            # Coloration de ligne selon le statut
            bg_color = None
            if cand.statut == CandidatureStatut.A_PREPARER:
                bg_color = QColor("#fef9c3")  # jaune pâle
            elif hasattr(CandidatureStatut, "A_ENVOYER") and cand.statut == CandidatureStatut.A_ENVOYER:
                bg_color = QColor("#dbeafe")  # bleu très clair
            elif cand.statut == CandidatureStatut.ENVOYEE:
                bg_color = QColor("#dcfce7")  # vert clair
            elif cand.statut == CandidatureStatut.RELANCE:
                bg_color = QColor("#fce7f3")  # rose clair
            elif cand.statut == CandidatureStatut.ENTRETIEN:
                bg_color = QColor("#ede9fe")  # violet clair
            elif cand.statut == CandidatureStatut.REFUSEE:
                bg_color = QColor("#fee2e2")  # rouge très clair
            elif cand.statut == CandidatureStatut.ARCHIVEE:
                bg_color = QColor("#e5e7eb")  # gris clair

            if bg_color is not None:
                for col in range(5):
                    item = self.table.item(row_idx, col)
                    if item is not None:
                        item.setBackground(bg_color)

    # ---------------------------------------------------------
    # ACTIONS
    # ---------------------------------------------------------
    def get_selected_candidature(self) -> Candidature | None:
        row = self.table.currentRow()
        if row < 0:
            return None

        entreprise = self.table.item(row, 0).text()
        poste = self.table.item(row, 1).text()

        return (
            self.session.query(Candidature)
            .join(Offre)
            .filter(Offre.entreprise == entreprise, Offre.titre_poste == poste)
            .first()
        )

    def open_letter(self) -> None:
        cand = self.get_selected_candidature()
        if not cand:
            return

        if not cand.chemin_lettre:
            QMessageBox.information(self, "Aucune lettre", "Aucune lettre associée.")
            return

        path = Path(cand.chemin_lettre)
        if not path.exists():
            QMessageBox.critical(self, "Erreur", f"Le fichier de lettre n'existe pas :\n{path}")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))

    def delete_selected(self) -> None:
        cand = self.get_selected_candidature()
        if not cand:
            QMessageBox.warning(self, "Aucune sélection", "Aucune candidature sélectionnée.")
            return

        confirm = QMessageBox.question(
            self,
            "Supprimer",
            "Supprimer cette candidature ?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if confirm == QMessageBox.Yes:
            self.session.delete(cand)
            self.session.commit()
            self.load_candidatures()

    def mark_selected_sent(self) -> None:
        cand = self.get_selected_candidature()
        if not cand:
            QMessageBox.warning(self, "Aucune sélection", "Aucune candidature sélectionnée.")
            return

        if cand.statut == CandidatureStatut.ENVOYEE:
            QMessageBox.information(self, "Déjà envoyée", "Cette candidature est déjà marquée comme envoyée.")
            return

        cand.statut = CandidatureStatut.ENVOYEE
        cand.date_envoi = date.today()
        self.session.commit()
        self.load_candidatures()

    def show_context_menu(self, pos: QPoint) -> None:
        index = self.table.indexAt(pos)
        if not index.isValid():
            return

        # Positionne la sélection sur la ligne cliquée
        self.table.setCurrentIndex(index)
        cand = self.get_selected_candidature()
        if not cand:
            return

        menu = QMenu(self)

        # Action pour ouvrir la lettre
        action_open = menu.addAction("Ouvrir la lettre")
        menu.addSeparator()

        # Sous-menu pour changer le statut
        statut_menu = menu.addMenu("Changer le statut")
        for statut in CandidatureStatut:
            label = statut.label() if hasattr(statut, "label") else str(getattr(statut, "value", statut))
            action = statut_menu.addAction(label)
            action.setData(statut)
            # Cocher le statut actuel
            action.setCheckable(True)
            if cand.statut == statut:
                action.setChecked(True)

        menu.addSeparator()

        # Actions directes supplémentaires
        action_mark_sent = menu.addAction("Marquer comme envoyée")
        action_delete = menu.addAction("Supprimer la candidature")

        chosen_action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if not chosen_action:
            return

        if chosen_action == action_open:
            self.open_letter()
            return

        if chosen_action == action_mark_sent:
            self.mark_selected_sent()
            return

        if chosen_action == action_delete:
            self.delete_selected()
            return

        # Sinon, c'est un changement de statut via le sous-menu
        new_statut = chosen_action.data()
        if not isinstance(new_statut, CandidatureStatut):
            return

        # Mise à jour du statut et de la date d'envoi si pertinent
        cand.statut = new_statut
        if new_statut == CandidatureStatut.ENVOYEE and cand.date_envoi is None:
            cand.date_envoi = date.today()

        self.session.commit()
        self.load_candidatures()