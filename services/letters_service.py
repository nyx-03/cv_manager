"""Services (métier) liés à la génération de lettres de motivation.

Objectifs :
- Centraliser la génération HTML/CSS des lettres.
- Ne dépendre ni de Qt, ni de PySide6.
- Fournir une API simple à la couche UI (MainWindow / dialogs).

Ce module:
- Résout un template (nom ou chemin) depuis des dossiers connus (templates/ ...).
- Lit un template HTML (fichier).
- Injecte un contexte (profil + offre) et rend le template (Jinja2 si disponible).
- Écrit un fichier HTML dans un dossier de sortie.

Format template supporté (simple) :
- Variables: {{ variable }}
- Dot-notation: {{ profil.nom }}, {{ offre.titre_poste }}

Note: les templates `.j2` sont rendus via Jinja2 (conditions/boucles/expressions supportées).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional


try:
    from jinja2 import Environment, StrictUndefined, Undefined, UndefinedError, TemplateSyntaxError, select_autoescape
except Exception:  # pragma: no cover
    Environment = None  # type: ignore
    StrictUndefined = None  # type: ignore
    Undefined = None  # type: ignore
    UndefinedError = None  # type: ignore
    TemplateSyntaxError = None  # type: ignore
    select_autoescape = None  # type: ignore


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
# Template resolution
# -----------------------------------------------------------------------------

# Dossiers connus (ordre de priorité)
_DEFAULT_TEMPLATE_DIRS: tuple[Path, ...] = (
    # <repo>/templates
    Path(__file__).resolve().parent.parent / "templates",
    # <repo>/ui/templates (si tu en ajoutes plus tard)
    Path(__file__).resolve().parent.parent / "ui" / "templates",
)

# Template lettre par défaut (fichier présent dans /templates)
DEFAULT_LETTER_TEMPLATE_NAME = "lettre_modern.html.j2"


def resolve_template_path(
    template: str | Path,
    *,
    extra_dirs: Optional[list[str | Path]] = None,
) -> tuple[Path, list[Path]]:
    """Résout un template à partir d'un nom ou d'un chemin.

    - Si `template` est un chemin existant: il est utilisé.
    - Sinon, on cherche dans les dossiers connus (templates/, ui/templates/, + extra_dirs).

    Returns:
        (resolved_path, tried_paths)
    """
    template_path = Path(template).expanduser()

    tried: list[Path] = []

    # 1) Chemin direct
    if template_path.is_absolute() or template_path.parent != Path("."):
        tried.append(template_path)
        if template_path.exists():
            return template_path, tried

    # 2) Recherche dans les dossiers connus
    dirs: list[Path] = list(_DEFAULT_TEMPLATE_DIRS)
    if extra_dirs:
        for d in extra_dirs:
            dirs.append(Path(d).expanduser())

    # 3) Essais: nom exact, + variantes d'extensions
    name = template_path.name
    candidates = [name]
    if not name.endswith(".j2"):
        candidates.append(name + ".j2")
    if not name.endswith(".html"):
        candidates.append(name + ".html")
    if not name.endswith(".html.j2"):
        candidates.append(name + ".html.j2")

    # Petit filet de sécurité: si un nom contient des espaces (ex: "developer Python.html"),
    # on tente une version "slugifiée".
    if " " in name:
        slug = _slugify(Path(name).stem)
        if slug:
            for ext in (".html", ".html.j2", ".j2"):
                candidates.append(slug + ext)

    seen: set[Path] = set()
    for d in dirs:
        for c in candidates:
            p = (d / c).resolve()
            if p in seen:
                continue
            seen.add(p)
            tried.append(p)
            if p.exists():
                return p, tried

    return template_path, tried


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

    resolved_template, tried = resolve_template_path(template_path)
    if not resolved_template.exists():
        tried_txt = "\n".join(f"- {p}" for p in tried)
        raise FileNotFoundError(
            f"Template introuvable. Chemins testés :\n{tried_txt}"
        )

    template_path = resolved_template

    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    template_html = template_path.read_text(encoding="utf-8")

    # Si le template contient des blocs Jinja2 et que Jinja2 n'est pas installé, on aide l'utilisateur.
    if Environment is None and ("{%" in template_html or "%}" in template_html):
        raise LetterTemplateError(
            "Template Jinja2 détecté (.j2) mais Jinja2 n'est pas installé. "
            "Installe la dépendance: pip install jinja2"
        )

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


# -----------------------------------------------------------------------------
# Default template path convenience
# -----------------------------------------------------------------------------

def get_default_letter_template_path() -> Path:
    """Retourne le chemin résolu du template de lettre par défaut."""
    resolved, _ = resolve_template_path(DEFAULT_LETTER_TEMPLATE_NAME)
    return resolved


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

    # Champs "plats" attendus par les templates (compat)
    date_du_jour = date_fr

    # Paragraphes: par défaut, on génère une base simple (tu pourras les éditer ensuite)
    titre = offre_ctx.get("titre_poste", "")
    entreprise = offre_ctx.get("entreprise", "")

    paragraphe_intro = (
        f"Je vous soumets ma candidature au poste de {titre} "
        f"au sein de {entreprise}.".strip()
        if titre or entreprise
        else "Je vous soumets ma candidature pour le poste proposé."
    )
    paragraphe_exp1 = "Fort d’une expérience solide en développement logiciel, je conçois des solutions fiables et maintenables, avec une attention particulière à la qualité et à la lisibilité du code."
    paragraphe_exp2 = "J’apprécie les environnements où l’on combine rigueur technique, collaboration et amélioration continue, afin de livrer rapidement de la valeur tout en maîtrisant la dette technique."
    paragraphe_poste = "Votre offre a retenu mon attention par son périmètre et les responsabilités associées ; je serais ravi de contribuer à vos projets et de participer à l’évolution de vos produits."
    paragraphe_personnalite = "Autonome, curieux et organisé, je m’intègre facilement à une équipe et je communique de façon claire, avec un vrai souci de compréhension du besoin."
    paragraphe_conclusion = "Je me tiens à votre disposition pour un entretien afin d’échanger sur mes motivations et sur la manière dont je peux contribuer à votre organisation."

    # Options (la UI pourra les alimenter plus tard)
    tagline = profil_ctx.get("titre", "")
    reference = ""
    badge_text = ""
    lieu_entreprise = offre_ctx.get("localisation", "")

    return {
        "profil": profil_ctx,
        "offre": offre_ctx,
        "now": {
            "iso": now.isoformat(timespec="seconds"),
            "date_fr": date_fr,
        },
        "full_name": full_name,
        "date_du_jour": date_du_jour,
        "tagline": tagline,
        "reference": reference,
        "badge_text": badge_text,
        "lieu_entreprise": lieu_entreprise,
        "paragraphe_intro": paragraphe_intro,
        "paragraphe_exp1": paragraphe_exp1,
        "paragraphe_exp2": paragraphe_exp2,
        "paragraphe_poste": paragraphe_poste,
        "paragraphe_personnalite": paragraphe_personnalite,
        "paragraphe_conclusion": paragraphe_conclusion,
    }


# -----------------------------------------------------------------------------
# Template rendering
# -----------------------------------------------------------------------------


_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}")


def render_template(template_html: str, context: Mapping[str, Any], *, strict: bool = False) -> str:
    """Rend un template HTML.

    - Si Jinja2 est disponible: rendu complet des templates `.j2` (conditions/boucles/expressions).
    - Sinon: fallback minimal sur remplacements `{{ a.b }}` (ne supporte pas `{% if %}` etc.).

    Args:
        template_html: contenu du template.
        context: dictionnaire de contexte.
        strict: si True, lève une erreur si une variable est manquante (utile en debug).
    """

    # 1) Jinja2 (recommandé)
    if Environment is not None:
        try:
            undefined_cls = StrictUndefined if strict and StrictUndefined is not None else Undefined
            env = Environment(
                autoescape=select_autoescape(["html", "xml"]) if select_autoescape is not None else True,
                undefined=undefined_cls,  # type: ignore[arg-type]
                trim_blocks=True,
                lstrip_blocks=True,
            )
            tpl = env.from_string(template_html)
            return tpl.render(**dict(context))
        except Exception as e:
            # Améliore le diagnostic des erreurs de syntaxe Jinja2
            if TemplateSyntaxError is not None and isinstance(e, TemplateSyntaxError):
                line = getattr(e, "lineno", None)
                name = getattr(e, "name", None) or "<template>"
                details = str(e)

                # Extrait une fenêtre de lignes autour de l'erreur
                snippet = ""
                if line and isinstance(line, int):
                    lines = template_html.splitlines()
                    start = max(line - 3, 0)
                    end = min(line + 2, len(lines))
                    excerpt = []
                    for i in range(start, end):
                        prefix = ">" if (i + 1) == line else " "
                        excerpt.append(f"{prefix} {i+1:04d}: {lines[i]}")
                    snippet = "\n".join(excerpt)

                msg = f"Erreur de syntaxe Jinja2 dans {name}" + (f" (ligne {line})" if line else "") + f": {details}"
                if snippet:
                    msg += "\n\n" + snippet
                raise LetterTemplateError(msg)

            # Variable manquante en strict, etc.
            if UndefinedError is not None and isinstance(e, UndefinedError):
                raise LetterTemplateError(f"Erreur de rendu Jinja2 (variable manquante): {e}")

            raise LetterTemplateError(f"Erreur de rendu Jinja2: {e}")

    # 2) Fallback minimal (compat)
    def resolve(path: str) -> str:
        parts = path.split(".")
        cur: Any = context
        for p in parts:
            if isinstance(cur, Mapping) and p in cur:
                cur = cur[p]
            else:
                return ""
        return "" if cur is None else str(cur)

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