from dataclasses import dataclass
from collections.abc import Iterable

from PySide6.QtCore import Qt, Signal, QSignalBlocker, QUrl
from PySide6.QtGui import QDesktopServices
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
    QTabWidget,
    QFormLayout,
    QGroupBox,
    QComboBox,
)

# Letters service helpers
from services.letters_service import ensure_user_templates_dir, list_user_templates


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

    def __init__(self, vm: LetterViewModel, parent: QWidget | None = None):
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
        # Full card clickable = open, but don't hijack clicks on action buttons.
        child = self.childAt(event.pos())
        if isinstance(child, QPushButton):
            return super().mousePressEvent(event)

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
    - editOfferRequested(offer_id)
    """

    backRequested = Signal()
    openLetterRequested = Signal(int)
    markSentRequested = Signal(int)
    deleteRequested = Signal(int)
    deleteOfferRequested = Signal(int)
    editOfferRequested = Signal(int)
    saveDraftRequested = Signal(dict)   # payload: paragraph fields
    generateLetterRequested = Signal()
    # Nouveau (non-breaking): contient le nom du template sélectionné (ou "" pour défaut profil/app)
    generateLetterRequestedWithTemplate = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("OfferDetailPage")

        self.current_offer: object | None = None

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

        self.btn_edit_offer = QPushButton("Modifier l’annonce")
        self.btn_edit_offer.setObjectName("SecondaryButton")
        self.btn_edit_offer.setToolTip("Modifier cette annonce")
        self.btn_edit_offer.clicked.connect(self._on_edit_offer_clicked)
        header.addWidget(self.btn_edit_offer)

        self.btn_delete_offer = QPushButton("Supprimer l’annonce")
        self.btn_delete_offer.setObjectName("DangerButton")
        self.btn_delete_offer.setToolTip("Supprimer cette annonce et ses candidatures associées")
        self.btn_delete_offer.clicked.connect(self._on_delete_offer_clicked)
        header.addWidget(self.btn_delete_offer)

        self.btn_edit_offer.setEnabled(False)

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

        # Tabs (Annonce / Lettre / Lettres)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("OfferDetailTabs")
        root.addWidget(self.tabs, 1)

        # --- Tab: Annonce ---
        tab_offer = QWidget()
        tab_offer_layout = QVBoxLayout(tab_offer)
        tab_offer_layout.setContentsMargins(0, 0, 0, 0)
        tab_offer_layout.setSpacing(10)

        offer_box = QGroupBox("Annonce")
        offer_box.setObjectName("OfferBox")
        offer_box_layout = QVBoxLayout(offer_box)
        offer_box_layout.setContentsMargins(12, 12, 12, 12)
        offer_box_layout.setSpacing(10)

        self.txt_offer = QTextEdit()
        self.txt_offer.setReadOnly(True)
        self.txt_offer.setAcceptRichText(False)
        self.txt_offer.setObjectName("OfferDetailText")
        offer_box_layout.addWidget(self.txt_offer)

        tab_offer_layout.addWidget(offer_box)
        tab_offer_layout.addStretch(1)

        self.tabs.addTab(tab_offer, "Annonce")

        # --- Tab: Lettre (éditeur) ---
        tab_editor = QWidget()
        tab_editor_layout = QVBoxLayout(tab_editor)
        tab_editor_layout.setContentsMargins(0, 0, 0, 0)
        tab_editor_layout.setSpacing(10)

        editor_box = QGroupBox("Édition de la lettre")
        editor_box.setObjectName("LetterEditorBox")
        editor_layout = QVBoxLayout(editor_box)
        editor_layout.setContentsMargins(12, 12, 12, 12)
        editor_layout.setSpacing(10)

        # Draft status (UX)
        self.lbl_draft_status = QLabel("Brouillon")
        self.lbl_draft_status.setObjectName("DraftStatus")
        self.lbl_draft_status.setProperty("dirty", False)
        self.lbl_draft_status.style().unpolish(self.lbl_draft_status)
        self.lbl_draft_status.style().polish(self.lbl_draft_status)
        editor_layout.addWidget(self.lbl_draft_status)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignTop)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        def _mk_field(placeholder: str, min_h: int = 80):
            txt = QTextEdit()
            txt.setAcceptRichText(False)
            txt.setMinimumHeight(min_h)
            txt.setPlaceholderText(placeholder)
            txt.setTabChangesFocus(True)
            txt.textChanged.connect(self._mark_draft_dirty)
            return txt

        self.ed_intro = _mk_field("Présente-toi en 2–3 phrases et annonce ton intérêt pour l’entreprise.")
        self.ed_exp1 = _mk_field("Expérience 1 : projet / techno / impact métier / résultats mesurables.")
        self.ed_exp2 = _mk_field("Expérience 2 : autonomie, delivery, qualité, CI/CD, performance, etc.")
        self.ed_poste = _mk_field("Explique pourquoi ce poste te correspond (stack, contexte) et comment tu vas apporter de la valeur.")
        self.ed_personnalite = _mk_field("Soft skills : rigueur, sens business, communication, autonomie, esprit d'équipe…")
        self.ed_conclusion = _mk_field("Conclusion courte : motivation + disponibilité + proposition d'échange.", min_h=70)

        form.addRow("Introduction", self.ed_intro)
        form.addRow("Expérience / adéquation 1", self.ed_exp1)
        form.addRow("Expérience / adéquation 2", self.ed_exp2)
        form.addRow("Lien avec le poste", self.ed_poste)
        form.addRow("Personnalité / soft skills", self.ed_personnalite)
        form.addRow("Conclusion", self.ed_conclusion)

        editor_layout.addLayout(form)

        # Template selector (optionnel)
        tpl_row = QHBoxLayout()
        tpl_row.setSpacing(10)

        lbl_tpl = QLabel("Template :")
        lbl_tpl.setObjectName("FormLabel")
        tpl_row.addWidget(lbl_tpl)

        self.combo_template = QComboBox()
        self.combo_template.setObjectName("TemplateCombo")
        self.combo_template.setMinimumWidth(260)
        tpl_row.addWidget(self.combo_template, 1)

        self.btn_tpl_refresh = QPushButton("Rafraîchir")
        self.btn_tpl_refresh.setObjectName("SecondaryButton")
        self.btn_tpl_refresh.clicked.connect(self.refresh_templates)
        tpl_row.addWidget(self.btn_tpl_refresh)

        self.btn_tpl_open_dir = QPushButton("Dossier")
        self.btn_tpl_open_dir.setObjectName("SecondaryButton")
        self.btn_tpl_open_dir.clicked.connect(self._open_templates_dir)
        tpl_row.addWidget(self.btn_tpl_open_dir)

        editor_layout.addLayout(tpl_row)

        # Actions bar
        actions = QHBoxLayout()
        actions.addStretch(1)

        self.btn_save_draft = QPushButton("Enregistrer")
        self.btn_save_draft.setObjectName("PrimaryButton")
        self.btn_save_draft.setToolTip("Enregistre le brouillon en base")
        self.btn_save_draft.clicked.connect(self._emit_save_draft)
        actions.addWidget(self.btn_save_draft)

        self.btn_generate = QPushButton("Générer HTML")
        self.btn_generate.setObjectName("SecondaryButton")
        self.btn_generate.setToolTip("Génère la lettre HTML à partir du brouillon")
        self.btn_generate.clicked.connect(self._on_generate_clicked)
        actions.addWidget(self.btn_generate)

        editor_layout.addLayout(actions)

        tab_editor_layout.addWidget(editor_box)
        tab_editor_layout.addStretch(1)

        self.tabs.addTab(tab_editor, "Lettre")

        # --- Tab: Lettres / candidatures ---
        tab_letters = QWidget()
        tab_letters_layout = QVBoxLayout(tab_letters)
        tab_letters_layout.setContentsMargins(0, 0, 0, 0)
        tab_letters_layout.setSpacing(10)

        letters_box = QGroupBox("Lettres / candidatures")
        letters_box.setObjectName("LettersBox")
        letters_box_layout = QVBoxLayout(letters_box)
        letters_box_layout.setContentsMargins(12, 12, 12, 12)
        letters_box_layout.setSpacing(10)

        self.letters_scroll = QScrollArea()
        self.letters_scroll.setWidgetResizable(True)
        self.letters_scroll.setFrameShape(QScrollArea.NoFrame)
        self.letters_scroll.setObjectName("LettersScroll")

        self.letters_container = QWidget()
        self.letters_layout = QVBoxLayout(self.letters_container)
        self.letters_layout.setContentsMargins(0, 0, 0, 0)
        self.letters_layout.setSpacing(10)

        self.letters_scroll.setWidget(self.letters_container)
        letters_box_layout.addWidget(self.letters_scroll)

        tab_letters_layout.addWidget(letters_box)
        tab_letters_layout.addStretch(1)

        self.tabs.addTab(tab_letters, "Candidatures")

        # Default tab
        self.tabs.setCurrentIndex(1)

        # Init template list
        self.refresh_templates()

    # ---------------------------
    # Public API
    # ---------------------------

    def set_offer(self, offer: object) -> None:
        """Affiche une offre (sans DB)."""
        self.current_offer = offer
        offer_id = getattr(offer, "id", None)
        if hasattr(self, "btn_edit_offer"):
            self.btn_edit_offer.setEnabled(offer_id is not None)

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

    def set_letter_content(self, lettre: object | None) -> None:
        """Pré-remplit l’éditeur avec le contenu d’une LettreMotivation."""
        def _val(obj, name):
            return getattr(obj, name, "") if obj is not None else ""

        # Prevent textChanged() from flagging the draft as dirty during programmatic fill.
        blockers = [
            QSignalBlocker(self.ed_intro),
            QSignalBlocker(self.ed_exp1),
            QSignalBlocker(self.ed_exp2),
            QSignalBlocker(self.ed_poste),
            QSignalBlocker(self.ed_personnalite),
            QSignalBlocker(self.ed_conclusion),
        ]
        _ = blockers  # keep references alive until the end of the method

        self.ed_intro.setPlainText(_val(lettre, "paragraphe_intro"))
        self.ed_exp1.setPlainText(_val(lettre, "paragraphe_exp1"))
        self.ed_exp2.setPlainText(_val(lettre, "paragraphe_exp2"))
        self.ed_poste.setPlainText(_val(lettre, "paragraphe_poste"))
        self.ed_personnalite.setPlainText(_val(lettre, "paragraphe_personnalite"))
        self.ed_conclusion.setPlainText(_val(lettre, "paragraphe_conclusion"))

        self._set_draft_status("Brouillon", dirty=False)

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


    def _on_edit_offer_clicked(self) -> None:
        # UI only: on délègue l’édition réelle au contrôleur (ApplicationView/MainWindow)
        offer_id = getattr(self.current_offer, "id", None)
        if offer_id is None:
            return
        self.editOfferRequested.emit(int(offer_id))

    def _on_delete_offer_clicked(self) -> None:
        # UI only: on délègue la suppression réelle au contrôleur (MainWindow)
        offer_id = getattr(self.current_offer, "id", None)
        if offer_id is None:
            return
        self.deleteOfferRequested.emit(int(offer_id))

    # ---------------------------
    # Internals
    # ---------------------------

    def _set_draft_status(self, text: str, dirty: bool) -> None:
        if not hasattr(self, "lbl_draft_status"):
            return
        self.lbl_draft_status.setText(text)
        self.lbl_draft_status.setProperty("dirty", bool(dirty))
        self.lbl_draft_status.style().unpolish(self.lbl_draft_status)
        self.lbl_draft_status.style().polish(self.lbl_draft_status)

    def _mark_draft_dirty(self) -> None:
        self._set_draft_status("Brouillon (modifié)", dirty=True)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        """Supprime proprement tous les items d'un layout (widgets, spacers, sous-layouts)."""
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue

            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
                continue

            child_layout = item.layout()
            if child_layout is not None:
                # Récursif
                while child_layout.count():
                    sub = child_layout.takeAt(0)
                    if sub is None:
                        continue
                    sw = sub.widget()
                    if sw is not None:
                        sw.setParent(None)
                        sw.deleteLater()
                    elif sub.layout() is not None:
                        # nettoyage récursif simple
                        try:
                            self._clear_layout(sub.layout())  # type: ignore
                        except Exception:
                            pass
                child_layout.setParent(None)
                continue

            # spacer item: rien à faire
            _ = item


    def _emit_save_draft(self) -> None:
        payload = {
            "paragraphe_intro": self.ed_intro.toPlainText().strip(),
            "paragraphe_exp1": self.ed_exp1.toPlainText().strip(),
            "paragraphe_exp2": self.ed_exp2.toPlainText().strip(),
            "paragraphe_poste": self.ed_poste.toPlainText().strip(),
            "paragraphe_personnalite": self.ed_personnalite.toPlainText().strip(),
            "paragraphe_conclusion": self.ed_conclusion.toPlainText().strip(),
        }
        self.saveDraftRequested.emit(payload)
        self._set_draft_status("Brouillon (enregistré)", dirty=False)


    # ---------------------------
    # Templates
    # ---------------------------

    def refresh_templates(self) -> None:
        """Recharge les templates utilisateur (data/templates) dans le combo."""
        if not hasattr(self, "combo_template"):
            return

        current = self.combo_template.currentText().strip()
        self.combo_template.blockSignals(True)
        self.combo_template.clear()
        # "" = laisse le service choisir (profil/app)
        self.combo_template.addItem("(Défaut — profil/app)")

        try:
            ensure_user_templates_dir()
            tpl_paths = list_user_templates()
            for p in tpl_paths:
                self.combo_template.addItem(p.name)
        except Exception:
            # Pas bloquant
            pass

        # Restore selection
        if current and current != "(Défaut — profil/app)":
            idx = self.combo_template.findText(current)
            if idx >= 0:
                self.combo_template.setCurrentIndex(idx)

        self.combo_template.blockSignals(False)

    def _selected_template_name(self) -> str:
        if not hasattr(self, "combo_template"):
            return ""
        name = self.combo_template.currentText().strip()
        if not name or name == "(Défaut — profil/app)":
            return ""
        return name

    def _open_templates_dir(self) -> None:
        try:
            d = ensure_user_templates_dir()
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))
        except Exception:
            return

    def _on_generate_clicked(self) -> None:
        """Émet la demande de génération en incluant le template choisi."""
        tpl = self._selected_template_name()
        # Non-breaking: on garde l'ancien signal (listeners existants)
        self.generateLetterRequested.emit()
        # Nouveau signal avec info template
        self.generateLetterRequestedWithTemplate.emit(tpl)
