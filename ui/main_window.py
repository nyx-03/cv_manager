# ui/main_window.py

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
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
    get_offer_stats,
    get_candidature,
    create_candidature,
    mark_sent,
    delete_candidature,
    validate_letter_path,
    CandidatureCreateData,
)
from services.profile_service import ensure_profile
from services.letters_service import generate_letter_html, get_default_letter_template_path

from models import Offre, Candidature, CandidatureStatut, LettreMotivation, LettreStatut


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("CV Manager - Candidatures")
        self.showMaximized()

        self.session = SessionLocal()
        self.current_offer: Offre | None = None

        self._setup_ui()
        self._setup_actions()
        self._load_offers()

    def _setup_actions(self):
        # Menu "Offre" (simple, fonctionne même si la sidebar évolue)
        offer_menu = self.menuBar().addMenu("Offre")

        self.action_delete_offer = QAction("Supprimer l'annonce…", self)
        self.action_delete_offer.setShortcut("Del")
        self.action_delete_offer.triggered.connect(self.on_delete_offer)
        offer_menu.addAction(self.action_delete_offer)

    def _setup_ui(self):
        self.view = ApplicationView(self.session, parent=self)
        self.setCentralWidget(self.view)
        self._wire_offer_detail_editor()

        # Provide status resolver for offer cards (colors)
        self.view.set_offers_status_resolver(self._resolve_offer_status)

        # Provide candidature stats resolver for offer cards (total + per-status badges)
        if hasattr(self.view, "set_offers_candidature_stats_resolver"):
            self.view.set_offers_candidature_stats_resolver(
                lambda offer: get_offer_stats(self.session, offer.id)
            )

        # Wire view -> controller
        self.view.offerClicked.connect(self.open_offer_detail)
        self.view.backToOffersRequested.connect(lambda: self.view.set_page(PAGE_OFFERS))
        self.view.openLetterRequested.connect(self.on_open_letter_by_id)
        self.view.markSentRequested.connect(self.on_mark_sent_by_id)
        self.view.deleteRequested.connect(self.on_delete_candidature_by_id)
        self.view.deleteOfferRequested.connect(self.on_delete_offer_by_id)

        self.view.newOfferRequested.connect(self.on_new_offer)
        self.view.prepareLetterRequested.connect(self.on_prepare_letter)
        self.view.showCandidaturesRequested.connect(self.on_show_candidatures)
        self.view.refreshRequested.connect(self._refresh_current_page)

    def _get_offer_detail_page_widget(self):
        """Retourne le widget OfferDetailPage si accessible via ApplicationView (best-effort)."""
        # Common attribute name
        if hasattr(self.view, "offer_detail_page"):
            return getattr(self.view, "offer_detail_page")
        # Common accessor
        if hasattr(self.view, "get_offer_detail_page"):
            try:
                return self.view.get_offer_detail_page()
            except Exception:
                return None
        # Generic lookup in stacked widget
        if hasattr(self.view, "stack"):
            try:
                w = self.view.stack.widget(PAGE_OFFER_DETAIL)
                return w
            except Exception:
                return None
        return None

    def _wire_offer_detail_editor(self):
        """Connecte les signaux de l'éditeur de lettre (OfferDetailPage) au contrôleur."""
        if getattr(self, "_offer_detail_editor_wired", False):
            return
        page = self._get_offer_detail_page_widget()
        if not page:
            return

        # Connexions best-effort (le widget peut ne pas avoir encore ces signaux selon la version)
        if hasattr(page, "saveDraftRequested"):
            page.saveDraftRequested.connect(self.on_save_letter_draft)  # type: ignore
        if hasattr(page, "generateLetterRequested"):
            page.generateLetterRequested.connect(self.on_generate_letter_from_editor)  # type: ignore

        self._offer_detail_editor_wired = True

    def _refresh_current_page(self):
        self._wire_offer_detail_editor()
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

        # Pré-remplissage de l'éditeur avec la lettre courante (si l'UI la supporte)
        try:
            lettre = self._get_or_create_current_lettre(offre)
            page = self._get_offer_detail_page_widget()
            if page and hasattr(page, "set_letter_content"):
                page.set_letter_content(lettre)
        except Exception:
            # Ne bloque pas l'ouverture du détail si la lettre n'est pas dispo
            pass

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

    def on_delete_offer_by_id(self, offer_id: int):
        # Sélectionner l'offre courante à partir de l'ID
        offre = self.session.query(Offre).filter_by(id=offer_id).first()
        if not offre:
            QMessageBox.warning(self, "Suppression", "Annonce introuvable.")
            return

        # Réutilise la logique existante basée sur l'offre sélectionnée
        self.current_offer = offre
        self.on_delete_offer()

    def _load_offers(self):
        offers = list_offers(self.session, desc=True)
        self.view.set_offers(offers)


    def on_new_offer(self):
        """Open the add-offer page inside the stacked layout."""
        try:
            self.view.show_add_offer()
        except Exception:
            # Fallback: switch to offers page
            self.view.set_page(PAGE_OFFERS)
    def _get_selected_offer(self) -> Offre | None:
        return self.current_offer

    def _get_letter_template_path(self) -> Path:
        """Retourne le chemin du template HTML utilisé pour générer les lettres.

        On utilise le template par défaut fourni par `letters_service` (templates/lettre_modern.html.j2).
        (On le rendra configurable via Settings ensuite.)
        """
        return get_default_letter_template_path()

    def _get_letters_output_dir(self) -> Path:
        """Dossier de sortie des lettres générées."""
        out_dir = Path.cwd() / "generated_letters"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def _get_or_create_current_lettre(self, offre: Offre) -> LettreMotivation:
        """Retourne la lettre courante (brouillon) pour une offre.

        Stratégie:
        - Si une lettre `is_current=True` existe: on la retourne.
        - Sinon: on crée une v1 en BROUILLON.

        NOTE: les paragraphes peuvent être vides au début; `letters_service` appliquera ses defaults.
        """
        lettre = (
            self.session.query(LettreMotivation)
            .filter_by(offre_id=offre.id, is_current=True)
            .order_by(LettreMotivation.version.desc())
            .first()
        )
        if lettre:
            return lettre

        last_version = (
            self.session.query(LettreMotivation)
            .filter_by(offre_id=offre.id)
            .order_by(LettreMotivation.version.desc())
            .first()
        )
        next_version = (last_version.version + 1) if last_version else 1

        lettre = LettreMotivation(
            offre_id=offre.id,
            version=next_version,
            is_current=True,
            statut=LettreStatut.BROUILLON,
        )
        self.session.add(lettre)
        self.session.commit()
        return lettre

    def on_prepare_letter(self):
        offre = self._get_selected_offer()
        if not offre:
            QMessageBox.warning(self, "Préparation lettre", "Sélectionne d'abord une offre dans la liste.")
            return

        profil = ensure_profile(self.session)

        # Lettre (brouillon) associée à l'offre: source de vérité pour le contenu édité
        try:
            lettre = self._get_or_create_current_lettre(offre)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de préparer le brouillon de lettre : {e}")
            return

        try:
            template_path = self._get_letter_template_path()
            out_dir = self._get_letters_output_dir()
            hint = f"{getattr(offre, 'entreprise', '')}-{getattr(offre, 'titre_poste', getattr(offre, 'titre', ''))}".strip("-")

            result = generate_letter_html(
                template_path=template_path,
                output_dir=out_dir,
                profil=profil,
                offre=offre,
                lettre=lettre,
                filename_hint=hint or "lettre",
            )
            output_path = result.output_path

            # Persiste le résultat sur la lettre
            try:
                lettre.output_path = str(output_path)
                lettre.statut = LettreStatut.GENEREE
                self.session.add(lettre)
                self.session.commit()
            except Exception:
                self.session.rollback()
                # On ne bloque pas l'utilisateur si la lettre a été générée, mais on signale le souci.
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Template introuvable (lettre)", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la génération de la lettre HTML : {e}")
            return

        created = None
        try:
            created = create_candidature(
                self.session,
                CandidatureCreateData(
                    offre_id=offre.id,
                    statut=CandidatureStatut.A_PREPARER,
                    date_envoi=None,
                    notes="",
                    chemin_lettre=str(output_path),
                ),
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de créer la candidature : {e}")
            return

        # Lien candidature -> lettre (si supporté par le modèle)
        try:
            cand_obj = None
            if created is not None:
                cand_obj = created
            else:
                cand_obj = (
                    self.session.query(Candidature)
                    .filter_by(offre_id=offre.id)
                    .order_by(Candidature.id.desc())
                    .first()
                )

            if cand_obj is not None and hasattr(cand_obj, "lettre_id"):
                cand_obj.lettre_id = lettre.id
                self.session.add(cand_obj)
                self.session.commit()
        except Exception:
            self.session.rollback()

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

    def on_delete_offer(self):
        offre = self._get_selected_offer()
        if not offre:
            QMessageBox.warning(self, "Suppression", "Aucune annonce sélectionnée.")
            return

        # Compter les candidatures liées
        cands = list_for_offer(self.session, offre.id, desc=True)
        cand_count = len(cands)

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Supprimer l'annonce")
        msg.setText("Es-tu sûr de vouloir supprimer cette annonce ?")
        msg.setInformativeText(
            f"Cette action supprimera l'annonce et ses {cand_count} candidature(s) associée(s) de la base.\n"
            "Tu peux aussi choisir de supprimer les fichiers de lettres associés."
        )

        btn_db_only = msg.addButton("Supprimer (DB seulement)", QMessageBox.AcceptRole)
        btn_db_and_files = msg.addButton("Supprimer (DB + fichiers)", QMessageBox.DestructiveRole)
        btn_cancel = msg.addButton("Annuler", QMessageBox.RejectRole)

        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_cancel:
            return

        delete_files = (clicked == btn_db_and_files)

        # Optionnel : supprimer les fichiers de lettres avant la suppression DB
        if delete_files:
            for cand in cands:
                if cand.chemin_lettre:
                    try:
                        p = Path(cand.chemin_lettre)
                        if p.exists() and p.is_file():
                            p.unlink()
                    except Exception:
                        # On ne bloque pas la suppression DB pour un fichier
                        pass

        try:
            # Supprime d'abord l'offre ; la relation cascade supprimera les candidatures
            self.session.query(Offre).filter_by(id=offre.id).delete()
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Erreur", f"Impossible de supprimer l'annonce : {e}")
            return

        # UI: revenir à la liste et rafraîchir
        self.current_offer = None
        try:
            self.view.set_page(PAGE_OFFERS)
        except Exception:
            pass
        self._load_offers()
        QMessageBox.information(self, "Suppression", "Annonce supprimée.")
    def _normalize_letter_payload(self, payload: dict) -> dict:
        """Normalise un payload d'éditeur vers les champs du modèle LettreMotivation.

        L'UI peut envoyer soit des clés courtes (intro/exp1/...), soit les champs
        du modèle (paragraphe_intro/paragraphe_exp1/...).
        """
        if not payload:
            return {}

        mapping = {
            "intro": "paragraphe_intro",
            "exp1": "paragraphe_exp1",
            "exp2": "paragraphe_exp2",
            "poste": "paragraphe_poste",
            "personnalite": "paragraphe_personnalite",
            "conclusion": "paragraphe_conclusion",
        }

        out: dict = {}
        for k, v in payload.items():
            key = mapping.get(k, k)
            out[key] = v
        return out

    def on_save_letter_draft(self, payload: dict):
        """Sauvegarde le brouillon de lettre (contenu édité) dans LettreMotivation."""
        offre = self._get_selected_offer()
        if not offre:
            QMessageBox.warning(self, "Brouillon", "Sélectionne d'abord une offre.")
            return

        try:
            lettre = self._get_or_create_current_lettre(offre)
            payload = self._normalize_letter_payload(payload)
            for k, v in payload.items():
                if hasattr(lettre, k):
                    setattr(lettre, k, v)
            # Si l'utilisateur édite, on reste au minimum en BROUILLON
            if hasattr(lettre, "statut") and lettre.statut is None:
                lettre.statut = LettreStatut.BROUILLON

            self.session.add(lettre)
            self.session.commit()

            # Optional: update draft status badge if available
            try:
                page = self._get_offer_detail_page_widget()
                if page and hasattr(page, "_set_draft_status"):
                    page._set_draft_status("Brouillon (enregistré)", False)
            except Exception:
                pass

            # Feedback discret
            try:
                self.statusBar().showMessage("Brouillon de lettre enregistré.", 2500)
            except Exception:
                pass
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer le brouillon : {e}")

    def on_generate_letter_from_editor(self):
        """Génère la lettre depuis l'éditeur: sauvegarde puis appelle la génération."""
        page = self._get_offer_detail_page_widget()
        payload = None
        if page:
            # Récupère les champs directement si présents (évite de dépendre d'un signal payload)
            try:
                payload = {
                    "paragraphe_intro": page.ed_intro.toPlainText().strip() if hasattr(page, "ed_intro") else "",
                    "paragraphe_exp1": page.ed_exp1.toPlainText().strip() if hasattr(page, "ed_exp1") else "",
                    "paragraphe_exp2": page.ed_exp2.toPlainText().strip() if hasattr(page, "ed_exp2") else "",
                    "paragraphe_poste": page.ed_poste.toPlainText().strip() if hasattr(page, "ed_poste") else "",
                    "paragraphe_personnalite": page.ed_personnalite.toPlainText().strip() if hasattr(page, "ed_personnalite") else "",
                    "paragraphe_conclusion": page.ed_conclusion.toPlainText().strip() if hasattr(page, "ed_conclusion") else "",
                }
                payload = self._normalize_letter_payload(payload)
            except Exception:
                payload = None

        if payload:
            self.on_save_letter_draft(payload)

        # Lance ensuite la génération standard
        self.on_prepare_letter()