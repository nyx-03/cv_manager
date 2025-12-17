"""OfferListWidget

Ce widget sert de couche d'abstraction pour la liste d'offres.

Historique:
- On a une UI moderne basée sur `OffersPage` (cartes, 3 colonnes, scroll).
- `OfferListWidget` permet de garder un nom "liste" côté code et d'éviter
  de toucher partout si on veut:
  - revenir à une vue tableau/liste,
  - proposer un toggle "cartes" / "liste",
  - ou factoriser des éléments UI (toolbar locale, filtres).

Aujourd'hui, ce widget wrap simplement `OffersPage`.

QSS:
- Tout le style est porté par `OffersPage` / `OfferCard` (via objectName + propriétés).
"""

from collections.abc import Callable, Iterable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from ui.pages.offers_page import OffersPage
from services.candidatures_service import OfferCandidatureStats


class OfferListWidget(QWidget):
    """Widget "liste" des offres (actuellement = vues cartes).

    API volontairement minimaliste:
    - set_offers(offers)
    - set_status_resolver(resolver)
    - set_columns(n)

    Signaux:
    - offerClicked(offer)
    """

    offerClicked = Signal(object)

    def __init__(
        self,
        parent: QWidget | None = None,
        title: str = "Annonces",
        columns: int = 3,
        status_resolver: Callable[[object], str] | None = None,
    ):
        super().__init__(parent)

        self._page = OffersPage(
            parent=self,
            title=title,
            columns=columns,
            status_resolver=status_resolver,
        )
        self._page.offerClicked.connect(self.offerClicked.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._page)

    # ---------------------------
    # Public API
    # ---------------------------

    def set_offers(self, offers: Iterable[object]) -> None:
        self._page.set_offers(offers)

    def set_status_resolver(self, resolver: Callable[[object], str] | None) -> None:
        self._page.set_status_resolver(resolver)

    def set_candidature_stats_resolver(
        self,
        resolver: Callable[[object], OfferCandidatureStats] | None,
    ) -> None:
        """Injecte un resolver de statistiques de candidatures vers OffersPage."""
        if hasattr(self._page, "set_candidature_stats_resolver"):
            self._page.set_candidature_stats_resolver(resolver)

    def set_columns(self, columns: int) -> None:
        self._page.set_columns(columns)

    # ---------------------------
    # Access (if needed)
    # ---------------------------

    @property
    def offers_page(self) -> OffersPage:
        """Accès au widget interne (utile si on veut brancher des options avancées)."""
        return self._page
