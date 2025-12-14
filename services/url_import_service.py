from __future__ import annotations

import json
import re
from urllib.parse import urlparse, urlunparse
from typing import Dict

import requests
from bs4 import BeautifulSoup

from datetime import datetime
from pathlib import Path

# Playwright est optionnel (recommandé pour les sites qui rendent le contenu en JS / protègent les pages détail)
try:
    from playwright.sync_api import sync_playwright  # type: ignore
    HAS_PLAYWRIGHT = True
except Exception:
    HAS_PLAYWRIGHT = False


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

TIMEOUT = 10

# --- Shared requests session and headers for robustness ---
SESSION = requests.Session()
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}


class UrlImportError(Exception):
    pass


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def import_offer_from_url(url: str) -> Dict[str, str]:
    """Importe une annonce depuis une URL (mode assisté).

    Retourne un dict compatible avec OfferFormDialog.set_prefill_data().
    Ne sauvegarde rien en base.
    """

    if not url:
        raise UrlImportError("URL vide")

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise UrlImportError("URL invalide")

    # Normalisation (évite les URL sans schéma / trailing issues)
    normalized_url = urlunparse(parsed)
    url = normalized_url

    html, final_url = _fetch_html(url)

    # First try with requests
    try:
        data = _parse_offer_html(html=html, url=url, final_url=final_url)
    except UrlImportError as exc:
        # For Jobup detail URLs, requests may return a SEO/listing shell.
        if HAS_PLAYWRIGHT and _domain_is_jobup(urlparse(final_url or url).netloc) and _is_probable_detail_url(final_url or url):
            html, final_url = _fetch_html_playwright(url)
            return _parse_offer_html(html=html, url=url, final_url=final_url)
        raise

    # If it looks like a Jobup detail URL but we still didn't get detail data, retry with Playwright.
    if HAS_PLAYWRIGHT and _domain_is_jobup(data.get("source_site", "")) and _is_probable_detail_url(data.get("source_url", "") or url):
        if (not data.get("_has_detail")) and (not data.get("_has_jobposting")):
            try:
                html, final_url = _fetch_html_playwright(url)
                return _parse_offer_html(html=html, url=url, final_url=final_url)
            except Exception:
                # Keep the requests result if browser fetch fails
                return data

    return data


