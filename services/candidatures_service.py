from __future__ import annotations

"""Services (métier) liés aux candidatures / lettres.

Objectifs :
- Centraliser la logique SQLAlchemy pour les candidatures.
- Centraliser les opérations "système" (validation de chemin, suppression fichier).
- Garder la couche UI (PySide6) le plus simple possible.

Ce module ne dépend PAS de Qt.
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from models import Candidature, CandidatureStatut


@dataclass(frozen=True)
class OfferCandidatureStats:
    """Statistiques agrégées sur les candidatures d'une offre."""

    total: int
    by_status: dict[CandidatureStatut, int]


@dataclass(frozen=True)
class CandidatureCreateData:
    """Données nécessaires pour créer une Candidature."""

    offre_id: int
    statut: CandidatureStatut = CandidatureStatut.A_PREPARER
    date_envoi: Optional[date] = None
    notes: str = ""
    chemin_lettre: str = ""


@dataclass(frozen=True)
class CandidatureUpdateData:
    """Champs modifiables d'une Candidature (None = ne pas changer)."""

    statut: Optional[CandidatureStatut] = None
    date_envoi: Optional[date] = None
    notes: Optional[str] = None
    chemin_lettre: Optional[str] = None


# -----------------------------------------------------------------------------
# Queries
# -----------------------------------------------------------------------------

def list_for_offer(session: Session, offre_id: int, *, desc: bool = True) -> list[Candidature]:
    """Retourne les candidatures d'une offre."""
    q = session.query(Candidature).filter_by(offre_id=offre_id)
    q = q.order_by(Candidature.id.desc() if desc else Candidature.id.asc())
    return q.all()


def get_candidature(session: Session, cand_id: int) -> Optional[Candidature]:
    """Retourne une candidature par id, ou None."""
    return session.query(Candidature).filter_by(id=cand_id).first()


# -----------------------------------------------------------------------------
# Mutations
# -----------------------------------------------------------------------------

def create_candidature(session: Session, data: CandidatureCreateData) -> Candidature:
    """Crée une candidature et commit."""
    cand = Candidature(
        offre_id=data.offre_id,
        statut=data.statut,
        date_envoi=data.date_envoi,
        notes=data.notes,
        chemin_lettre=data.chemin_lettre,
    )
    session.add(cand)
    session.commit()
    session.refresh(cand)
    return cand


def update_candidature(session: Session, cand_id: int, data: CandidatureUpdateData) -> Candidature:
    """Met à jour une candidature et commit.

    Lève ValueError si introuvable.
    """
    cand = get_candidature(session, cand_id)
    if not cand:
        raise ValueError(f"Candidature introuvable (id={cand_id})")

    if data.statut is not None:
        cand.statut = data.statut
    if data.date_envoi is not None or data.date_envoi is None:
        # On autorise explicitement la remise à None
        cand.date_envoi = data.date_envoi
    if data.notes is not None:
        cand.notes = data.notes
    if data.chemin_lettre is not None:
        cand.chemin_lettre = data.chemin_lettre

    session.commit()
    session.refresh(cand)
    return cand


def mark_sent(session: Session, cand_id: int) -> Candidature:
    """Marque une candidature comme envoyée et met la date du jour."""
    cand = get_candidature(session, cand_id)
    if not cand:
        raise ValueError(f"Candidature introuvable (id={cand_id})")

    cand.statut = CandidatureStatut.ENVOYEE
    cand.date_envoi = date.today()
    session.commit()
    session.refresh(cand)
    return cand


def delete_candidature(session: Session, cand_id: int, *, delete_file: bool = False) -> None:
    """Supprime une candidature (et éventuellement le fichier de lettre)."""
    cand = get_candidature(session, cand_id)
    if not cand:
        raise ValueError(f"Candidature introuvable (id={cand_id})")

    letter_path = (cand.chemin_lettre or "").strip()

    session.delete(cand)
    session.commit()

    if delete_file and letter_path:
        _try_delete_file(letter_path)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def validate_letter_path(path: str) -> Path:
    """Valide qu'un chemin de lettre existe et renvoie un Path absolu.

    Lève FileNotFoundError si le fichier est absent.
    """
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = p.resolve()
    if not p.exists():
        raise FileNotFoundError(str(p))
    return p


def _try_delete_file(path: str) -> bool:
    """Tente de supprimer un fichier. Retourne True si supprimé."""
    try:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = p.resolve()
        if p.exists():
            p.unlink()
            return True
    except Exception:
        return False
    return False

def get_offer_stats(session: Session, offre_id: int) -> OfferCandidatureStats:
    """
    Retourne les statistiques de candidatures pour une offre donnée :
    - total: nombre total de candidatures
    - by_status: dict de CandidatureStatut -> nombre (0 si aucun)
    """
    from sqlalchemy import func

    # Obtenir les comptes groupés par statut pour l'offre donnée
    q = (
        session.query(Candidature.statut, func.count(Candidature.id))
        .filter(Candidature.offre_id == offre_id)
        .group_by(Candidature.statut)
    )
    counts = dict(q.all())
    # Initialiser le dict de statuts avec 0 pour tous les statuts possibles
    by_status = {statut: 0 for statut in CandidatureStatut}
    for statut, count in counts.items():
        by_status[statut] = count
    total = sum(by_status.values())
    return OfferCandidatureStats(total=total, by_status=by_status)