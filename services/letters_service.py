

"""Services (métier) liés à la génération de lettres de motivation.

Objectifs :
- Centraliser la génération HTML/CSS des lettres.
- Ne dépendre ni de Qt, ni de PySide6.
- Fournir une API simple à la couche UI (MainWindow / dialogs).

Ce module:
- Lit un template HTML (fichier).
- Injecte un contexte (profil + offre) via un mini moteur de templating.
- Écrit un fichier HTML dans un dossier de sortie.

Format template supporté (simple) :
- Variables: {{ variable }}
- Dot-notation: {{ profil.nom }}, {{ offre.titre_poste }}

Si tu utilises déjà un moteur (Jinja2, etc.) on pourra le remplacer ensuite.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional


# -----------------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class LetterGenerationResult:
    """Résultat d'une génération de lettre."""

    output_path: Path
    html: str


class LetterTemplateError(RuntimeError):
    pass


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def generate_letter_html(
    *,
    template_path: str | Path,
    output_dir: str | Path,
    profil: object,
    offre: object,
    filename_hint: str = "lettre",
    extra_context: Optional[Mapping[str, Any]] = None,
    now: Optional[datetime] = None,
) -> LetterGenerationResult:
    """Génère une lettre HTML à partir d'un template.

    Args:
        template_path: chemin vers le template HTML.
        output_dir: dossier de sortie.
        profil: objet profil (ex: ProfilCandidat).
        offre: objet offre (ex: Offre).
        filename_hint: base de nom de fichier.
        extra_context: champs additionnels.
        now: override de la date/heure (tests).

    Returns:
        LetterGenerationResult

    Raises:
        FileNotFoundError: template introuvable.
        LetterTemplateError: erreur template/écriture.
    """
    now = now or datetime.now()

    template_path = Path(template_path).expanduser()
    if not template_path.exists():
        raise FileNotFoundError(str(template_path))

    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    template_html = template_path.read_text(encoding="utf-8")

    context = build_letter_context(profil=profil, offre=offre, now=now)
    if extra_context:
        context.update(dict(extra_context))

    html = render_template(template_html, context)

    safe_name = _slugify(filename_hint) or "lettre"
    stamp = now.strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"{safe_name}_{stamp}.html"

    try:
        output_path.write_text(html, encoding="utf-8")
    except Exception as e:
        raise LetterTemplateError(f"Impossible d'écrire la lettre: {e}")

    return LetterGenerationResult(output_path=output_path, html=html)


def build_letter_context(*, profil: object, offre: object, now: Optional[datetime] = None) -> dict[str, Any]:
    """Construit un contexte standard (profil + offre).

    Cette fonction est volontairement tolérante: si un attribut n'existe pas, on renvoie "".
    """
    now = now or datetime.now()

    def g(obj: object, *names: str) -> str:
        for n in names:
            if hasattr(obj, n):
                v = getattr(obj, n)
                if v is not None:
                    return str(v)
        return ""

    profil_ctx = {
        "prenom": g(profil, "prenom", "first_name"),
        "nom": g(profil, "nom", "last_name"),
        "email": g(profil, "email"),
        "telephone": g(profil, "telephone", "tel", "phone"),
        "adresse": g(profil, "adresse", "address"),
        "ville": g(profil, "ville", "city"),
        "code_postal": g(profil, "code_postal", "postal_code"),
        "pays": g(profil, "pays", "country"),
        "linkedin": g(profil, "linkedin"),
        "github": g(profil, "github"),
        "portfolio": g(profil, "portfolio", "website", "site"),
        "titre": g(profil, "titre", "headline"),
    }

    offre_ctx = {
        "titre_poste": g(offre, "titre_poste", "titre"),
        "entreprise": g(offre, "entreprise", "company"),
        "localisation": g(offre, "localisation", "lieu", "location"),
        "type_contrat": g(offre, "type_contrat", "contrat"),
        "source": g(offre, "source"),
        "url": g(offre, "url", "lien"),
        "texte_annonce": g(offre, "texte_annonce", "description"),
    }

    # Quelques champs utiles côté template
    date_fr = now.strftime("%d/%m/%Y")
    full_name = (profil_ctx["prenom"] + " " + profil_ctx["nom"]).strip()

    return {
        "profil": profil_ctx,
        "offre": offre_ctx,
        "now": {
            "iso": now.isoformat(timespec="seconds"),
            "date_fr": date_fr,
        },
        "full_name": full_name,
    }


# -----------------------------------------------------------------------------
# Minimal templating engine
# -----------------------------------------------------------------------------


_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}")


def render_template(template_html: str, context: Mapping[str, Any]) -> str:
    """Rend un template HTML via remplacements {{ ... }}.

    Supporte la dot-notation: {{ profil.nom }} -> context['profil']['nom']
    """

    def resolve(path: str) -> str:
        parts = path.split(".")
        cur: Any = context
        for p in parts:
            if isinstance(cur, Mapping) and p in cur:
                cur = cur[p]
            else:
                # Tolérant : inconnu => chaîne vide
                return ""
        if cur is None:
            return ""
        return str(cur)

    def repl(m: re.Match) -> str:
        return resolve(m.group(1))

    try:
        return _VAR_RE.sub(repl, template_html)
    except Exception as e:
        raise LetterTemplateError(f"Erreur de rendu du template: {e}")


# -----------------------------------------------------------------------------
# Utils
# -----------------------------------------------------------------------------


def _slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9\-\s_]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")