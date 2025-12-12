 # ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QListWidget, QTextEdit,
    QSplitter, QToolBar, QMessageBox, QDialog, QLabel, QPushButton, QHBoxLayout, QListWidgetItem, QFrame,
    QSizePolicy, QScrollArea
)
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtCore import Qt, QUrl, QSize
from ui.pages.offer_detail_page import OfferDetailPage, LetterViewModel
from db import SessionLocal

from services.templates_service import render_lettre_candidature_html
from ui.offer_form_dialog import OfferFormDialog
from ui.dashboard_widget import DashboardWidget
from ui.stats_widget import StatsWidget
from ui.settings_widget import SettingsWidget
from ui.pages.offers_page import OffersPage
from models import Offre, ProfilCandidat, Candidature, CandidatureStatut
from pathlib import Path
from datetime import date

# --- Service layer for offers ---
from services.offers_service import (
    list_offers,
    create_offer,
    get_offer,
    OfferCreateData,
)

# --- Service layer for candidatures ---
from services.candidatures_service import (
    list_for_offer,
    get_candidature,
    create_candidature,
    mark_sent,
    delete_candidature,
    validate_letter_path,
    CandidatureCreateData,
)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("CV Manager - Candidatures")
        self.showMaximized()

        self.session = SessionLocal()

        self._setup_ui()
        self._load_offers()

    def _setup_ui(self):

        # --- Root central widget avec sidebar + contenu principal ---
        root = QWidget(self)
        self.setCentralWidget(root)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ----- Sidebar à gauche -----
        sidebar = QFrame(root)
        sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(8)

        title_label = QLabel("CV Manager")
        title_label.setObjectName("SidebarTitle")
        sidebar_layout.addWidget(title_label)
        sidebar_layout.addSpacing(12)

        # Actions principales (anciennement toolbar)
        actions_label = QLabel("Actions")
        actions_label.setProperty("heading", True)
        sidebar_layout.addWidget(actions_label)

        btn_new_offer = QPushButton("Nouvelle offre")
        btn_new_offer.setObjectName("SidebarButton")
        btn_new_offer.clicked.connect(self.on_new_offer)
        sidebar_layout.addWidget(btn_new_offer)

        btn_prepare_letter = QPushButton("Préparer lettre")
        btn_prepare_letter.setObjectName("SidebarButton")
        btn_prepare_letter.clicked.connect(self.on_prepare_letter)
        sidebar_layout.addWidget(btn_prepare_letter)


        btn_all_candidatures = QPushButton("Toutes les candidatures")
        btn_all_candidatures.setObjectName("SidebarButton")
        btn_all_candidatures.clicked.connect(self.on_show_candidatures)
        sidebar_layout.addWidget(btn_all_candidatures)

        btn_refresh = QPushButton("Rafraîchir")
        btn_refresh.setObjectName("SidebarButton")
        btn_refresh.clicked.connect(
            lambda: (
                self.dashboard.refresh()
                if getattr(self, "stack", None) and self.stack.currentIndex() == 0
                else self.stats.refresh()
                if getattr(self, "stack", None) and self.stack.currentIndex() == 2
                else self.open_offer_detail(self.current_offer)
                if getattr(self, "stack", None)
                and self.stack.currentIndex() == getattr(self, "offer_detail_index", -1)
                and self.current_offer
                else self._load_offers()
            )
        )
        sidebar_layout.addWidget(btn_refresh)

        sidebar_layout.addSpacing(12)

        btn_home = QPushButton("Annonces")
        btn_home.setObjectName("SidebarButton")
        sidebar_layout.addWidget(btn_home)

        btn_dashboard = QPushButton("Tableau de bord")
        btn_dashboard.setObjectName("SidebarButton")
        sidebar_layout.addWidget(btn_dashboard)

        btn_stats = QPushButton("Statistiques")
        btn_stats.setObjectName("SidebarButton")
        sidebar_layout.addWidget(btn_stats)

        # Connexions pour la navigation de la sidebar
        btn_home.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_dashboard.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        btn_stats.clicked.connect(lambda: self.stack.setCurrentIndex(2))

        sidebar_layout.addStretch()

        btn_settings = QPushButton("Paramètres")
        btn_settings.setObjectName("SidebarButton")
        sidebar_layout.addWidget(btn_settings)
        btn_settings.clicked.connect(lambda: self.stack.setCurrentIndex(3))

        # ----- Zone principale à droite -----
        main_container = QWidget(root)
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # --- Pages "Annonces" (cards) et "Détail" (page dédiée) ---
        self.current_offer = None

        # Page annonces (cards) — widget dédié
        self.offers_page = OffersPage(
            parent=self,
            title="Annonces",
            columns=3,
            status_resolver=self._resolve_offer_status,
        )
        self.offers_page.offerClicked.connect(self.open_offer_detail)

        # Page détail annonce — widget dédié
        self.offer_detail_page = OfferDetailPage(self)
        self.offer_detail_page.backRequested.connect(lambda: self.stack.setCurrentIndex(1))
        self.offer_detail_page.openLetterRequested.connect(self.on_open_letter_by_id)
        self.offer_detail_page.markSentRequested.connect(self.on_mark_sent_by_id)
        self.offer_detail_page.deleteRequested.connect(self.on_delete_candidature_by_id)

        # --- Système de pages : Dashboard + Vue principale ---
        from PySide6.QtWidgets import QStackedWidget

        self.stack = QStackedWidget(main_container)
        main_layout.addWidget(self.stack)

        # Page 0 : Dashboard
        self.dashboard = DashboardWidget(self.session, self)
        self.stack.addWidget(self.dashboard)

        # Page 1 : Annonces (cards)
        self.stack.addWidget(self.offers_page)

        # Page 2 : Statistiques
        self.stats = StatsWidget(self.session, self)
        self.stack.addWidget(self.stats)

        # Page 3 : Paramètres
        self.settings = SettingsWidget(self.session, self)
        self.stack.addWidget(self.settings)

        # Page 4 : Détail annonce (toujours à la fin)
        self.stack.addWidget(self.offer_detail_page)
        self.offer_detail_index = self.stack.count() - 1

        # Afficher la vue principale par défaut
        self.stack.setCurrentIndex(1)

        # Ajout de la sidebar et du contenu principal dans le layout racine
        root_layout.addWidget(sidebar)
        root_layout.addWidget(main_container)


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

    def _clear_layout(self, layout):
        """Supprime tous les widgets d'un layout (utile pour rerender des listes de cards)."""
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def open_offer_detail(self, offre: Offre):
        self.current_offer = offre
        self.offer_detail_page.set_offer(offre)

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

        self.offer_detail_page.set_letters(vms)
        self.stack.setCurrentIndex(self.offer_detail_index)

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
        self.offers_page.set_offers(offers)

    def on_offer_selected(self, current, previous):
        if not hasattr(self, "detail_view") or not hasattr(self, "candidatures_list"):
            return
        if not current:
            self.detail_view.clear()
            self.candidatures_list.clear()
            return

        offre_id = current.data(Qt.UserRole)
        offre = get_offer(self.session, offre_id)

        if not offre:
            self.detail_view.clear()
            self.candidatures_list.clear()
            return

        texte = (
            f"Titre : {offre.titre_poste}\n"
            f"Entreprise : {offre.entreprise or ''}\n"
            f"Source : {offre.source or ''}\n"
            f"URL : {offre.url or ''}\n"
            f"Localisation : {offre.localisation or ''}\n"
            f"Type de contrat : {offre.type_contrat or ''}\n\n"
            f"Texte de l'annonce :\n{offre.texte_annonce or ''}"
        )
        self.detail_view.setPlainText(texte)

        # Charger les candidatures liées
        self._load_candidatures_for_offer(offre.id)

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

    def _get_or_create_profile(self):
        """Retourne le ProfilCandidat unique, en le créant si besoin."""
        profil = self.session.query(ProfilCandidat).first()
        if profil is None:
            profil = ProfilCandidat(
                nom="",
                prenom="",
                email="",
            )
            self.session.add(profil)
            self.session.commit()
        return profil


    def _get_selected_offer(self) -> Offre | None:
        return self.current_offer

    def on_prepare_letter(self):
        offre = self._get_selected_offer()
        if not offre:
            QMessageBox.warning(self, "Préparation lettre", "Sélectionne d'abord une offre dans la liste.")
            return

        profil = self._get_or_create_profile()

        try:
            output_path = render_lettre_candidature_html(profil, offre)
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

    def _load_candidatures_for_offer(self, offre_id: int):
        """Charge les candidatures liées à une offre et les affiche dans la liste."""
        if not hasattr(self, "candidatures_list"):
            return

        self.candidatures_list.clear()

        candidatures = (
            self.session.query(Candidature)
            .filter_by(offre_id=offre_id)
            .order_by(Candidature.id.desc())
            .all()
        )

        for cand in candidatures:
            date_txt = cand.date_envoi.strftime("%d/%m/%Y") if cand.date_envoi else "Brouillon"
            statut_txt = cand.statut.name if cand.statut else "INCONNU"

            text = f"{date_txt} – {statut_txt}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, cand.id)
            self.candidatures_list.addItem(item)

    def _get_selected_candidature(self) -> Candidature | None:
        if not hasattr(self, "candidatures_list"):
            return None
        item = self.candidatures_list.currentItem()
        if not item:
            return None

        cand_id = item.data(Qt.UserRole)
        if not cand_id:
            return None

        return self.session.query(Candidature).filter_by(id=cand_id).first()

    def on_open_letter(self):
        cand = self._get_selected_candidature()
        if not cand:
            QMessageBox.warning(self, "Ouvrir la lettre", "Sélectionne une candidature dans la liste.")
            return

        if not cand.chemin_lettre:
            QMessageBox.warning(self, "Ouvrir la lettre", "Cette candidature n'a pas encore de lettre associée.")
            return

        path = Path(cand.chemin_lettre)
        if not path.exists():
            QMessageBox.critical(self, "Erreur", f"Le fichier n'existe pas : {path}")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))

    def on_delete_candidature(self):
        cand = self._get_selected_candidature()
        if not cand:
            QMessageBox.warning(
                self,
                "Suppression",
                "Sélectionne d'abord une candidature dans la liste."
            )
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

        # Si on doit supprimer le fichier
        if clicked == btn_db_and_file and cand.chemin_lettre:
            path = Path(cand.chemin_lettre)
            if path.exists():
                try:
                    path.unlink()
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Suppression fichier",
                        f"Le fichier n'a pas pu être supprimé : {e}"
                    )

        offre_id = cand.offre_id

        # Suppression en base
        self.session.delete(cand)
        self.session.commit()

        # Rafraîchir la liste de candidatures pour l'offre
        self._load_candidatures_for_offer(offre_id)

    def on_mark_sent(self):
        cand = self._get_selected_candidature()
        if not cand:
            QMessageBox.warning(
                self,
                "Marquer comme envoyée",
                "Sélectionne d'abord une candidature dans la liste."
            )
            return

        cand.statut = CandidatureStatut.ENVOYEE
        cand.date_envoi = date.today()
        self.session.commit()

        QMessageBox.information(self, "Envoyée", "La candidature est maintenant marquée comme envoyée.")

        self._load_candidatures_for_offer(cand.offre_id)

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