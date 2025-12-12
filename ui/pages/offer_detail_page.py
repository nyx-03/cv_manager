from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QFrame,
    QTextEdit,
    QSizePolicy,
)


@dataclass(frozen=True)
class LetterViewModel:
    """Données minimales pour afficher une lettre/candidature."""

    id: int
    statut: str = ""
    date_label: str = ""
    notes: str = ""
    path: str = ""  # optionnel (ou URL)


class LetterCard(QFrame):
    """Carte cliquable pour une lettre/candidature (UI only).

    - ObjectName: LetterCard
    - Dynamic property used by QSS: status
    """

    openRequested = Signal(int)
    markSentRequested = Signal(int)
    deleteRequested = Signal(int)

    def __init__(self, vm: LetterViewModel, parent=None):
        super().__init__(parent)
        self.vm = vm

        self.setObjectName("LetterCard")
        self.setProperty("status", (vm.statut or "").upper())
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Title line
        title_parts = [p for p in [vm.date_label, (vm.statut or "").upper()] if p]
        self.lbl_title = QLabel(" — ".join(title_parts) if title_parts else "Lettre")
        self.lbl_title.setObjectName("LetterCardTitle")
        layout.addWidget(self.lbl_title)

        # Notes
        if vm.notes:
            self.lbl_notes = QLabel(vm.notes)
            self.lbl_notes.setWordWrap(True)
            self.lbl_notes.setObjectName("LetterCardNotes")
            layout.addWidget(self.lbl_notes)

        # Actions
        actions = QHBoxLayout()
        actions.addStretch(1)

        self.btn_open = QPushButton("Ouvrir")
        self.btn_open.setObjectName("SecondaryButton")
        self.btn_open.clicked.connect(lambda: self.openRequested.emit(vm.id))
        actions.addWidget(self.btn_open)

        self.btn_sent = QPushButton("Marquer envoyée")
        self.btn_sent.setObjectName("SecondaryButton")
        self.btn_sent.clicked.connect(lambda: self.markSentRequested.emit(vm.id))
        actions.addWidget(self.btn_sent)

        self.btn_delete = QPushButton("Supprimer")
        self.btn_delete.setObjectName("DangerButton")
        self.btn_delete.clicked.connect(lambda: self.deleteRequested.emit(vm.id))
        actions.addWidget(self.btn_delete)

        layout.addLayout(actions)

        # Ensure QSS refresh
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        # Full card clickable = open
        self.openRequested.emit(self.vm.id)
        super().mousePressEvent(event)


class OfferDetailPage(QWidget):
    """Page dédiée au détail d'une annonce + lettres/candidatures associées.

    Cette page est volontairement "UI only": elle n'accède pas à la DB.
    La MainWindow (ou un controller/service) lui fournit:
    - l'offre sélectionnée via set_offer()
    - la liste de candidatures via set_letters(...)

    Signaux:
    - backRequested()
    - openLetterRequested(candidature_id)
    - markSentRequested(candidature_id)
    - deleteRequested(candidature_id)
    - deleteOfferRequested(offer_id)
    """

    backRequested = Signal()
    openLetterRequested = Signal(int)
    markSentRequested = Signal(int)
    deleteRequested = Signal(int)
    deleteOfferRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OfferDetailPage")

        self.current_offer: Optional[object] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # Header
        header = QHBoxLayout()

        self.btn_back = QPushButton("← Retour aux annonces")
        self.btn_back.setObjectName("SecondaryButton")
        self.btn_back.clicked.connect(self.backRequested.emit)
        header.addWidget(self.btn_back)

        header.addStretch(1)

        self.btn_delete_offer = QPushButton("Supprimer l’annonce")
        self.btn_delete_offer.setObjectName("DangerButton")
        self.btn_delete_offer.setToolTip("Supprimer cette annonce et ses candidatures associées")
        self.btn_delete_offer.clicked.connect(self._on_delete_offer_clicked)
        header.addWidget(self.btn_delete_offer)

        root.addLayout(header)

        # Title + meta
        self.lbl_title = QLabel("")
        self.lbl_title.setProperty("heading", True)
        self.lbl_title.setObjectName("OfferDetailTitle")
        root.addWidget(self.lbl_title)

        self.lbl_meta = QLabel("")
        self.lbl_meta.setWordWrap(True)
        self.lbl_meta.setObjectName("OfferDetailMeta")
        root.addWidget(self.lbl_meta)

        # Offer text
        self.txt_offer = QTextEdit()
        self.txt_offer.setReadOnly(True)
        self.txt_offer.setObjectName("OfferDetailText")
        root.addWidget(self.txt_offer)

        # Letters title
        letters_title = QLabel("Lettres / candidatures")
        letters_title.setProperty("heading", True)
        root.addWidget(letters_title)

        # Letters scroll
        self.letters_scroll = QScrollArea()
        self.letters_scroll.setWidgetResizable(True)
        self.letters_scroll.setFrameShape(QScrollArea.NoFrame)

        self.letters_container = QWidget()
        self.letters_layout = QVBoxLayout(self.letters_container)
        self.letters_layout.setContentsMargins(0, 0, 0, 0)
        self.letters_layout.setSpacing(10)

        self.letters_scroll.setWidget(self.letters_container)
        root.addWidget(self.letters_scroll)

    # ---------------------------
    # Public API
    # ---------------------------

    def set_offer(self, offer: object) -> None:
        """Affiche une offre (sans DB)."""
        self.current_offer = offer

        titre = getattr(offer, "titre_poste", None) or getattr(offer, "titre", None) or ""
        ent = getattr(offer, "entreprise", None) or ""
        self.lbl_title.setText(f"{titre} — {ent}".strip(" —"))

        parts = []
        source = getattr(offer, "source", None) or ""
        if source:
            parts.append(f"Source : {source}")
        url = getattr(offer, "url", None) or ""
        if url:
            parts.append(f"URL : {url}")
        loc = getattr(offer, "localisation", None) or getattr(offer, "lieu", None) or ""
        if loc:
            parts.append(f"Localisation : {loc}")
        contrat = getattr(offer, "type_contrat", None) or ""
        if contrat:
            parts.append(f"Contrat : {contrat}")
        self.lbl_meta.setText("\n".join(parts))

        texte = getattr(offer, "texte_annonce", None) or getattr(offer, "description", None) or ""
        self.txt_offer.setPlainText(str(texte) if texte is not None else "")

    def set_letters(self, letters: Iterable[LetterViewModel]) -> None:
        """Rend les cartes de lettres/candidatures."""
        self._clear_layout(self.letters_layout)

        letters = list(letters)
        if not letters:
            empty = QLabel("Aucune lettre/candidature pour cette annonce.")
            empty.setObjectName("EmptyState")
            empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.letters_layout.addWidget(empty)
            self.letters_layout.addStretch(1)
            return

        for vm in letters:
            card = LetterCard(vm, self)
            card.openRequested.connect(self.openLetterRequested.emit)
            card.markSentRequested.connect(self.markSentRequested.emit)
            card.deleteRequested.connect(self.deleteRequested.emit)
            self.letters_layout.addWidget(card)

        self.letters_layout.addStretch(1)

    def _on_delete_offer_clicked(self):
        # UI only: on délègue la suppression réelle au contrôleur (MainWindow)
        offer_id = getattr(self.current_offer, "id", None)
        if offer_id is None:
            return
        self.deleteOfferRequested.emit(int(offer_id))

    # ---------------------------
    # Internals
    # ---------------------------

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
