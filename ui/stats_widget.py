

from collections import Counter
from datetime import datetime

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
    QHeaderView,
)
from PySide6.QtCore import Qt

from models import Offre, Candidature, CandidatureStatut


class StatsWidget(QWidget):
    """
    Widget de statistiques pour le CV Manager.

    Affiche des statistiques détaillées :
    - répartition des candidatures par statut
    - répartition des candidatures par entreprise (Top N)
    - répartition des candidatures par mois (sur la base de date_envoi)
    """

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session

        self._setup_ui()
        self.refresh()

    # ---------------------------------------------------------
    # UI SETUP
    # ---------------------------------------------------------
    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        # --- Card : titre général ---
        header_card = QFrame(self)
        header_card.setObjectName("Card")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(12, 12, 12, 12)
        header_layout.setSpacing(4)

        title_label = QLabel("Statistiques")
        title_label.setProperty("heading", True)
        header_layout.addWidget(title_label)

        subtitle_label = QLabel("Analyse détaillée de tes candidatures")
        header_layout.addWidget(subtitle_label)

        root_layout.addWidget(header_card)

        # --- Card : résumé global ---
        summary_card = QFrame(self)
        summary_card.setObjectName("Card")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        summary_layout.setSpacing(8)

        summary_title = QLabel("Résumé global")
        summary_title.setProperty("heading", True)
        summary_layout.addWidget(summary_title)

        self.label_total_candidatures = QLabel("Total candidatures : 0")
        self.label_total_offres = QLabel("Total offres : 0")
        self.label_dernier_mois = QLabel("Candidatures envoyées ce mois-ci : 0")

        summary_row = QHBoxLayout()
        summary_row.addWidget(self.label_total_candidatures)
        summary_row.addWidget(self.label_total_offres)
        summary_row.addWidget(self.label_dernier_mois)
        summary_row.addStretch()

        summary_layout.addLayout(summary_row)

        btn_refresh = QPushButton("Rafraîchir les statistiques")
        btn_refresh.setObjectName("SecondaryButton")
        btn_refresh.clicked.connect(self.refresh)
        summary_layout.addWidget(btn_refresh)

        root_layout.addWidget(summary_card)

        # --- Card : par statut ---
        status_card = QFrame(self)
        status_card.setObjectName("Card")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(12, 12, 12, 12)
        status_layout.setSpacing(8)

        status_title = QLabel("Candidatures par statut")
        status_title.setProperty("heading", True)
        status_layout.addWidget(status_title)

        self.table_by_status = QTableWidget()
        self.table_by_status.setObjectName("StatsByStatusTable")
        self.table_by_status.setColumnCount(2)
        self.table_by_status.setHorizontalHeaderLabels(["Statut", "Nombre"])
        self.table_by_status.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_by_status.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_by_status.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_by_status.setAlternatingRowColors(True)

        status_layout.addWidget(self.table_by_status)
        root_layout.addWidget(status_card)

        # --- Card : par entreprise ---
        company_card = QFrame(self)
        company_card.setObjectName("Card")
        company_layout = QVBoxLayout(company_card)
        company_layout.setContentsMargins(12, 12, 12, 12)
        company_layout.setSpacing(8)

        company_title = QLabel("Candidatures par entreprise (Top 10)")
        company_title.setProperty("heading", True)
        company_layout.addWidget(company_title)

        self.table_by_company = QTableWidget()
        self.table_by_company.setObjectName("StatsByCompanyTable")
        self.table_by_company.setColumnCount(2)
        self.table_by_company.setHorizontalHeaderLabels(["Entreprise", "Nombre"])
        self.table_by_company.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_by_company.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_by_company.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_by_company.setAlternatingRowColors(True)

        company_layout.addWidget(self.table_by_company)
        root_layout.addWidget(company_card)

        # --- Card : par mois ---
        month_card = QFrame(self)
        month_card.setObjectName("Card")
        month_layout = QVBoxLayout(month_card)
        month_layout.setContentsMargins(12, 12, 12, 12)
        month_layout.setSpacing(8)

        month_title = QLabel("Candidatures par mois (basées sur la date d'envoi)")
        month_title.setProperty("heading", True)
        month_layout.addWidget(month_title)

        self.table_by_month = QTableWidget()
        self.table_by_month.setObjectName("StatsByMonthTable")
        self.table_by_month.setColumnCount(2)
        self.table_by_month.setHorizontalHeaderLabels(["Mois", "Candidatures envoyées"])
        self.table_by_month.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_by_month.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_by_month.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_by_month.setAlternatingRowColors(True)

        month_layout.addWidget(self.table_by_month)
        root_layout.addWidget(month_card)

        root_layout.addStretch()

    # ---------------------------------------------------------
    # DATA REFRESH
    # ---------------------------------------------------------
    def refresh(self):
        """Recharge les statistiques complètes."""
        self._refresh_summary()
        self._refresh_by_status()
        self._refresh_by_company()
        self._refresh_by_month()

    def _refresh_summary(self):
        total_cand = self.session.query(Candidature).count()
        total_offres = self.session.query(Offre).count()

        # Candidatures envoyées ce mois-ci
        now = datetime.now()
        first_day = datetime(now.year, now.month, 1)
        cand_this_month = (
            self.session.query(Candidature)
            .filter(Candidature.date_envoi != None)  # noqa: E711
            .filter(Candidature.date_envoi >= first_day.date())
            .count()
        )

        self.label_total_candidatures.setText(f"Total candidatures : {total_cand}")
        self.label_total_offres.setText(f"Total offres : {total_offres}")
        self.label_dernier_mois.setText(f"Candidatures envoyées ce mois-ci : {cand_this_month}")

    def _refresh_by_status(self):
        # Compte les candidatures par statut
        counts = {}
        for statut in CandidatureStatut:
            nb = (
                self.session.query(Candidature)
                .filter(Candidature.statut == statut)
                .count()
            )
            counts[statut] = nb

        self.table_by_status.setRowCount(len(counts))

        for row_idx, (statut, nb) in enumerate(counts.items()):
            label = statut.label() if hasattr(statut, "label") else str(statut)
            statut_item = QTableWidgetItem(label)
            nb_item = QTableWidgetItem(str(nb))

            self.table_by_status.setItem(row_idx, 0, statut_item)
            self.table_by_status.setItem(row_idx, 1, nb_item)

    def _refresh_by_company(self, limit: int = 10):
        # Récupère toutes les candidatures avec leur entreprise et compte par entreprise
        rows = (
            self.session.query(Candidature)
            .join(Offre)
            .all()
        )

        counter = Counter()
        for cand in rows:
            entreprise = cand.offre.entreprise or "Sans nom"
            counter[entreprise] += 1

        top = counter.most_common(limit)

        self.table_by_company.setRowCount(len(top))

        for row_idx, (entreprise, nb) in enumerate(top):
            entreprise_item = QTableWidgetItem(entreprise)
            nb_item = QTableWidgetItem(str(nb))

            self.table_by_company.setItem(row_idx, 0, entreprise_item)
            self.table_by_company.setItem(row_idx, 1, nb_item)

    def _refresh_by_month(self):
        # Récupère toutes les candidatures avec une date d'envoi
        rows = (
            self.session.query(Candidature)
            .filter(Candidature.date_envoi != None)  # noqa: E711
            .all()
        )

        counter = Counter()
        for cand in rows:
            d = cand.date_envoi
            if d is None:
                continue
            key = f"{d.month:02d}/{d.year}"
            counter[key] += 1

        # Tri par année/mois chronologique
        def parse_key(k: str):
            month_str, year_str = k.split("/")
            return int(year_str), int(month_str)

        sorted_items = sorted(counter.items(), key=lambda item: parse_key(item[0]))

        self.table_by_month.setRowCount(len(sorted_items))

        for row_idx, (month_label, nb) in enumerate(sorted_items):
            month_item = QTableWidgetItem(month_label)
            nb_item = QTableWidgetItem(str(nb))

            self.table_by_month.setItem(row_idx, 0, month_item)
            self.table_by_month.setItem(row_idx, 1, nb_item)