def import_offer_from_url_browser(url: str) -> Dict[str, str]:
    """Importe une annonce via un navigateur headless (Playwright).

    Utile quand `requests` récupère une page SEO/liste au lieu du détail (Jobup, sites JS, consentement, etc.).
    """
    if not HAS_PLAYWRIGHT:
        raise UrlImportError(
            "Playwright n'est pas installé. Installation:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )

    if not url:
        raise UrlImportError("URL vide")

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise UrlImportError("URL invalide")

    url = urlunparse(parsed)

    html, final_url = _fetch_html_playwright(url)
    return _parse_offer_html(html=html, url=url, final_url=final_url)


def _parse_offer_html(*, html: str, url: str, final_url: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    # Collecte brute (debug / amélioration du pré-remplissage)
    og_raw = _collect_opengraph_raw(soup)
    jsonld_raw = _collect_jsonld_raw(soup)

    data: Dict[str, str] = {}
    data["_has_jobposting"] = False
    data["_has_detail"] = False

    data["url"] = url
    data["source_url"] = final_url or url
    data["source_site"] = urlparse(final_url or url).netloc.lower()
    data["source"] = _humanize_domain(data["source_site"])

    # 1) OpenGraph
    _extract_opengraph(soup, data)

    # 2) JSON-LD JobPosting
    _extract_json_ld_jobposting(soup, data)

    # 2bis) Jobup: le détail peut être présent sans JSON-LD JobPosting, et OG/<title> peuvent rester SEO.
    if _domain_is_jobup(data.get("source_site", "")):
        _extract_jobup_detail_from_page(soup, data)

    # Si on n'a pas de JobPosting ni de détail, il est très probable qu'on soit sur une page de liste,
    # une page SEO, un shell JS ou une page consentement. On évite de remplir avec du faux.
    if (not data.get("_has_jobposting")) and (not data.get("_has_detail")) and _looks_like_listing_or_shell(soup, data):
        dump_path = _write_import_dump_txt(
            url=url,
            html=html,
            og_raw=og_raw,
            jsonld_raw=jsonld_raw,
            data=data,
            soup=soup,
        )
        data["_dump_path"] = str(dump_path)
        raise UrlImportError(
            "Je n'ai pas récupéré une page 'détail d'annonce' (probablement une liste, une page SEO, "
            "une page de consentement ou un contenu chargé en JavaScript). "
            "Essaie avec une URL de détail d'annonce (pas une liste) ou utilise le mode navigateur intégré. "
            f"Dump: {dump_path}"
        )

    # Description: JSON-LD > OG > texte visible
    if not data.get("texte_annonce"):
        og_desc = data.get("_og_description", "")
        if isinstance(og_desc, str) and og_desc.strip():
            data["texte_annonce"] = og_desc.strip()

    # 3) Fallbacks
    if not data.get("titre_poste"):
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        data["titre_poste"] = _clean_title(title)

    if not data.get("texte_annonce"):
        targeted = _extract_targeted_job_text(soup)
        data["texte_annonce"] = targeted or _extract_visible_text(soup)

    dump_path = _write_import_dump_txt(
        url=url,
        html=html,
        og_raw=og_raw,
        jsonld_raw=jsonld_raw,
        data=data,
        soup=soup,
    )
    data["_dump_path"] = str(dump_path)

    return data


# ---------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------

def _fetch_html(url: str) -> tuple[str, str]:
    """Fetch HTML with a shared session.

    Some job boards intermittently block/slow down requests. We retry a bit and
    surface a clearer message so the UI can propose the Playwright fallback.
    """
    last_exc: Exception | None = None

    for attempt in range(3):
        try:
            resp = SESSION.get(
                url,
                headers=DEFAULT_HEADERS,
                timeout=TIMEOUT,
                allow_redirects=True,
            )

            # Common soft-block codes on job boards
            if resp.status_code in {403, 429}:
                raise UrlImportError(
                    f"Accès bloqué (HTTP {resp.status_code}). "
                    "Le site peut nécessiter un navigateur (JavaScript / anti-bot). "
                    "Essaie le mode navigateur."
                )

            resp.raise_for_status()

            if not resp.encoding:
                resp.encoding = resp.apparent_encoding

            return resp.text, str(resp.url)
        except UrlImportError as exc:
            # Already a user-friendly message
            raise
        except Exception as exc:
            last_exc = exc
            # Tiny backoff (no sleep import: keep it simple)
            continue

    raise UrlImportError(f"Impossible de récupérer la page: {last_exc}")


# --- Jobup-specific helpers ---

def _is_probable_detail_url(url: str) -> bool:
    if not url:
        return False
    try:
        p = urlparse(url)
    except Exception:
        return False
    path = (p.path or "").lower()
    # Common patterns across job boards
    if "/detail/" in path or "/job/" in path or "/jobs/" in path:
        return True
    # Jobup detail URLs are typically /fr/emplois/detail/<uuid>/
    if "emplois" in path and "detail" in path:
        return True
    return False


def _fetch_html_playwright(url: str) -> tuple[str, str]:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(locale="fr-FR")
            page = context.new_page()
            page.set_extra_http_headers({"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"})
            page.goto(url, wait_until="networkidle", timeout=30000)
            # Laisse un court temps aux scripts pour hydrater les blocs
            page.wait_for_timeout(500)
            html = page.content()
            final_url = page.url
            context.close()
            browser.close()
            return html, final_url
    except Exception as exc:
        raise UrlImportError(f"Impossible de récupérer la page via navigateur (Playwright): {exc}")


# ---------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------

def _extract_opengraph(soup: BeautifulSoup, data: Dict[str, str]) -> None:
    """Extrait quelques champs OpenGraph utiles."""
    og_map = {
        "og:title": "titre_poste",
        # Description OG souvent marketing → on la stocke à part
        "og:description": "_og_description",
        "og:site_name": "source",
    }

    for meta in soup.find_all("meta"):
        prop = meta.get("property") or meta.get("name")
        if prop in og_map and meta.get("content"):
            key = og_map[prop]
            if not data.get(key):
                data[key] = meta["content"].strip()


def _extract_json_ld_jobposting(soup: BeautifulSoup, data: Dict[str, str]) -> None:
    """Extrait un éventuel schema.org JobPosting depuis le JSON-LD."""
    scripts = soup.find_all("script", type="application/ld+json")

    for script in scripts:
        try:
            payload = json.loads(script.string or "")
        except Exception:
            continue

        # payload peut être: dict, list, ou dict avec @graph
        if isinstance(payload, list):
            nodes = payload
        elif isinstance(payload, dict):
            if isinstance(payload.get("@graph"), list):
                nodes = payload.get("@graph") or []
            else:
                nodes = [payload]
        else:
            continue

        for node in nodes:
            if not isinstance(node, dict):
                continue

            t = node.get("@type")
            is_job = (t == "JobPosting") or (isinstance(t, list) and "JobPosting" in t)
            if not is_job:
                continue

            data["_has_jobposting"] = True

            if not data.get("titre_poste"):
                data["titre_poste"] = _as_text(node.get("title"))

            hiring = node.get("hiringOrganization") or {}
            if isinstance(hiring, dict) and not data.get("entreprise"):
                data["entreprise"] = _as_text(hiring.get("name"))

            # jobLocation peut être dict ou list
            loc = node.get("jobLocation")
            if isinstance(loc, list) and loc:
                loc = loc[0]
            if isinstance(loc, dict):
                addr = loc.get("address") or {}
                if isinstance(addr, dict) and not data.get("localisation"):
                    data["localisation"] = _as_text(addr.get("addressLocality"))

            if not data.get("type_contrat"):
                data["type_contrat"] = _as_text(node.get("employmentType"))

            desc = node.get("description")
            if desc:
                new_desc = _strip_html(_as_text(desc))
                if new_desc:
                    current = data.get("texte_annonce", "")
                    # Remplace si plus riche
                    if (not current) or (len(new_desc) > len(current)):
                        data["texte_annonce"] = new_desc


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _domain_prefers_browser(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    host = host.replace("www.", "")
    return host in {"jobup.ch"}


# --- Jobup-specific helpers ---

def _domain_is_jobup(source_site: str) -> bool:
    host = (source_site or "").lower().replace("www.", "")
    # allow passing a netloc directly
    host = host.split(":")[0]
    return host == "jobup.ch"


def _extract_jobup_detail_from_page(soup: BeautifulSoup, data: Dict[str, str]) -> None:
    """Tente d'extraire le détail d'annonce Jobup depuis le HTML rendu.

    Problème rencontré: Jobup peut servir une page qui contient une liste + le détail,
    et le texte aplati mélange tout. Ici on:
    - repère le bloc "Détails de l'annonce d'emploi" (en prenant la DERNIÈRE occurrence)
    - travaille sur un sous-texte borné jusqu'aux marqueurs de fin (Catégories / À propos / etc.)
    - extrait les champs de façon robuste par regex et par lignes.
    """

    marker = "Détails de l'annonce d'emploi"

    # 1) Trouver la dernière occurrence du marker (souvent celle du détail)
    candidates = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "span", "div", "section", "main", "article"]):
        txt = tag.get_text(" ", strip=True)
        if txt and marker in txt:
            candidates.append(tag)

    if not candidates:
        return

    marker_node = candidates[-1]

    # 2) Monter à un conteneur assez large
    container = (
        marker_node.find_parent(["main", "article", "section"])
        or marker_node.find_parent("div")
        or marker_node
    )

    # Texte multi-lignes pour faciliter l'extraction
    text = container.get_text("\n", strip=True)

    # 3) Borne le texte à partir du marker
    idx = text.find(marker)
    if idx == -1:
        return
    detail = text[idx:]

    # 4) Si "Infos sur l'emploi" n'est pas présent, ce n'est pas un détail fiable
    if "Infos sur l'emploi" not in detail:
        return

    # 5) Couper aux sections de fin typiques
    end_markers = [
        "Catégories:",
        "À propos de l'entreprise",
        "À propos de l’entreprise",
        "Voir le profil de l’entreprise",
        "Voir le profil de l'entreprise",
        "Signaler cette offre",
        "Signaler cette offre d'emploi",
        "Ouvrir dans un nouvel onglet",
    ]
    for mk in end_markers:
        if mk in detail:
            detail = detail.split(mk, 1)[0]
            break

    # Normalise
    detail = re.sub(r"\r", "", detail)
    detail = re.sub(r"\n{2,}", "\n", detail).strip()

    # 6) Extraire les KV (Infos sur l'emploi)
    def _kv(label: str) -> str:
        # Capture "Label : value" jusqu'au prochain label connu
        pattern = rf"{re.escape(label)}\s*:\s*(.+?)(?=\n(?:Date de publication|Taux d'activité|Type de contrat|Lieu de travail)\s*:|\n(?:Nous recherchons|Missions|Profil|Conditions|À propos)|\Z)"
        m = re.search(pattern, detail, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            return ""
        return re.sub(r"\s+", " ", m.group(1)).strip()

    loc = _kv("Lieu de travail")
    contrat = _kv("Type de contrat")

    if loc and not data.get("localisation"):
        data["localisation"] = loc
    if contrat and not data.get("type_contrat"):
        data["type_contrat"] = contrat

    # 7) Header (Titre + Entreprise) = lignes entre marker et "Infos sur l'emploi"
    header_block = detail.split("Infos sur l'emploi", 1)[0]
    header_block = header_block.replace(marker, " ")
    header_block = re.sub(
        r"\b(Postuler|Sauvegarder|Candidature simplifiée|Nouveau|Mis en avant)\b",
        " ",
        header_block,
        flags=re.IGNORECASE,
    )
    header_block = re.sub(r"\s{2,}", " ", header_block).strip()

    # Découpe en lignes (en conservant un fallback sur les mots)
    raw_lines = [ln.strip() for ln in header_block.split("\n") if ln.strip()]
    if not raw_lines:
        raw_lines = [" ".join(header_block.split()[:20]).strip()] if header_block else []

    # Nettoyage SEO
    def _is_seo(s: str) -> bool:
        s2 = s.lower()
        return ("offres d'emploi" in s2) or ("catégorie" in s2) or ("trouvées sur jobup" in s2)

    # Sur Jobup, la première ligne utile est souvent le titre
    title_candidate = ""
    company_candidate = ""

    for ln in raw_lines:
        if not title_candidate and not _is_seo(ln):
            title_candidate = ln
            continue
        if title_candidate and not company_candidate and not _is_seo(ln):
            # évite d'attraper la ville comme "entreprise"
            if not re.search(r"\b(Genève|Lausanne|Renens|Neuchâtel|Zürich|Basel|Bern|Bienne|Sion)\b", ln, flags=re.IGNORECASE):
                company_candidate = ln
            break

    # Si le titre contient déjà "Entreprise" collé, on essaie de séparer.
    if title_candidate and not company_candidate:
        # Pattern: "TITRE ... Entreprise ..." (souvent dans les dumps)
        parts = re.split(r"\s{2,}|\s+-\s+", title_candidate)
        if len(parts) >= 2:
            title_candidate = parts[0].strip()

    if title_candidate and not _is_seo(title_candidate):
        data["titre_poste"] = title_candidate

    if company_candidate and not data.get("entreprise"):
        data["entreprise"] = company_candidate

    # 8) Description: texte après les KV, en retirant les lignes KV elles-mêmes
    if not data.get("texte_annonce"):
        # On prend tout après "Lieu de travail" (dans le bloc détail) puis on nettoie.
        m_desc = re.search(r"Lieu de travail\s*:\s*.*?\n(.*)", detail, flags=re.IGNORECASE | re.DOTALL)
        desc_text = m_desc.group(1).strip() if m_desc else ""

        # Retire les lignes infos répétées
        desc_text = re.sub(r"\n(Date de publication|Taux d'activité|Type de contrat|Lieu de travail)\s*:\s*.*", " ", desc_text, flags=re.IGNORECASE)

        # Retire CTA résiduels
        desc_text = re.sub(r"\b(Postuler|Sauvegarder|Candidature simplifiée|Nouveau|Mis en avant)\b", " ", desc_text, flags=re.IGNORECASE)

        desc_text = re.sub(r"\s{2,}", " ", desc_text).strip()

        if len(desc_text) > 200:
            data["texte_annonce"] = desc_text[:8000]

    # 9) Marqueur de détail fiable
    titre = (data.get("titre_poste") or "").strip().lower()
    if data.get("texte_annonce") and len(data.get("texte_annonce", "")) > 200 and titre and ("offres d'emploi" not in titre):
        data["_has_detail"] = True


def _looks_like_listing_or_shell(soup: BeautifulSoup, data: Dict[str, str]) -> bool:
    """Heuristique: détecte une page qui n'est pas un détail d'annonce."""
    if data.get("_has_detail"):
        return False
    title = (soup.title.string.strip() if soup.title and soup.title.string else "").lower()

    # Titres typiques de pages liste/catégorie (Jobup & autres)
    listing_markers = [
        "offres d'emploi",
        "offres emploi",
        "jobs",
        "job",
        "catégorie",
        "recherche",
        "search",
        "result",
        "résultats",
    ]

    # Meta OG très générique (SEO) : souvent pas une annonce
    og_desc = (data.get("_og_description") or "").lower()
    generic_markers = ["trouvez", "découvrez", "postulez", "emploi", "jobup", "annonces"]

    if any(m in title for m in listing_markers):
        return True

    # JSON-LD présent mais pas JobPosting: souvent BreadcrumbList/Website
    if soup.find("script", attrs={"type": "application/ld+json"}) and not data.get("_has_jobposting"):
        # si la description OG est marketing, on considère que ce n'est pas fiable
        if og_desc and sum(1 for m in generic_markers if m in og_desc) >= 2:
            return True

    return False


def _extract_targeted_job_text(soup: BeautifulSoup) -> str:
    """Essaie d'extraire la description depuis des conteneurs 'détail d'annonce'.

    On reste générique (pas spécifique à un site) et on évite de prendre toute la page.
    """
    selectors = [
        "main",
        "article",
        "[role='main']",
        "#job-description",
        "#jobDescription",
        "#description",
        ".job-description",
        ".jobDescription",
        ".description",
        ".offer-description",
        ".offerDescription",
        ".job-ad",
        ".jobad",
        ".content",
        ".details",
    ]

    best = ""
    for sel in selectors:
        try:
            node = soup.select_one(sel)
        except Exception:
            node = None
        if not node:
            continue

        # Nettoyage local
        for tag in node(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()

        txt = node.get_text(" ", strip=True)
        if txt and len(txt) > len(best):
            best = txt

    # On limite pour ne pas remplir le champ avec trop de bruit
    return best[:8000] if best else ""


def _collect_opengraph_raw(soup: BeautifulSoup) -> Dict[str, str]:
    """Récupère toutes les meta OpenGraph/Twitter utiles (brut)."""
    out: Dict[str, str] = {}
    for meta in soup.find_all("meta"):
        key = meta.get("property") or meta.get("name")
        val = meta.get("content")
        if not key or not val:
            continue
        # On garde OG + Twitter + description/keywords classiques
        if key.startswith("og:") or key.startswith("twitter:") or key in {"description", "keywords"}:
            if key not in out:
                out[key] = val.strip()
    return out


def _collect_jsonld_raw(soup: BeautifulSoup) -> list[str]:
    """Récupère le contenu brut des scripts JSON-LD."""
    raws: list[str] = []
    for script in soup.find_all("script", type="application/ld+json"):
        txt = script.string
        if txt and txt.strip():
            raws.append(txt.strip())
    return raws


def _write_import_dump_txt(*, url: str, html: str, og_raw: Dict[str, str], jsonld_raw: list[str], data: Dict[str, str], soup: BeautifulSoup) -> Path:
    """Écrit un fichier .txt avec tout ce qu'on arrive à extraire.

    Objectif: diagnostiquer pourquoi le pré-remplissage n'est pas fidèle.
    """
    dumps_dir = Path.cwd() / "imports_debug"
    dumps_dir.mkdir(parents=True, exist_ok=True)

    domain = urlparse(url).netloc.replace(":", "_") or "unknown"
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = dumps_dir / f"import_{domain}_{ts}.txt"

    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    def w(line: str = ""):
        f.write(line + "\n")

    with path.open("w", encoding="utf-8") as f:
        w("CV Manager – Import debug dump")
        w(f"URL: {url}")
        w(f"Date: {datetime.now().isoformat(timespec='seconds')}")
        w(f"Title: {title}")
        w(f"HTML length: {len(html)}")
        w("")

        w("=== EXTRACTED FIELDS (prefill data) ===")
        for k in sorted(data.keys()):
            # Ne pas afficher le texte complet en double si énorme
            v = data.get(k, "")
            if k == "texte_annonce" and isinstance(v, str) and len(v) > 1200:
                w(f"{k}: {v[:1200]}… (len={len(v)})")
            else:
                w(f"{k}: {v}")
        w("")

        w("=== OPENGRAPH / TWITTER METAS (raw) ===")
        if og_raw:
            for k in sorted(og_raw.keys()):
                w(f"{k}: {og_raw[k]}")
        else:
            w("(none)")
        w("")

        w("=== JSON-LD SCRIPTS (raw) ===")
        if jsonld_raw:
            for i, raw in enumerate(jsonld_raw, start=1):
                w(f"--- JSON-LD #{i} ---")
                w(raw)
                w("")
        else:
            w("(none)")
        w("")

        w("=== VISIBLE TEXT (first 5000 chars) ===")
        parsed_soup = BeautifulSoup(html, "html.parser")
        targeted = _extract_targeted_job_text(parsed_soup)
        if targeted:
            w("(targeted) " + targeted)
        else:
            w(_extract_visible_text(parsed_soup))

    return path


def _as_text(value) -> str:
    """Convertit une valeur JSON-LD (str/list/dict) en texte sûr."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for v in value:
            t = _as_text(v)
            if t:
                parts.append(t)
        return ", ".join(parts)
    if isinstance(value, dict):
        if "name" in value:
            return _as_text(value.get("name"))
        return str(value)
    return str(value).strip()


def _humanize_domain(domain: str) -> str:
    return domain.replace("www.", "").split(":")[0]


def _clean_title(title: str) -> str:
    if not title:
        return ""
    title = re.sub(r"\s+[-|–•].*$", "", title)
    return title.strip()


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(" ", strip=True)


def _extract_visible_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)
    return text[:5000]
