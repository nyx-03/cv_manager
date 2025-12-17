"""Services (métier) liés aux offres.

Objectifs :
- Centraliser la logique SQLAlchemy (CRUD) des offres.
- Garder la couche UI (PySide6) le plus "bête" possible.

Ce module ne dépend PAS de Qt.
"""

from dataclasses import dataclass
from collections.abc import Iterable

from sqlalchemy.orm import Session

from models import Offre


@dataclass(frozen=True)
class OfferCreateData:
    """Données nécessaires pour créer une Offre."""

    titre_poste: str
    entreprise: str = ""
    url: str = ""
    source: str = ""
    localisation: str = ""
    type_contrat: str = ""
    texte_annonce: str = ""


@dataclass(frozen=True)
class OfferUpdateData:
    """Données modifiables d'une Offre (None = ne pas changer)."""

    titre_poste: str | None = None
    entreprise: str | None = None
    url: str | None = None
    source: str | None = None
    localisation: str | None = None
    type_contrat: str | None = None
    texte_annonce: str | None = None


# -----------------------------------------------------------------------------
# Queries
# -----------------------------------------------------------------------------

def list_offers(session: Session, *, desc: bool = True) -> list[Offre]:
    """Retourne toutes les offres (triées par id)."""
    q = session.query(Offre)
    q = q.order_by(Offre.id.desc() if desc else Offre.id.asc())
    return q.all()


def get_offer(session: Session, offer_id: int) -> Offre | None:
    """Retourne une offre par id, ou None."""
    return session.query(Offre).filter_by(id=offer_id).first()


def search_offers(
    session: Session,
    *,
    text: str = "",
    entreprise: str = "",
    source: str = "",
    localisation: str = "",
    limit: int = 200,
) -> list[Offre]:
    """Recherche simple côté offres (LIKE) sur quelques champs.

    Note: les filtres sur statut de candidature sont gérés dans candidatures_service.
    """
    q = session.query(Offre)

    if text:
        like = f"%{text.strip()}%"
        q = q.filter(
            (Offre.titre_poste.ilike(like))
            | (Offre.entreprise.ilike(like))
            | (Offre.texte_annonce.ilike(like))
        )

    if entreprise:
        q = q.filter(Offre.entreprise.ilike(f"%{entreprise.strip()}%"))

    if source:
        q = q.filter(Offre.source.ilike(f"%{source.strip()}%"))

    if localisation:
        q = q.filter(Offre.localisation.ilike(f"%{localisation.strip()}%"))

    q = q.order_by(Offre.id.desc()).limit(max(1, int(limit)))
    return q.all()


# -----------------------------------------------------------------------------
# Mutations
# -----------------------------------------------------------------------------

def create_offer(session: Session, data: OfferCreateData) -> Offre:
    """Crée une offre et commit."""
    offre = Offre(
        titre_poste=data.titre_poste,
        entreprise=data.entreprise,
        url=data.url,
        source=data.source,
        localisation=data.localisation,
        type_contrat=data.type_contrat,
        texte_annonce=data.texte_annonce,
    )
    session.add(offre)
    session.commit()
    session.refresh(offre)
    return offre


def update_offer(session: Session, offer_id: int, data: OfferUpdateData) -> Offre:
    """Met à jour une offre et commit.

    Lève ValueError si l'offre n'existe pas.
    """
    offre = get_offer(session, offer_id)
    if not offre:
        raise ValueError(f"Offre introuvable (id={offer_id})")

    for field in (
        "titre_poste",
        "entreprise",
        "url",
        "source",
        "localisation",
        "type_contrat",
        "texte_annonce",
    ):
        value = getattr(data, field)
        if value is not None:
            setattr(offre, field, value)

    session.commit()
    session.refresh(offre)
    return offre


def delete_offer(session: Session, offer_id: int) -> None:
    """Supprime une offre (DB seulement) et commit.

    Note: si tu veux supprimer aussi les candidatures associées, gère ça dans
    `candidatures_service` (ou avec une cascade côté modèle SQLAlchemy).
    """
    offre = get_offer(session, offer_id)
    if not offre:
        raise ValueError(f"Offre introuvable (id={offer_id})")

    session.delete(offre)
    session.commit()


def upsert_offers(session: Session, offers: Iterable[OfferCreateData]) -> list[Offre]:
    """Crée plusieurs offres rapidement.

    Stratégie simple: création en masse sans déduplication.
    (Si tu veux dédupliquer par URL ou (entreprise+titre), on le fera ensuite.)
    """
    created: list[Offre] = []
    for data in offers:
        created.append(create_offer(session, data))
    return created
