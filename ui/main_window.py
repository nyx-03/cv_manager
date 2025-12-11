# ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QListWidget, QTextEdit,
    QSplitter, QToolBar, QMessageBox, QDialog, QLabel, QPushButton, QHBoxLayout, QListWidgetItem, QFrame
)
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtCore import Qt, QUrl, QSize
from db import SessionLocal

from services.templates_service import render_lettre_candidature_html
from ui.offer_form_dialog import OfferFormDialog
from ui.dashboard_widget import DashboardWidget
from ui.stats_widget import StatsWidget
from ui.settings_widget import SettingsWidget
from models import Offre, ProfilCandidat, Candidature, CandidatureStatut
from pathlib import Path
from datetime import date


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
                else self._load_offers()
            )
        )
        sidebar_layout.addWidget(btn_refresh)

        sidebar_layout.addSpacing(12)

        btn_dashboard = QPushButton("Tableau de bord")
        btn_dashboard.setObjectName("SidebarButton")
        sidebar_layout.addWidget(btn_dashboard)

        btn_stats = QPushButton("Statistiques")
        btn_stats.setObjectName("SidebarButton")
        sidebar_layout.addWidget(btn_stats)

        # Connexions pour la navigation de la sidebar
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

        # Splitter principal (offres + détails/candidatures)
        splitter = QSplitter(Qt.Horizontal, self)

        # Liste des offres
        self.offers_list = QListWidget()
        self.offers_list.currentItemChanged.connect(self.on_offer_selected)
        self.offers_list.currentItemChanged.connect(lambda *_: self.stack.setCurrentIndex(1))

        # Card pour la liste des offres
        left_card = QFrame()
        left_card.setObjectName("Card")
        left_card.setProperty("cardSection", "offers")
        left_layout = QVBoxLayout(left_card)

        left_label = QLabel("Offres")
        left_label.setProperty("heading", True)
        left_layout.addWidget(left_label)
        left_layout.addWidget(self.offers_list)

        # Zone de détail de l'offre
        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        # Zone candidatures dans une card
        right_panel = QFrame()
        right_panel.setObjectName("Card")
        right_panel.setProperty("cardSection", "details")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        label_details = QLabel("Détails de l'offre")
        label_details.setProperty("heading", True)
        right_layout.addWidget(label_details)
        right_layout.addWidget(self.detail_view)

        label_cand = QLabel("Candidatures pour cette offre :")
        label_cand.setProperty("heading", True)
        right_layout.addWidget(label_cand)

        self.candidatures_list = QListWidget()
        right_layout.addWidget(self.candidatures_list)

        # Boutons candidatures
        cand_buttons_layout = QHBoxLayout()
        cand_buttons_layout.addStretch()

        self.btn_open_letter = QPushButton("Ouvrir la lettre")
        self.btn_open_letter.clicked.connect(self.on_open_letter)
        cand_buttons_layout.addWidget(self.btn_open_letter)

        self.btn_delete_cand = QPushButton("Supprimer la candidature")
        self.btn_delete_cand.clicked.connect(self.on_delete_candidature)
        cand_buttons_layout.addWidget(self.btn_delete_cand)

        self.btn_mark_sent = QPushButton("Marquer comme envoyée")
        self.btn_mark_sent.clicked.connect(self.on_mark_sent)
        cand_buttons_layout.addWidget(self.btn_mark_sent)

        right_layout.addLayout(cand_buttons_layout)

        # Double-clic sur une candidature pour ouvrir la lettre
        self.candidatures_list.itemDoubleClicked.connect(lambda _: self.on_open_letter())

        splitter.addWidget(left_card)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        # --- Système de pages : Dashboard + Vue principale ---
        from PySide6.QtWidgets import QStackedWidget

        self.stack = QStackedWidget(main_container)
        main_layout.addWidget(self.stack)

        # Page 0 : Dashboard
        self.dashboard = DashboardWidget(self.session, self)
        self.stack.addWidget(self.dashboard)

        # Page 1 : Vue principale (ancien splitter)
        page_main = QWidget(self)
        page_main_layout = QVBoxLayout(page_main)
        page_main_layout.setContentsMargins(0, 0, 0, 0)
        page_main_layout.addWidget(splitter)

        self.stack.addWidget(page_main)

        # Page 2 : Statistiques
        self.stats = StatsWidget(self.session, self)
        self.stack.addWidget(self.stats)

        # Page 3 : Paramètres
        self.settings = SettingsWidget(self.session, self)
        self.stack.addWidget(self.settings)

        # Afficher la vue principale par défaut
        self.stack.setCurrentIndex(1)

        # Ajout de la sidebar et du contenu principal dans le layout racine
        root_layout.addWidget(sidebar)
        root_layout.addWidget(main_container)

    def _load_offers(self):
        self.offers_list.clear()
        offers = self.session.query(Offre).order_by(Offre.id.desc()).all()

        for offre in offers:
            item_text = f"{offre.titre_poste} - {offre.entreprise or ''}"
            item = self.offers_list.addItem(item_text)
            item_id = offre.id
            self.offers_list.item(self.offers_list.count() - 1).setData(Qt.UserRole, item_id)

    def on_offer_selected(self, current, previous):
        if not current:
            self.detail_view.clear()
            self.candidatures_list.clear()
            return

        offre_id = current.data(Qt.UserRole)
        offre = self.session.query(Offre).filter_by(id=offre_id).first()

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

            # Sauvegarde dans la DB
            offre = Offre(
                titre_poste=data["titre_poste"],
                entreprise=data["entreprise"],
                source=data["source"],
                url=data["url"],
                localisation=data["localisation"],
                type_contrat=data["type_contrat"],
                texte_annonce=data["texte_annonce"],
            )

            self.session.add(offre)
            self.session.commit()

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
        current_item = self.offers_list.currentItem()
        if not current_item:
            return None

        offre_id = current_item.data(Qt.UserRole)
        if not offre_id:
            return None

        return self.session.query(Offre).filter_by(id=offre_id).first()

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

        candidature = Candidature(
            offre_id=offre.id,
            date_envoi=None,
            statut=CandidatureStatut.A_PREPARER,
            chemin_lettre=str(output_path),
            chemin_cv=None,
            notes=None,
        )
        self.session.add(candidature)
        self.session.commit()

        QMessageBox.information(
            self,
            "Lettre générée",
            f"Lettre HTML générée avec succès :\n{output_path}\n\n"
            "Tu peux l’ouvrir dans ton navigateur et l’imprimer en PDF si besoin."
        )
        self._load_candidatures_for_offer(offre.id)

    def _load_candidatures_for_offer(self, offre_id: int):
        """Charge les candidatures liées à une offre et les affiche dans la liste."""
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