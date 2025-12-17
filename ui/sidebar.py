


from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QWidget


@dataclass(frozen=True)
class SidebarActions:
    """Noms d'actions déclenchées par la sidebar."""

    NEW_OFFER: str = "new_offer"
    PREPARE_LETTER: str = "prepare_letter"
    SHOW_CANDIDATURES: str = "show_candidatures"
    REFRESH: str = "refresh"


@dataclass(frozen=True)
class SidebarPages:
    """Noms de pages (navigation) déclenchées par la sidebar."""

    DASHBOARD: str = "dashboard"
    OFFERS: str = "offers"
    STATS: str = "stats"
    SETTINGS: str = "settings"


class Sidebar(QFrame):
    """Barre latérale gauche.

    - Émet navigateRequested(page_name) pour changer de page.
    - Émet actionRequested(action_name) pour déclencher une action.

    QSS:
    - ObjectName: Sidebar
    - Buttons: SidebarButton
    - Separators: SidebarSeparator
    """

    navigateRequested = Signal(str)
    actionRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")

        self.actions = SidebarActions()
        self.pages = SidebarPages()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # --- Actions (haut)
        self.btn_new_offer = self._btn("Nouvelle offre", self.actions.NEW_OFFER)
        layout.addWidget(self.btn_new_offer)

        self.btn_prepare_letter = self._btn("Préparer lettre", self.actions.PREPARE_LETTER)
        layout.addWidget(self.btn_prepare_letter)

        self.btn_show_candidatures = self._btn("Toutes candidatures", self.actions.SHOW_CANDIDATURES)
        layout.addWidget(self.btn_show_candidatures)

        self.btn_refresh = self._btn("Rafraîchir", self.actions.REFRESH)
        layout.addWidget(self.btn_refresh)

        # --- Navigation
        self._separator(layout)

        self.btn_offers = self._nav_btn("Annonces", self.pages.OFFERS)
        layout.addWidget(self.btn_offers)

        self.btn_dashboard = self._nav_btn("Tableau de bord", self.pages.DASHBOARD)
        layout.addWidget(self.btn_dashboard)

        self.btn_stats = self._nav_btn("Statistiques", self.pages.STATS)
        layout.addWidget(self.btn_stats)

        self.btn_settings = self._nav_btn("Paramètres", self.pages.SETTINGS)
        layout.addWidget(self.btn_settings)

        layout.addStretch(1)

    # -------------------------
    # Helpers
    # -------------------------

    def _base_btn(self, text: str) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName("SidebarButton")
        return b

    def _btn(self, text: str, action_name: str) -> QPushButton:
        b = self._base_btn(text)
        b.clicked.connect(lambda: self.actionRequested.emit(action_name))
        return b

    def _nav_btn(self, text: str, page_name: str) -> QPushButton:
        b = self._base_btn(text)
        b.clicked.connect(lambda: self.navigateRequested.emit(page_name))
        return b

    def _separator(self, layout: QVBoxLayout) -> None:
        sep = QFrame()
        sep.setObjectName("SidebarSeparator")
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

    # -------------------------
    # Optional API
    # -------------------------

    def set_active_page(self, page_name: str) -> None:
        """Marque visuellement le bouton actif via une propriété QSS.

        (Optionnel) : MainWindow peut appeler cette méthode pour gérer un état.
        """
        mapping = {
            self.pages.OFFERS: self.btn_offers,
            self.pages.DASHBOARD: self.btn_dashboard,
            self.pages.STATS: self.btn_stats,
            self.pages.SETTINGS: self.btn_settings,
        }
        for name, btn in mapping.items():
            btn.setProperty("active", name == page_name)
            btn.style().unpolish(btn)
            btn.style().polish(btn)