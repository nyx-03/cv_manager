from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QAbstractItemView,
)
from PySide6.QtCore import Qt

from models import Offre, Candidature, CandidatureStatut


class DashboardWidget(QWidget):
    """Widget de tableau de bord pour le CV Manager.

    Affiche des statistiques globales ainsi que les dernières candidatures.
    """

    def __init__(self, session: object, parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session

        self._setup_ui()
        self.refresh()

    # ---------------------------------------------------------
    # UI SETUP
    # ---------------------------------------------------------
    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        # --- Card : titre général ---
        header_card = QFrame(self)
        header_card.setObjectName("Card")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(12, 12, 12, 12)
        header_layout.setSpacing(4)

        title_label = QLabel("Tableau de bord")
        title_label.setProperty("heading", True)
        header_layout.addWidget(title_label)

        subtitle_label = QLabel("Vue d'ensemble de ta recherche d'emploi")
        header_layout.addWidget(subtitle_label)

        root_layout.addWidget(header_card)

        # --- Card : statistiques globales ---
        stats_card = QFrame(self)
        stats_card.setObjectName("Card")
        stats_layout = QVBoxLayout(stats_card)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(8)

        stats_title = QLabel("Statistiques globales")
        stats_title.setProperty("heading", True)
        stats_layout.addWidget(stats_title)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        # Total offres
        self.label_total_offres = QLabel("Offres : 0")
        # Total candidatures
        self.label_total_candidatures = QLabel("Candidatures : 0")
        # Envoyées
        self.label_envoyees = QLabel("Envoyées : 0")
        # À préparer
        self.label_a_preparer = QLabel("À préparer : 0")
        # Relances
        self.label_relance = QLabel("Relances : 0")
        # Entretiens
        self.label_entretiens = QLabel("Entretiens : 0")

        for lbl in (
            self.label_total_offres,
            self.label_total_candidatures,
            self.label_envoyees,
            self.label_a_preparer,
            self.label_relance,
            self.label_entretiens,
        ):
            stats_row.addWidget(lbl)

        stats_row.addStretch()
        stats_layout.addLayout(stats_row)

        # Bouton de rafraîchissement
        btn_refresh = QPushButton("Rafraîchir le tableau de bord")
        btn_refresh.setObjectName("SecondaryButton")
        btn_refresh.clicked.connect(self.refresh)
        stats_layout.addWidget(btn_refresh)

        root_layout.addWidget(stats_card)

        # --- Card : dernières candidatures ---
        recent_card = QFrame(self)
        recent_card.setObjectName("Card")
        recent_layout = QVBoxLayout(recent_card)
        recent_layout.setContentsMargins(12, 12, 12, 12)
        recent_layout.setSpacing(8)

        recent_title = QLabel("Dernières candidatures")
        recent_title.setProperty("heading", True)
        recent_layout.addWidget(recent_title)

        self.recent_table = QTableWidget()
        self.recent_table.setObjectName("DashboardRecentTable")
        self.recent_table.setColumnCount(4)
        self.recent_table.setHorizontalHeaderLabels([
            "Date",
            "Entreprise",
            "Poste",
            "Statut",
        ])
        self.recent_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.recent_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.recent_table.setAlternatingRowColors(True)

        recent_layout.addWidget(self.recent_table)

        root_layout.addWidget(recent_card)

        root_layout.addStretch()

    # ---------------------------------------------------------
    # DATA REFRESH
    # ---------------------------------------------------------
    def refresh(self) -> None:
        """Recharge les statistiques et la liste des dernières candidatures."""
        self._refresh_stats()
        self._refresh_recent_candidatures()

    def _refresh_stats(self) -> None:
        # Total offres
        total_offres = self.session.query(Offre).count()
        self.label_total_offres.setText(f"Offres : {total_offres}")

        # Total candidatures
        total_cand = self.session.query(Candidature).count()
        self.label_total_candidatures.setText(f"Candidatures : {total_cand}")

        # Par statut
        def count_by_statut(statut: CandidatureStatut) -> int:
            return (
                self.session.query(Candidature)
                .filter(Candidature.statut == statut)
                .count()
            )

        a_preparer = count_by_statut(CandidatureStatut.A_PREPARER)
        envoyees = count_by_statut(CandidatureStatut.ENVOYEE)
        relance = count_by_statut(CandidatureStatut.RELANCE)
        entretiens = count_by_statut(CandidatureStatut.ENTRETIEN)

        self.label_a_preparer.setText(f"À préparer : {a_preparer}")
        self.label_envoyees.setText(f"Envoyées : {envoyees}")
        self.label_relance.setText(f"Relances : {relance}")
        self.label_entretiens.setText(f"Entretiens : {entretiens}")

    def _refresh_recent_candidatures(self, limit: int = 10) -> None:
        rows: list[Candidature]
        # Récupère les dernières candidatures avec jointure sur l'offre
        rows = (
            self.session.query(Candidature)
            .join(Offre)
            .order_by(Candidature.id.desc())
            .limit(limit)
            .all()
        )

        self.recent_table.setRowCount(len(rows))

        for row_idx, cand in enumerate(rows):
            # Date d'envoi si disponible, sinon vide
            date_value = getattr(cand, "date_envoi", None)
            if date_value is not None:
                date_text = date_value.strftime("%d/%m/%Y")
            else:
                date_text = "-"

            entreprise = cand.offre.entreprise or ""
            poste = getattr(cand.offre, "titre_poste", "") or ""
            statut_text = cand.statut.label() if hasattr(cand.statut, "label") else str(cand.statut)

            date_item = QTableWidgetItem(date_text)
            entreprise_item = QTableWidgetItem(entreprise)
            poste_item = QTableWidgetItem(poste)
            statut_item = QTableWidgetItem(statut_text)

            self.recent_table.setItem(row_idx, 0, date_item)
            self.recent_table.setItem(row_idx, 1, entreprise_item)
            self.recent_table.setItem(row_idx, 2, poste_item)
            self.recent_table.setItem(row_idx, 3, statut_item)