from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QFormLayout,
    QMessageBox,
    QFrame,
    QSizePolicy,
)

from models import Offre
from services.url_import_service import (
    UrlImportError,
    import_offer_from_url,
    import_offer_from_url_browser,
)


class OfferFormPage(QWidget):
    """Page d'ajout / édition d'une offre.

    Objectif:
    - Remplacer l'ancien OfferFormDialog par une page dans un QStackedWidget.
    - Permettre: saisie manuelle, pré-remplissage via URL (requests ou navigateur/Playwright), sauvegarde en DB.

    Cette page est volontairement "auto-suffisante" et récupère la session SQLAlchemy en remontant la hiérarchie
    des parents (ApplicationView -> MainWindow), en cherchant un attribut `.session`.
    """

    saved = Signal(object)  # Offre
    cancelled = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_offer: Optional[Offre] = None

        self._create_widgets()
        self._create_layouts()
        self._connect_signals()

        self.reset_form()

    # ---------------------------------------------------------------------
    # Public API (appelée par ApplicationView)
    # ---------------------------------------------------------------------

    def reset_form(self) -> None:
        self.current_offer = None

        self.input_url.setText("")
        self.input_title.setText("")
        self.input_company.setText("")
        self.input_location.setText("")
        self.input_contract.setText("")
        self.text_description.setPlainText("")

        self._set_info_message("", kind="")
        self._set_mode_title(is_edit=False)

        self._last_dump_path = None
        self.btn_open_dump.setVisible(False)

        self.btn_save.setText("Créer l'offre")
        # UX: re-enable prefill buttons
        self.btn_prefill.setEnabled(True)
        self.btn_prefill_browser.setEnabled(True)
        # UX: auto-focus the title field
        self.input_title.setFocus()

    def load_offer(self, offre: Offre) -> None:
        self.current_offer = offre
        self.btn_prefill.setEnabled(False)
        self.btn_prefill_browser.setEnabled(False)

        self.input_url.setText(getattr(offre, "url", "") or "")
        self.input_title.setText(getattr(offre, "titre_poste", "") or "")
        self.input_company.setText(getattr(offre, "entreprise", "") or "")
        self.input_location.setText(getattr(offre, "localisation", "") or "")
        self.input_contract.setText(getattr(offre, "type_contrat", "") or "")
        self.text_description.setPlainText(getattr(offre, "texte_annonce", "") or "")

        self._set_info_message("", kind="")
        self._set_mode_title(is_edit=True)
        self.btn_save.setText("Enregistrer")

    def set_prefill_data(self, data: Dict[str, Any]) -> None:
        """Utilisé par MainWindow / ou directement par cette page après import URL."""
        # Ne force pas l'URL si l'utilisateur a déjà saisi une autre URL
        if not self.input_url.text().strip() and data.get("url"):
            self.input_url.setText(str(data.get("url")))

        if data.get("titre_poste"):
            self.input_title.setText(str(data.get("titre_poste")))
        if data.get("entreprise"):
            self.input_company.setText(str(data.get("entreprise")))
        if data.get("localisation"):
            self.input_location.setText(str(data.get("localisation")))
        if data.get("type_contrat"):
            self.input_contract.setText(str(data.get("type_contrat")))
        if data.get("texte_annonce"):
            self.text_description.setPlainText(str(data.get("texte_annonce")))
        dump_path = data.get("_dump_path")
        self._last_dump_path = str(dump_path) if dump_path else None
        self.btn_open_dump.setVisible(bool(self._last_dump_path))

        if self._last_dump_path:
            self._set_info_message("Import OK. Un dump de diagnostic est disponible.", kind="success")
        else:
            self._set_info_message("Import OK.", kind="success")

    def set_import_error(self, message: str) -> None:
        self._set_info_message(message, kind="error")
        dump_path = self._extract_dump_path_from_error(message)
        self._last_dump_path = dump_path
        self.btn_open_dump.setVisible(bool(dump_path))

    # ---------------------------------------------------------------------
    # UI construction
    # ---------------------------------------------------------------------

    def _create_widgets(self) -> None:
        # Header
        self.title_label = QLabel("Ajouter une offre")
        self.title_label.setObjectName("pageTitle")

        self.subtitle_label = QLabel(
            "Renseigne les champs manuellement ou pré-remplis depuis une URL (Jobup / etc.)."
        )
        self.subtitle_label.setObjectName("pageSubtitle")
        self.subtitle_label.setWordWrap(True)

        # Info / error message
        self.info_label = QLabel("")
        self.info_label.setObjectName("formInfo")
        self.info_label.setWordWrap(True)
        self.info_label.setVisible(False)

        self.btn_open_dump = QPushButton("Ouvrir le dump")
        self.btn_open_dump.setObjectName("secondaryButton")
        self.btn_open_dump.setVisible(False)
        self._last_dump_path: Optional[str] = None

        # Form fields
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText("https://...")
        self.input_url.setClearButtonEnabled(True)

        self.input_title = QLineEdit()
        self.input_title.setPlaceholderText("Intitulé du poste")

        self.input_company = QLineEdit()
        self.input_company.setPlaceholderText("Entreprise")

        self.input_location = QLineEdit()
        self.input_location.setPlaceholderText("Localisation")

        self.input_contract = QLineEdit()
        self.input_contract.setPlaceholderText("Type de contrat")

        self.text_description = QTextEdit()
        self.text_description.setPlaceholderText("Description / texte de l'annonce")
        self.text_description.setAcceptRichText(False)

        # Buttons
        self.btn_back = QPushButton("Retour")
        self.btn_back.setObjectName("secondaryButton")

        self.btn_prefill = QPushButton("Pré-remplir")
        self.btn_prefill.setObjectName("secondaryButton")

        self.btn_prefill_browser = QPushButton("Pré-remplir (navigateur)")
        self.btn_prefill_browser.setObjectName("secondaryButton")

        self.btn_open_url = QPushButton("Ouvrir l'URL")
        self.btn_open_url.setObjectName("secondaryButton")

        self.btn_save = QPushButton("Créer l'offre")
        self.btn_save.setObjectName("primaryButton")

        # Divider
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setFrameShadow(QFrame.Sunken)
        self.divider.setObjectName("divider")

    def _create_layouts(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # Header layout
        header = QVBoxLayout()
        header.setSpacing(6)
        header.addWidget(self.title_label)
        header.addWidget(self.subtitle_label)
        root.addLayout(header)

        root.addWidget(self.info_label)
        root.addWidget(self.btn_open_dump)
        root.addWidget(self.divider)

        # URL row + actions
        url_row = QHBoxLayout()
        url_row.setSpacing(10)
        url_row.addWidget(QLabel("URL"))
        url_row.addWidget(self.input_url, 1)
        url_row.addWidget(self.btn_open_url)
        url_row.addWidget(self.btn_prefill)
        url_row.addWidget(self.btn_prefill_browser)
        root.addLayout(url_row)

        # Form
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        form.addRow("Titre du poste", self.input_title)
        form.addRow("Entreprise", self.input_company)
        form.addRow("Localisation", self.input_location)
        form.addRow("Type de contrat", self.input_contract)
        form.addRow("Description", self.text_description)

        root.addLayout(form, 1)

        # Footer
        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.addWidget(self.btn_back)
        footer.addStretch(1)
        footer.addWidget(self.btn_save)
        root.addLayout(footer)

        # Expand description
        self.text_description.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _connect_signals(self) -> None:
        self.btn_back.clicked.connect(self._on_back)
        self.btn_open_url.clicked.connect(self._on_open_url)
        self.btn_prefill.clicked.connect(self._on_prefill_requests)
        self.btn_prefill_browser.clicked.connect(self._on_prefill_browser)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_open_dump.clicked.connect(self._on_open_dump)

    # ---------------------------------------------------------------------
    # Actions
    # ---------------------------------------------------------------------

    def _set_busy(self, busy: bool, label: str = "") -> None:
        # Disable actions during import / save to avoid double clicks.
        self.btn_prefill.setEnabled(not busy and self.btn_prefill.isEnabled())
        self.btn_prefill_browser.setEnabled(not busy and self.btn_prefill_browser.isEnabled())
        self.btn_open_url.setEnabled(not busy)
        self.btn_save.setEnabled(not busy)
        if label:
            self._set_info_message(label, kind="info")

    def _on_open_dump(self) -> None:
        if not self._last_dump_path:
            self._set_info_message("Aucun dump disponible.", kind="error")
            return
        qurl = QUrl.fromLocalFile(self._last_dump_path)
        QDesktopServices.openUrl(qurl)

    def _on_back(self) -> None:
        """Return to offers list via ApplicationView."""
        parent = self.parent()
        show_offers = getattr(parent, "show_offers", None)
        if callable(show_offers):
            show_offers()
        else:
            # Fallback to page index
            set_page = getattr(parent, "set_page", None)
            page_offers = getattr(parent, "PAGE_OFFERS", None)
            if callable(set_page):
                set_page(page_offers if isinstance(page_offers, int) else 1)

        self.cancelled.emit()

    def _on_open_url(self) -> None:
        url = self.input_url.text().strip()
        if not url:
            self._set_info_message("Aucune URL à ouvrir.", kind="error")
            return

        # Ensure a scheme so QUrl is valid.
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
            self.input_url.setText(url)

        QDesktopServices.openUrl(QUrl(url))

    def _on_prefill_requests(self) -> None:
        url = self.input_url.text().strip()
        if not url:
            self._set_info_message("Renseigne une URL avant de pré-remplir.", kind="error")
            return

        self._set_busy(True, "Import en cours...")
        try:
            data = import_offer_from_url(url)
        except UrlImportError as e:
            msg = str(e)
            self.set_import_error(msg)
            self._maybe_offer_dump_open(msg)
            self._set_busy(False)
            return
        except Exception as e:
            self.set_import_error(f"Erreur inattendue : {e}")
            self._set_busy(False)
            return

        self.set_prefill_data(data)
        self._set_busy(False)

    def _on_prefill_browser(self) -> None:
        url = self.input_url.text().strip()
        if not url:
            self._set_info_message("Renseigne une URL avant de pré-remplir.", kind="error")
            return

        self._set_busy(True, "Import navigateur en cours...")
        try:
            data = import_offer_from_url_browser(url)
        except UrlImportError as e:
            msg = str(e)
            self.set_import_error(msg)
            self._maybe_offer_dump_open(msg)
            self._set_busy(False)
            return
        except Exception as e:
            self.set_import_error(f"Erreur inattendue : {e}")
            self._set_busy(False)
            return

        self.set_prefill_data(data)
        self._set_busy(False)

    def _on_save(self) -> None:
        self.btn_save.setEnabled(False)
        title = self.input_title.text().strip()
        if not title:
            self._set_info_message("Le titre du poste est obligatoire.", kind="error")
            self.btn_save.setEnabled(True)
            return

        session = self._get_session()
        if session is None:
            self._set_info_message("Session DB introuvable (ApplicationView/MainWindow).", kind="error")
            self.btn_save.setEnabled(True)
            return

        url = self.input_url.text().strip()
        company = self.input_company.text().strip()
        location = self.input_location.text().strip()
        contract = self.input_contract.text().strip()
        description = self.text_description.toPlainText().strip()

        try:
            if self.current_offer is None:
                offre = Offre(
                    titre_poste=title,
                    entreprise=company,
                    localisation=location,
                    type_contrat=contract,
                    url=url,
                    texte_annonce=description,
                )
                session.add(offre)
                session.commit()
                session.refresh(offre)
                self.current_offer = offre
                self._set_info_message("Offre créée.", kind="success")
                self.saved.emit(offre)
                # Reset for potential next creation
                self.reset_form()
            else:
                offre = self.current_offer
                # Update only if attributes exist
                if hasattr(offre, "titre_poste"):
                    offre.titre_poste = title
                if hasattr(offre, "entreprise"):
                    offre.entreprise = company
                if hasattr(offre, "localisation"):
                    offre.localisation = location
                if hasattr(offre, "type_contrat"):
                    offre.type_contrat = contract
                if hasattr(offre, "url"):
                    offre.url = url
                if hasattr(offre, "texte_annonce"):
                    offre.texte_annonce = description

                session.commit()
                self._set_info_message("Modifications enregistrées.", kind="success")
                self.saved.emit(offre)
        except Exception as e:
            session.rollback()
            self._set_info_message(f"Erreur lors de l'enregistrement : {e}", kind="error")
        self.btn_save.setEnabled(True)

    # ---------------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------------

    def _set_mode_title(self, *, is_edit: bool) -> None:
        self.title_label.setText("Modifier l'offre" if is_edit else "Ajouter une offre")

    def _set_info_message(self, text: str, *, kind: str) -> None:
        self.info_label.setText(text)
        self.info_label.setVisible(bool(text))

        # Utilise une propriété QSS pour styliser (info/success/error)
        if kind:
            self.info_label.setProperty("kind", kind)
        else:
            self.info_label.setProperty("kind", "")

        # Force un repolish pour appliquer le QSS dynamiquement
        self.info_label.style().unpolish(self.info_label)
        self.info_label.style().polish(self.info_label)

    def _maybe_offer_dump_open(self, error_message: str) -> None:
        dump_path = self._extract_dump_path_from_error(error_message)
        if not dump_path:
            return

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Import URL")
        box.setText("Impossible de pré-remplir automatiquement cette annonce.")
        box.setInformativeText("Tu peux ouvrir le fichier de diagnostic pour analyser ce qui a été récupéré.")
        btn_open = box.addButton("Ouvrir le dump", QMessageBox.AcceptRole)
        box.addButton("OK", QMessageBox.RejectRole)
        box.exec()

        if box.clickedButton() == btn_open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(dump_path))

    def _extract_dump_path_from_error(self, msg: str) -> Optional[str]:
        # Le service écrit généralement "Dump: /path/to/file.txt"
        marker = "Dump:"
        if marker not in msg:
            return None
        path = msg.split(marker, 1)[1].strip()
        return path if path else None

    def _get_session(self):
        # Remonte les parents pour trouver un attribut `.session`
        w: Optional[object] = self
        for _ in range(8):
            if w is None:
                break
            if hasattr(w, "session"):
                return getattr(w, "session")
            w = w.parent()  # type: ignore[assignment]
        return None


class QObjectLike:
    # Petite aide typée pour `.parent()`
    def parent(self):
        raise NotImplementedError
