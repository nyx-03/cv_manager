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


import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


try:
    from jinja2 import (
        Environment,
        StrictUndefined,
        Undefined,
        UndefinedError,
        TemplateSyntaxError,
        select_autoescape,
    )
    try:
        # Sandbox recommandé (limite l'accès aux attributs Python)
        from jinja2.sandbox import SandboxedEnvironment
    except Exception:  # pragma: no cover
        SandboxedEnvironment = None  # type: ignore
except Exception:  # pragma: no cover
    Environment = None  # type: ignore
    SandboxedEnvironment = None  # type: ignore
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

# Dossier templates utilisateur (local, à ignorer par Git)
_USER_TEMPLATES_DIR: Path = Path.cwd() / "data" / "templates"

# Dossiers connus (ordre de priorité)
_DEFAULT_TEMPLATE_DIRS: tuple[Path, ...] = (
    # <repo>/templates
    Path(__file__).resolve().parent.parent / "templates",
    # <repo>/ui/templates (si tu en ajoutes plus tard)
    Path(__file__).resolve().parent.parent / "ui" / "templates",
    # <project>/data/templates (templates importés par l'utilisateur)
    _USER_TEMPLATES_DIR,
)

# Template lettre par défaut (fichier présent dans /templates)
DEFAULT_LETTER_TEMPLATE_NAME = "lettre_moderne.html.j2"


def resolve_template_path(
    template: str | Path,
    *,
    extra_dirs: list[str | Path] | None = None,
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
# User template management
# -----------------------------------------------------------------------------

def ensure_user_templates_dir() -> Path:
    """Crée (si besoin) et retourne le dossier des templates utilisateur."""
    _USER_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    return _USER_TEMPLATES_DIR


def list_user_templates() -> list[Path]:
    """Liste les templates utilisateur disponibles (triés)."""
    d = ensure_user_templates_dir()
    items = []
    for p in d.glob("*.j2"):
        if p.is_file():
            items.append(p)
    # Autorise aussi les templates HTML non-j2 (fallback simple)
    for p in d.glob("*.html"):
        if p.is_file():
            items.append(p)
    # Uniques + tri
    uniq = sorted({p.resolve() for p in items})
    return uniq


def import_user_template(src_path: str | Path, *, overwrite: bool = False) -> Path:
    """Importe un template (copie) dans `data/templates/`.

    Args:
        src_path: chemin du fichier template à importer.
        overwrite: si True, écrase un template existant avec le même nom.

    Returns:
        Chemin du template importé dans le dossier utilisateur.

    Raises:
        FileNotFoundError: si le fichier source n'existe pas.
        LetterTemplateError: si l'extension est invalide ou si la copie échoue.
    """
    src = Path(src_path).expanduser().resolve()
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"Fichier template introuvable: {src}")

    if src.suffix.lower() not in {".j2", ".html"} and not src.name.lower().endswith(".html.j2"):
        raise LetterTemplateError(
            "Template invalide. Formats supportés: .j2, .html, .html.j2"
        )

    dest_dir = ensure_user_templates_dir()
    dest = (dest_dir / src.name).resolve()

    if dest.exists() and not overwrite:
        raise LetterTemplateError(
            f"Un template portant ce nom existe déjà: {dest.name}. "
            "Renomme-le ou active overwrite=True."
        )

    try:
        dest.write_bytes(src.read_bytes())
    except Exception as e:
        raise LetterTemplateError(f"Impossible d'importer le template: {e}")

    # Validation légère (compile) si Jinja2 dispo
    try:
        validate_template_file(dest)
    except Exception:
        # On laisse le fichier importé, mais l'UI pourra afficher l'erreur au test.
        pass

    return dest


