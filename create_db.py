# create_db.py
"""Initialisation et migration légère de la base SQLite.

Ce projet n'utilise pas encore Alembic.
On applique donc une migration minimale:
- create_all() crée les nouvelles tables manquantes
- des ALTER TABLE ajoutent les nouvelles colonnes sur les tables existantes

⚠️ SQLite ne permet pas d'ajouter une contrainte FOREIGN KEY via ALTER TABLE.
On ajoute donc seulement la colonne `candidature.lettre_id` + index.
"""

from __future__ import annotations

from sqlalchemy import text

from db import engine, Base
import models  # noqa: F401  # pour que les classes soient importées et enregistrées dans Base.metadata


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": name},
    ).fetchone()
    return row is not None


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == column for r in rows)  # r[1] = name


def migrate_sqlite() -> None:
    """Applique une migration légère sur SQLite (idempotente)."""
    with engine.begin() as conn:
        # 1) Nouvelle table: créée via create_all, mais on garde une vérification.
        #    (Si models.py est importé, Base.metadata contient lettre_motivation.)
        #    create_all est appelé dans main() juste avant.

        # 2) Ajout de colonne sur candidature: lettre_id
        if _table_exists(conn, "candidature") and not _column_exists(conn, "candidature", "lettre_id"):
            conn.execute(text("ALTER TABLE candidature ADD COLUMN lettre_id INTEGER"))

        # 3) Index utile pour les jointures
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_candidature_lettre_id ON candidature(lettre_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_lettre_motivation_offre_id ON lettre_motivation(offre_id)"))


def main() -> None:
    # Crée les tables manquantes (ne modifie pas les tables existantes)
    Base.metadata.create_all(bind=engine)

    # Applique les migrations légères pour les schémas existants
    migrate_sqlite()

    print("Base de données initialisée / migrée.")


if __name__ == "__main__":
    main()