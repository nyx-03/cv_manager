from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class OfferCard(QFrame):
    """Carte cliquable représentant une offre.

    ObjectName: OfferCard
    Dynamic property used by QSS: status (e.g. A_PREPARER, ENVOYEE, ENTRETIEN, REFUSEE)

    The `offer` object is expected to have (some of) these attributes:
    - titre_poste / titre
    - entreprise
    - localisation / lieu
    - source
    """

    def __init__(self, offer, on_open: Callable[[object], None], parent=None):
        super().__init__(parent)
        self.offer = offer
        self._on_open = on_open

        self.setObjectName("OfferCard")
        # Default status so QSS has something predictable.
        self.setProperty("status", "A_PREPARER")
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_text = (
            getattr(offer, "titre_poste", None)
            or getattr(offer, "titre", None)
            or ""
        )
        company_text = getattr(offer, "entreprise", None) or ""

        self.lbl_title = QLabel(str(title_text))
        self.lbl_title.setObjectName("OfferCardTitle")

        self.lbl_company = QLabel(str(company_text))
        self.lbl_company.setObjectName("OfferCardSubtitle")

        # Optional meta line
        loc = (
            getattr(offer, "localisation", None)
            or getattr(offer, "lieu", None)
            or ""
        )
        source = getattr(offer, "source", None) or ""
        meta_parts = [p for p in (str(loc).strip(), str(source).strip()) if p]
        meta_text = " • ".join(meta_parts)

        self.lbl_meta: Optional[QLabel] = None
        if meta_text:
            self.lbl_meta = QLabel(meta_text)
            self.lbl_meta.setObjectName("OfferCardMeta")

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_company)
        if self.lbl_meta is not None:
            layout.addWidget(self.lbl_meta)
        layout.addStretch(1)

    def mousePressEvent(self, event):
        if callable(self._on_open):
            self._on_open(self.offer)
        super().mousePressEvent(event)

    def set_status(self, status: str):
        """Convenience setter (optional). Prefer setProperty('status', ...) directly."""
        self.setProperty("status", status)
        self.style().unpolish(self)
        self.style().polish(self)
