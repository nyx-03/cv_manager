from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget

from ui.sidebar import Sidebar
from ui.dashboard_widget import DashboardWidget
from ui.stats_widget import StatsWidget
from ui.settings_widget import SettingsWidget
from ui.offer_list_widget import OfferListWidget
from ui.pages.offer_detail_page import OfferDetailPage, LetterViewModel
from ui.pages.offer_form_page import OfferFormPage

from models import Offre

from services.candidatures_service import OfferCandidatureStats


# --- Page indices (QStackedWidget) ---
PAGE_DASHBOARD = 0
PAGE_OFFERS = 1
PAGE_STATS = 2
PAGE_SETTINGS = 3
PAGE_OFFER_DETAIL = 4
PAGE_ADD_OFFER = 5


class ApplicationView(QWidget):
    """Vue principale de l'application (UI only).

    Cette classe encapsule:
    - Sidebar
    - QStackedWidget (pages)

    Elle ne fait PAS de requêtes DB elle-même: la couche MainWindow (ou Controller)
    lui pousse les données via:
    - set_offers(...)
    - show_offer_detail(...)
    - set_offer_detail_letters(...)

    Signaux exposés pour permettre au contrôleur d'agir:
    - newOfferRequested()
    - prepareLetterRequested()
    - showCandidaturesRequested()
    - refreshRequested()
    - offerClicked(offre)
    - backToOffersRequested()
    - openLetterRequested(candidature_id)
    - markSentRequested(candidature_id)
    - deleteRequested(candidature_id)
    - deleteOfferRequested(offer_id)
    """

    # Sidebar actions
    newOfferRequested = Signal()
    prepareLetterRequested = Signal()
    showCandidaturesRequested = Signal()
    refreshRequested = Signal()

    # Navigation/data
    offerClicked = Signal(object)

    # Offer detail actions
    backToOffersRequested = Signal()
    openLetterRequested = Signal(int)
    markSentRequested = Signal(int)
    deleteRequested = Signal(int)
    deleteOfferRequested = Signal(int)

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session

        self.current_offer: Optional[Offre] = None

        # 1) Widgets
        self.sidebar = Sidebar(self)

        self.offers_page = OfferListWidget(
            parent=self,
            title="Annonces",
            columns=3,
        )
        self.offer_detail_page = OfferDetailPage(self)
        self.offer_form_page = OfferFormPage(self)
        self.dashboard = DashboardWidget(self.session, self)
        self.stats = StatsWidget(self.session, self)
        self.settings = SettingsWidget(self.session, self)

        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.dashboard)         # 0
        self.stack.addWidget(self.offers_page)       # 1
        self.stack.addWidget(self.stats)             # 2
        self.stack.addWidget(self.settings)          # 3
        self.stack.addWidget(self.offer_detail_page) # 4
        self.stack.addWidget(self.offer_form_page)   # 5

        # 2) Layouts
        self.root_layout = QHBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.main_container = QWidget(self)
        self.main_layout = QVBoxLayout(self.main_container)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(8)
        self.main_layout.addWidget(self.stack)

        # 3) Assemble
        self.root_layout.addWidget(self.sidebar)
        self.root_layout.addWidget(self.main_container)

        # 4) Connections
        self._create_connections()

        # Default page
        self.set_page(PAGE_OFFERS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def current_page(self) -> int:
        return self.stack.currentIndex()

    def set_offers_status_resolver(self, resolver: Callable[[object], str]) -> None:
        self.offers_page.set_status_resolver(resolver)

    def set_offers_candidature_stats_resolver(
        self, resolver: Callable[[object], OfferCandidatureStats]
    ) -> None:
        """Injecte une fonction qui retourne les stats de candidatures pour une offre.

        Cette méthode délègue au composant de la page Offres si celui-ci expose
        `set_candidature_stats_resolver` (OffersPage) ou une API équivalente.
        """
        if hasattr(self.offers_page, "set_candidature_stats_resolver"):
            self.offers_page.set_candidature_stats_resolver(resolver)

    def set_offers(self, offers) -> None:
        self.offers_page.set_offers(offers)

    def show_offer_detail(self, offre: Offre) -> None:
        self.current_offer = offre
        self.offer_detail_page.set_offer(offre)
        self.set_page(PAGE_OFFER_DETAIL)

    def set_offer_detail_letters(self, letter_vms: list[LetterViewModel]) -> None:
        self.offer_detail_page.set_letters(letter_vms)

    def refresh_dashboard(self) -> None:
        if hasattr(self.dashboard, "refresh"):
            self.dashboard.refresh()

    def refresh_stats(self) -> None:
        if hasattr(self.stats, "refresh"):
            self.stats.refresh()

    def show_add_offer(self) -> None:
        self.offer_form_page.reset_form()
        self.set_page(PAGE_ADD_OFFER)

    def show_edit_offer(self, offre: Offre) -> None:
        self.offer_form_page.load_offer(offre)
        self.set_page(PAGE_ADD_OFFER)

    def show_offers(self) -> None:
        """Show offers list page."""
        self.set_page(PAGE_OFFERS)

    def show_dashboard(self) -> None:
        self.set_page(PAGE_DASHBOARD)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _create_connections(self) -> None:
        # Offers
        self.offers_page.offerClicked.connect(self.offerClicked.emit)

        # Detail page
        self.offer_detail_page.backRequested.connect(self.show_offers)
        self.offer_detail_page.openLetterRequested.connect(self.openLetterRequested.emit)
        self.offer_detail_page.markSentRequested.connect(self.markSentRequested.emit)
        self.offer_detail_page.deleteRequested.connect(self.deleteRequested.emit)
        self.offer_detail_page.deleteOfferRequested.connect(self.deleteOfferRequested.emit)

        # Offer form page (add / edit)
        self.offer_form_page.saved.connect(self._on_offer_saved)
        self.offer_form_page.cancelled.connect(self._on_offer_cancelled)

        # Sidebar
        self.sidebar.navigateRequested.connect(self._handle_sidebar_nav)
        self.sidebar.actionRequested.connect(self._handle_sidebar_action)

        # Sync active state
        self.stack.currentChanged.connect(self._sync_active_page)
        self._sync_active_page(self.stack.currentIndex())

    def _handle_sidebar_nav(self, page_name: str) -> None:
        mapping = {
            self.sidebar.pages.DASHBOARD: PAGE_DASHBOARD,
            self.sidebar.pages.OFFERS: PAGE_OFFERS,
            self.sidebar.pages.STATS: PAGE_STATS,
            self.sidebar.pages.SETTINGS: PAGE_SETTINGS,
        }
        if page_name in mapping:
            self.set_page(mapping[page_name])

    def _handle_sidebar_action(self, action_name: str) -> None:
        if action_name == self.sidebar.actions.NEW_OFFER:
            self.show_add_offer()
        elif action_name == self.sidebar.actions.PREPARE_LETTER:
            self.prepareLetterRequested.emit()
        elif action_name == self.sidebar.actions.SHOW_CANDIDATURES:
            self.showCandidaturesRequested.emit()
        elif action_name == self.sidebar.actions.REFRESH:
            self.refreshRequested.emit()

    def _sync_active_page(self, index: int) -> None:
        if index == PAGE_DASHBOARD:
            self.sidebar.set_active_page(self.sidebar.pages.DASHBOARD)
        elif index in (PAGE_OFFERS, PAGE_OFFER_DETAIL, PAGE_ADD_OFFER):
            # Détail = sous-section des offres
            self.sidebar.set_active_page(self.sidebar.pages.OFFERS)
        elif index == PAGE_STATS:
            self.sidebar.set_active_page(self.sidebar.pages.STATS)
        elif index == PAGE_SETTINGS:
            self.sidebar.set_active_page(self.sidebar.pages.SETTINGS)

    # ------------------------------------------------------------------
    # Offer form handlers
    # ------------------------------------------------------------------

    def _on_offer_saved(self, offre: Offre) -> None:
        """Called when an offer has been created or updated from OfferFormPage."""
        self.current_offer = offre
        self.show_offers()
        self.refreshRequested.emit()
        self.refresh_dashboard()

    def _on_offer_cancelled(self) -> None:
        """Called when user clicks 'Retour' in OfferFormPage."""
        self.show_offers()