from __future__ import annotations

from typing import Callable, Iterable, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QScrollArea,
    QGridLayout,
    QVBoxLayout,
    QSizePolicy,
)

from ui.widgets.offer_card import OfferCard


class OffersPage(QWidget):
    """Page "Annonces" : grille de cartes (3 colonnes) avec scroll.

    - Utilise OfferCard (ui/widgets/offer_card.py)
    - Émet offerClicked(offer) au clic sur une carte
    - Le style (couleurs statuts, hover, etc.) est géré par QSS via :
      - objectName "OfferCard"
      - dynamic property "status"
    """

    offerClicked = Signal(object)

    def __init__(
        self,
        parent=None,
        title: str = "Annonces",
        columns: int = 3,
        status_resolver: Optional[Callable[[object], str]] = None,
    ):
        super().__init__(parent)
        self._columns = max(1, int(columns))
        self._status_resolver = status_resolver
        self._offers: list[object] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self.lbl_title = QLabel(title)
        self.lbl_title.setProperty("heading", True)
        root.addWidget(self.lbl_title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)

        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(10)

        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll)

    # ---------------------------
    # Public API
    # ---------------------------

    def set_columns(self, columns: int) -> None:
        self._columns = max(1, int(columns))
        self._render()

    def set_status_resolver(self, resolver: Optional[Callable[[object], str]]) -> None:
        """Permet à la MainWindow (ou un service) de définir comment calculer le statut d'une offre."""
        self._status_resolver = resolver
        self._render()

    def set_offers(self, offers: Iterable[object]) -> None:
        self._offers = list(offers)
        self._render()

    def offers(self) -> list[object]:
        return list(self._offers)

    # ---------------------------
    # Rendering
    # ---------------------------

    def _clear_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _on_card_clicked(self, offer: object) -> None:
        self.offerClicked.emit(offer)

    def _apply_status(self, card: OfferCard, offer: object) -> None:
        status = "A_PREPARER"
        if self._status_resolver is not None:
            try:
                status = str(self._status_resolver(offer) or "A_PREPARER")
            except Exception:
                status = "A_PREPARER"
        card.setProperty("status", status)
        # Re-polish pour forcer Qt à ré-appliquer les sélecteurs QSS basés sur la propriété.
        card.style().unpolish(card)
        card.style().polish(card)

    def _render(self) -> None:
        self._clear_grid()

        if not self._offers:
            empty = QLabel("Aucune annonce pour le moment.")
            empty.setObjectName("EmptyState")
            empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.grid.addWidget(empty, 0, 0, 1, self._columns)
            return

        cols = self._columns
        for i, offer in enumerate(self._offers):
            row = i // cols
            col = i % cols

            card = OfferCard(offer, self._on_card_clicked, self)
            self._apply_status(card, offer)
            self.grid.addWidget(card, row, col)

        for c in range(cols):
            self.grid.setColumnStretch(c, 1)

        # Spacer pour pousser le contenu vers le haut
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        last_row = (len(self._offers) - 1) // cols
        self.grid.addWidget(spacer, last_row + 1, 0, 1, cols)
