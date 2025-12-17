from collections.abc import Callable, Mapping

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QPushButton


class OfferCard(QFrame):
    editRequested = Signal(object)
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

        # Prevent the card from growing vertically inside the grid cell.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title_text = (
            getattr(offer, "titre_poste", None)
            or getattr(offer, "titre", None)
            or ""
        )
        company_text = getattr(offer, "entreprise", None) or ""

        self.lbl_title = QLabel(str(title_text))
        self.lbl_title.setObjectName("OfferCardTitle")
        self.lbl_title.setWordWrap(True)

        self.btn_edit = QPushButton("✏️")
        self.btn_edit.setObjectName("OfferCardEditButton")
        self.btn_edit.setCursor(Qt.PointingHandCursor)
        self.btn_edit.setToolTip("Modifier l'annonce")
        self.btn_edit.setFlat(True)
        self.btn_edit.setFocusPolicy(Qt.NoFocus)
        self.btn_edit.setFixedSize(28, 28)
        self.btn_edit.clicked.connect(lambda: self.editRequested.emit(self.offer))

        header.addWidget(self.lbl_title, 1)
        header.addWidget(self.btn_edit, 0, Qt.AlignTop)

        self.lbl_company = QLabel(str(company_text))
        self.lbl_company.setObjectName("OfferCardSubtitle")
        self.lbl_company.setWordWrap(True)

        # Optional meta line
        loc = (
            getattr(offer, "localisation", None)
            or getattr(offer, "lieu", None)
            or ""
        )
        source = getattr(offer, "source", None) or ""
        meta_parts = [p for p in (str(loc).strip(), str(source).strip()) if p]
        meta_text = " • ".join(meta_parts)

        self.lbl_meta: QLabel | None = None
        if meta_text:
            self.lbl_meta = QLabel(meta_text)
            self.lbl_meta.setObjectName("OfferCardMeta")

        # --- Candidature stats (optional) ---
        self._stats_total: int = 0
        self._stats_by_status: dict[str, int] = {}

        self.badges_row = QHBoxLayout()
        self.badges_row.setSpacing(6)
        self.badges_row.setContentsMargins(0, 4, 0, 0)

        self.lbl_badge_total: QLabel | None = None
        self._status_badges: dict[str, QLabel] = {}

        layout.addLayout(header)
        layout.addWidget(self.lbl_company)
        if self.lbl_meta is not None:
            layout.addWidget(self.lbl_meta)

        # Badges row (only visible when stats are set)
        self._badges_container = QFrame()
        self._badges_container.setObjectName("OfferCardBadges")
        self._badges_container.setLayout(self.badges_row)
        self._badges_container.setVisible(False)
        layout.addWidget(self._badges_container)


    # (Blank line for readability)
    def set_candidature_stats(self, total: int, by_status: Mapping[str, int] | None = None) -> None:
        """Affiche des infos de candidatures sur la carte.

        - total: nombre total de candidatures liées à l'offre
        - by_status: mapping {STATUT -> count}. Les statuts avec 0 peuvent être omis.
        """
        self._stats_total = max(int(total or 0), 0)
        self._stats_by_status = {str(k): int(v or 0) for k, v in (by_status or {}).items()}

        # Lazy-create total badge
        if self.lbl_badge_total is None:
            self.lbl_badge_total = QLabel()
            self.lbl_badge_total.setObjectName("OfferCardBadge")
            self.badges_row.addWidget(self.lbl_badge_total)

        self.lbl_badge_total.setText(f"{self._stats_total} candidature(s)")
        self.lbl_badge_total.setVisible(True)

        # Remove old status badges
        for lbl in self._status_badges.values():
            lbl.setParent(None)
            lbl.deleteLater()
        self._status_badges.clear()

        # Add per-status badges (only > 0)
        # We keep ordering stable, common statuses first.
        preferred_order = ["A_PREPARER", "ENVOYEE", "ENTRETIEN", "REFUSEE", "RELANCE", "ACCEPTEE"]
        items = list(self._stats_by_status.items())
        items.sort(key=lambda kv: (preferred_order.index(kv[0]) if kv[0] in preferred_order else 999, kv[0]))

        for status, count in items:
            if count <= 0:
                continue
            lbl = QLabel(f"{status.replace('_', ' ').title()}: {count}")
            lbl.setObjectName("OfferCardStat")
            # Allow QSS to color by status
            lbl.setProperty("status", status)
            self.badges_row.addWidget(lbl)
            self._status_badges[status] = lbl

        # Spacer to push badges left (ensure we don't accumulate stretches)
        # Clear any existing stretches by removing trailing items that are spacers.
        while self.badges_row.count() > 0:
            item = self.badges_row.itemAt(self.badges_row.count() - 1)
            if item is not None and item.spacerItem() is not None:
                self.badges_row.takeAt(self.badges_row.count() - 1)
            else:
                break
        self.badges_row.addStretch(1)

        self._badges_container.setVisible(True)
        self._badges_container.style().unpolish(self._badges_container)
        self._badges_container.style().polish(self._badges_container)

    def mousePressEvent(self, event):
        # Si on clique sur le bouton d'édition, ne pas ouvrir la carte.
        try:
            pos = event.position().toPoint()  # Qt6
        except Exception:
            pos = event.pos()  # fallback

        w = self.childAt(pos)
        if w is not None and w.objectName() == "OfferCardEditButton":
            event.accept()
            return

        if callable(self._on_open):
            self._on_open(self.offer)
        super().mousePressEvent(event)

    def set_status(self, status: str):
        """Convenience setter (optional). Prefer setProperty('status', ...) directly."""
        self.setProperty("status", status)
        self.style().unpolish(self)
        self.style().polish(self)