def validate_template_text(template_html: str) -> None:
    """Valide un template (syntaxe Jinja2) en le compilant.

    Si Jinja2 n'est pas disponible, ne fait qu'une validation minimale.
    """
    if not template_html.strip():
        raise LetterTemplateError("Template vide")

    # Si présence de blocs Jinja2, on requiert Jinja2
    if ("{%" in template_html or "%}" in template_html) and Environment is None:
        raise LetterTemplateError(
            "Template Jinja2 détecté (.j2) mais Jinja2 n'est pas installé. "
            "Installe la dépendance: pip install jinja2"
        )

    if Environment is None:
        # Fallback: on accepte (remplacements {{ a.b }})
        return

    try:
        env_cls = SandboxedEnvironment if SandboxedEnvironment is not None else Environment
        env = env_cls(
            autoescape=select_autoescape(["html", "xml"]) if select_autoescape is not None else True,
            undefined=Undefined,  # type: ignore[arg-type]
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.from_string(template_html)
    except Exception as e:
        if TemplateSyntaxError is not None and isinstance(e, TemplateSyntaxError):
            line = getattr(e, "lineno", None)
            details = str(e)
            raise LetterTemplateError(
                "Erreur de syntaxe Jinja2" + (f" (ligne {line})" if line else "") + f": {details}"
            )
        raise LetterTemplateError(f"Template invalide: {e}")


def validate_template_file(path: str | Path) -> None:
    """Valide un fichier template."""
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Template introuvable: {p}")
    validate_template_text(p.read_text(encoding="utf-8"))


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def generate_letter_html(
    *,
    template_path: str | Path | None = None,
    template_name: str | None = None,
    output_dir: str | Path,
    profil: object,
    offre: object,
    lettre: object | None = None,
    filename_hint: str = "lettre",
    extra_context: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> LetterGenerationResult:
    """Génère une lettre HTML à partir d'un template.

    Args:
        template_path: chemin (ou nom) vers le template HTML. Si None, utilise le template par défaut (profil/app).
        template_name: nom du template (ex: "mon_modele.html.j2"), pratique pour data/templates.
        output_dir: dossier de sortie.
        profil: objet profil (ex: ProfilCandidat).
        offre: objet offre (ex: Offre).
        lettre: objet LettreMotivation optionnel utilisé pour alimenter le contenu.
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

    template_path = resolve_template_for_generation(
        profil=profil,
        template_path=template_path,
        template_name=template_name,
    )

    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    template_html = template_path.read_text(encoding="utf-8")

    # Validation (compile Jinja2) avant rendu pour des erreurs plus propres
    try:
        validate_template_text(template_html)
    except LetterTemplateError as e:
        raise LetterTemplateError(f"Template invalide: {e}")

    # Si le template contient des blocs Jinja2 et que Jinja2 n'est pas installé, on aide l'utilisateur.
    if Environment is None and ("{%" in template_html or "%}" in template_html):
        raise LetterTemplateError(
            "Template Jinja2 détecté (.j2) mais Jinja2 n'est pas installé. "
            "Installe la dépendance: pip install jinja2"
        )

    context = build_letter_context(profil=profil, offre=offre, now=now)
    if lettre is not None:
        for field in (
            "paragraphe_intro",
            "paragraphe_exp1",
            "paragraphe_exp2",
            "paragraphe_poste",
            "paragraphe_personnalite",
            "paragraphe_conclusion",
        ):
            if hasattr(lettre, field):
                value = getattr(lettre, field)
                if value:
                    context[field] = value
        # If lettre has template_name or output_path, do NOT override template_path or output_dir automatically (UI controlled)

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


# --- Helpers pour template par défaut profil et résolution ---

def get_profile_default_template_name(profil: object) -> str:
    """Retourne le nom du template par défaut depuis le profil, si disponible."""
    for field in (
        "template_lettre",
        "template_letter",
        "default_template",
        "default_letter_template",
    ):
        if hasattr(profil, field):
            val = getattr(profil, field)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


def resolve_template_for_generation(
    *,
    profil: object,
    template_path: str | Path | None = None,
    template_name: str | None = None,
    extra_dirs: list[str | Path] | None = None,
) -> Path:
    """Résout le template à utiliser pour la génération.

    Priorité:
    1) template_path explicite (chemin ou nom)
    2) template_name explicite (nom de fichier) — utile pour data/templates
    3) template par défaut stocké dans le profil
    4) template par défaut de l'application
    """
    if template_path:
        resolved, tried = resolve_template_path(template_path, extra_dirs=extra_dirs)
        if not resolved.exists():
            tried_txt = "\n".join(f"- {p}" for p in tried)
            raise FileNotFoundError(f"Template introuvable. Chemins testés :\n{tried_txt}")
        return resolved

    if template_name:
        resolved, tried = resolve_template_path(template_name, extra_dirs=extra_dirs)
        if not resolved.exists():
            tried_txt = "\n".join(f"- {p}" for p in tried)
            raise FileNotFoundError(f"Template introuvable. Chemins testés :\n{tried_txt}")
        return resolved

    profile_tpl = get_profile_default_template_name(profil)
    if profile_tpl:
        resolved, tried = resolve_template_path(profile_tpl, extra_dirs=extra_dirs)
        if resolved.exists():
            return resolved

    # Fallback: template app
    return get_default_letter_template_path()


def build_letter_context(*, profil: object, offre: object, now: datetime | None = None) -> dict[str, Any]:
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
            env_cls = SandboxedEnvironment if SandboxedEnvironment is not None else Environment
            env = env_cls(
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