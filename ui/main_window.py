# ui/main_window.py

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QDialog,
)

from db import SessionLocal

from ui.application_view import (
    ApplicationView,
    PAGE_DASHBOARD,
    PAGE_OFFERS,
    PAGE_STATS,
    PAGE_SETTINGS,
    PAGE_OFFER_DETAIL,
)

from services.offers_service import list_offers, create_offer, OfferCreateData
from services.candidatures_service import (
    list_for_offer,
    get_candidature,
    create_candidature,
    mark_sent,
    delete_candidature,
    validate_letter_path,
    CandidatureCreateData,
)
from services.profile_service import ensure_profile
from services.letters_service import generate_letter_html

from models import Offre, Candidature, CandidatureStatut


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("CV Manager - Candidatures")
        self.showMaximized()

        self.session = SessionLocal()

        self._setup_ui()
        self._load_offers()

    def _setup_ui(self):
        self.view = ApplicationView(self.session, parent=self)
        self.setCentralWidget(self.view)

        # Provide status resolver for offer cards (colors)
        self.view.set_offers_status_resolver(self._resolve_offer_status)

        # Wire view -> controller
        self.view.offerClicked.connect(self.open_offer_detail)
        self.view.backToOffersRequested.connect(lambda: self.view.set_page(PAGE_OFFERS))
        self.view.openLetterRequested.connect(self.on_open_letter_by_id)
        self.view.markSentRequested.connect(self.on_mark_sent_by_id)
        self.view.deleteRequested.connect(self.on_delete_candidature_by_id)

        self.view.newOfferRequested.connect(self.on_new_offer)
        self.view.prepareLetterRequested.connect(self.on_prepare_letter)
        self.view.showCandidaturesRequested.connect(self.on_show_candidatures)
        self.view.refreshRequested.connect(self._refresh_current_page)

    def _refresh_current_page(self):
        idx = self.view.current_page() if hasattr(self, "view") else -1
        if idx == PAGE_DASHBOARD:
            self.view.refresh_dashboard()
        elif idx == PAGE_STATS:
            self.view.refresh_stats()
        elif idx == PAGE_OFFER_DETAIL and self.current_offer:
            self.open_offer_detail(self.current_offer)
        else:
            self._load_offers()

    def _resolve_offer_status(self, offre: Offre) -> str:
        """Retourne un statut pour l'offre (utilisé pour colorer les cartes via QSS).

        Stratégie: dernier statut de candidature lié à l'offre, sinon A_PREPARER.
        """
        last = (
            self.session.query(Candidature)
            .filter_by(offre_id=offre.id)
            .order_by(Candidature.id.desc())
            .first()
        )
        return last.statut.name if last and last.statut else "A_PREPARER"


    def open_offer_detail(self, offre: Offre):
        from ui.pages.offer_detail_page import LetterViewModel

        self.current_offer = offre
        self.view.show_offer_detail(offre)

        candidatures = list_for_offer(self.session, offre.id, desc=True)

        vms: list[LetterViewModel] = []
        for cand in candidatures:
            date_label = cand.date_envoi.strftime("%d/%m/%Y") if cand.date_envoi else "Brouillon"
            statut = cand.statut.name if cand.statut else ""
            vms.append(
                LetterViewModel(
                    id=cand.id,
                    statut=statut,
                    date_label=date_label,
                    notes=str(cand.notes) if cand.notes else "",
                    path=cand.chemin_lettre or "",
                )
            )

        self.view.set_offer_detail_letters(vms)
        self.view.set_page(PAGE_OFFER_DETAIL)

    def on_open_letter_by_id(self, cand_id: int):
        cand = get_candidature(self.session, cand_id)
        if not cand:
            QMessageBox.warning(self, "Ouvrir la lettre", "Candidature introuvable.")
            return

        if not cand.chemin_lettre:
            QMessageBox.warning(self, "Ouvrir la lettre", "Cette candidature n'a pas encore de lettre associée.")
            return

        try:
            path = validate_letter_path(cand.chemin_lettre)
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Erreur", f"Le fichier n'existe pas : {e}")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def on_mark_sent_by_id(self, cand_id: int):
        try:
            mark_sent(self.session, cand_id)
        except ValueError:
            QMessageBox.warning(self, "Marquer comme envoyée", "Candidature introuvable.")
            return

        if self.current_offer:
            self.open_offer_detail(self.current_offer)

    def on_delete_candidature_by_id(self, cand_id: int):
        cand = get_candidature(self.session, cand_id)
        if not cand:
            QMessageBox.warning(self, "Suppression", "Candidature introuvable.")
            return

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Supprimer la candidature")
        msg.setText("Es-tu sûr de vouloir supprimer cette candidature ?")
        msg.setInformativeText(
            "La candidature sera supprimée de la base de données.\n"
            "Tu peux aussi choisir de supprimer le fichier de lettre associé."
        )
        btn_db_only = msg.addButton("Supprimer (DB seulement)", QMessageBox.AcceptRole)
        btn_db_and_file = msg.addButton("Supprimer (DB + fichier)", QMessageBox.DestructiveRole)
        btn_cancel = msg.addButton("Annuler", QMessageBox.RejectRole)

        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_cancel:
            return

        delete_file = (clicked == btn_db_and_file)
        try:
            delete_candidature(self.session, cand_id, delete_file=delete_file)
        except ValueError:
            QMessageBox.warning(self, "Suppression", "Candidature introuvable.")
            return

        if self.current_offer:
            self.open_offer_detail(self.current_offer)

    def _load_offers(self):
        offers = list_offers(self.session, desc=True)
        self.view.set_offers(offers)

    def on_new_offer(self):
        dialog = OfferFormDialog(self)
        result = dialog.exec()

        if result == QDialog.Accepted:
            data = dialog.get_data()

            # Vérifier un minimum
            if not data["titre_poste"]:
                QMessageBox.warning(self, "Erreur", "Le titre du poste est obligatoire.")
                return

            # Sauvegarde via service
            create_offer(
                self.session,
                OfferCreateData(
                    titre_poste=data["titre_poste"],
                    entreprise=data.get("entreprise", ""),
                    source=data.get("source", ""),
                    url=data.get("url", ""),
                    localisation=data.get("localisation", ""),
                    type_contrat=data.get("type_contrat", ""),
                    texte_annonce=data.get("texte_annonce", ""),
                ),
            )

            QMessageBox.information(self, "Succès", "Offre enregistrée.")
            self._load_offers()  # rafraîchir la liste


    def _get_selected_offer(self) -> Offre | None:
        return self.current_offer

    def _get_letter_template_path(self) -> Path:
        """Retourne le chemin du template HTML utilisé pour générer les lettres.

        Pour l'instant, on cherche un fichier `developer Python.html` dans quelques emplacements.
        (On le rendra configurable via Settings ensuite.)
        """
        candidates = [
            Path(__file__).resolve().parent / "templates" / "developer Python.html",
            Path.cwd() / "templates" / "developer Python.html",
            Path.cwd() / "developer Python.html",
        ]
        for p in candidates:
            if p.exists():
                return p
        raise FileNotFoundError("Template introuvable. Chemins testés :\n- " + "\n- ".join(str(p) for p in candidates))

    def _get_letters_output_dir(self) -> Path:
        """Dossier de sortie des lettres générées."""
        out_dir = Path.cwd() / "generated_letters"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def on_prepare_letter(self):
        offre = self._get_selected_offer()
        if not offre:
            QMessageBox.warning(self, "Préparation lettre", "Sélectionne d'abord une offre dans la liste.")
            return

        profil = ensure_profile(self.session)

        try:
            template_path = self._get_letter_template_path()
            out_dir = self._get_letters_output_dir()
            hint = f"{getattr(offre, 'entreprise', '')}-{getattr(offre, 'titre_poste', getattr(offre, 'titre', ''))}".strip("-")

            result = generate_letter_html(
                template_path=template_path,
                output_dir=out_dir,
                profil=profil,
                offre=offre,
                filename_hint=hint or "lettre",
            )
            output_path = result.output_path
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Template introuvable", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la génération de la lettre HTML : {e}")
            return

        create_candidature(
            self.session,
            CandidatureCreateData(
                offre_id=offre.id,
                statut=CandidatureStatut.A_PREPARER,
                date_envoi=None,
                notes="",
                chemin_lettre=str(output_path),
            ),
        )

        QMessageBox.information(
            self,
            "Lettre générée",
            f"Lettre HTML générée avec succès :\n{output_path}\n\n"
            "Tu peux l’ouvrir dans ton navigateur et l’imprimer en PDF si besoin."
        )
        if self.current_offer and self.current_offer.id == offre.id:
            self.open_offer_detail(self.current_offer)


    def on_show_candidatures(self):
        try:
            from ui.candidatures_window import CandidaturesWindow
        except ImportError as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Impossible d'ouvrir la vue des candidatures :\n{e}"
            )
            return

        dialog = CandidaturesWindow(self.session, parent=self)
        dialog.exec()