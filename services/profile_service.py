

"""Services (métier) liés au profil candidat.

Objectifs :
- Centraliser l'accès DB (SQLAlchemy) au profil.
- Garder la couche UI (PySide6) "bête" : pas de requêtes dans les widgets.
- Fournir une API simple: charger, créer, mettre à jour.

Ce module ne dépend PAS de Qt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from models import ProfilCandidat


@dataclass(frozen=True)
class ProfileData:
    """Données du profil (tous champs optionnels sauf quand utilisé en création)."""

    prenom: str = ""
    nom: str = ""
    email: str = ""
    telephone: str = ""
    adresse: str = ""
    ville: str = ""
    code_postal: str = ""
    pays: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""
    titre: str = ""


@dataclass(frozen=True)
class ProfileUpdateData:
    """Mise à jour partielle (None = ne pas changer)."""

    prenom: Optional[str] = None
    nom: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    adresse: Optional[str] = None
    ville: Optional[str] = None
    code_postal: Optional[str] = None
    pays: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    titre: Optional[str] = None


# -----------------------------------------------------------------------------
# Queries
# -----------------------------------------------------------------------------

def get_profile(session: Session) -> Optional[ProfilCandidat]:
    """Retourne le profil candidat (single row), ou None si absent."""
    return session.query(ProfilCandidat).order_by(ProfilCandidat.id.asc()).first()


def ensure_profile(session: Session, defaults: Optional[ProfileData] = None) -> ProfilCandidat:
    """Retourne un profil existant, ou le crée s'il n'existe pas."""
    profil = get_profile(session)
    if profil:
        return profil

    d = defaults or ProfileData()
    profil = ProfilCandidat(
        prenom=d.prenom,
        nom=d.nom,
        email=d.email,
        telephone=d.telephone,
        adresse=d.adresse,
        ville=d.ville,
        code_postal=d.code_postal,
        pays=d.pays,
        linkedin=d.linkedin,
        github=d.github,
        portfolio=d.portfolio,
        titre=d.titre,
    )
    session.add(profil)
    session.commit()
    session.refresh(profil)
    return profil


# -----------------------------------------------------------------------------
# Mutations
# -----------------------------------------------------------------------------

def update_profile(session: Session, data: ProfileUpdateData) -> ProfilCandidat:
    """Met à jour le profil (crée-le si nécessaire) et commit.

    Tolérant : si le modèle ne contient pas certains champs, on ignore.
    """
    profil = ensure_profile(session)

    # Champs connus côté service
    fields = (
        "prenom",
        "nom",
        "email",
        "telephone",
        "adresse",
        "ville",
        "code_postal",
        "pays",
        "linkedin",
        "github",
        "portfolio",
        "titre",
    )

    for f in fields:
        value = getattr(data, f)
        if value is None:
            continue
        if hasattr(profil, f):
            setattr(profil, f, value)

    session.commit()
    session.refresh(profil)
    return profil


def to_profile_data(profil: ProfilCandidat) -> ProfileData:
    """Convertit un modèle ProfilCandidat vers ProfileData (utile pour remplir l'UI)."""
    def g(attr: str) -> str:
        return str(getattr(profil, attr, "") or "")

    return ProfileData(
        prenom=g("prenom"),
        nom=g("nom"),
        email=g("email"),
        telephone=g("telephone"),
        adresse=g("adresse"),
        ville=g("ville"),
        code_postal=g("code_postal"),
        pays=g("pays"),
        linkedin=g("linkedin"),
        github=g("github"),
        portfolio=g("portfolio"),
        titre=g("titre"),
    )