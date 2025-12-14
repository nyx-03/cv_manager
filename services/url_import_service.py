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

    # Si la page ressemble à une liste/shell JS sur des domaines connus, on tentera Playwright
    if HAS_PLAYWRIGHT and _domain_prefers_browser(final_url or url):
        try:
            parsed_probe = BeautifulSoup(html, "html.parser")
            probe_data: Dict[str, str] = {"_has_jobposting": False}
            _extract_opengraph(parsed_probe, probe_data)
            _extract_json_ld_jobposting(parsed_probe, probe_data)
            if not probe_data.get("_has_jobposting") and _looks_like_listing_or_shell(parsed_probe, probe_data):
                html, final_url = _fetch_html_playwright(url)
        except Exception:
            # On garde la version requests si Playwright échoue
            pass

    return _parse_offer_html(html=html, url=url, final_url=final_url)


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

def _fetch_html(url: str) -> tuple[str, str]:
    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.text, str(resp.url)
    except Exception as exc:
        raise UrlImportError(f"Impossible de récupérer la page: {exc}")


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
    return host == "jobup.ch"


def _extract_jobup_detail_from_page(soup: BeautifulSoup, data: Dict[str, str]) -> None:
    """Tente d'extraire le détail d'annonce Jobup depuis le HTML rendu.

    Objectif: éviter les faux positifs (page liste/SEO) et remplir correctement:
    - titre_poste
    - entreprise
    - localisation
    - type_contrat
    - texte_annonce

    Stratégie:
    1) On cherche le bloc texte qui contient "Détails de l'annonce d'emploi".
    2) On s'appuie d'abord sur la section "Infos sur l'emploi" (Lieu/Contrat/...) qui apparaît sur la page détail.
    3) On extrait ensuite un header court avant cette section et on le nettoie (CTA, doublons).
    """

    full_text = soup.get_text(" ", strip=True)
    marker = "Détails de l'annonce d'emploi"
    idx = full_text.find(marker)
    if idx == -1:
        return

    detail = full_text[idx:]

    # Si la section "Infos sur l'emploi" n'est pas présente, c'est souvent une page liste.
    if "Infos sur l'emploi" not in detail:
        return

    # --- Champs structurés depuis la section "Infos sur l'emploi" ---
    if not data.get("type_contrat"):
        m = re.search(r"Type de contrat\s*:\s*([^\n\r]+?)(?:\s+Lieu de travail\s*:|\s+Taux d'activité\s*:|\s+Nous recherchons|\s+Missions|\s+Profil|\s+Conditions|\s+À propos)", detail)
        if m:
            data["type_contrat"] = m.group(1).strip()

    if not data.get("localisation"):
        m = re.search(r"Lieu de travail\s*:\s*([^\n\r]+?)(?:\s+Taux d'activité\s*:|\s+Type de contrat\s*:|\s+Nous recherchons|\s+Missions|\s+Profil|\s+Conditions|\s+À propos)", detail)
        if m:
            data["localisation"] = m.group(1).strip()

    # --- Header: on prend le texte entre le marker et "Infos sur l'emploi" ---
    header = detail.split("Infos sur l'emploi", 1)[0]
    if header.startswith(marker):
        header = header[len(marker):].strip()

    # Nettoyage: CTA / badges
    header = re.sub(r"\b(Postuler|Sauvegarder|Signaler cette offre d'emploi|Ouvrir dans un nouvel onglet)\b", " ", header)
    header = re.sub(r"\b(Candidature simplifiée|Nouveau|Mis en avant)\b", " ", header)
    header = re.sub(r"\s{2,}", " ", header).strip()

    # Le header peut contenir des doublons (titre+entreprise répétés). On essaye de réduire.
    # On garde uniquement les ~30 premiers mots (avant que ça parte en SEO ou navigation).
    words = header.split()
    header_short = " ".join(words[:30]).strip()

    # Heuristique entreprise (suffixes courants). On capture la dernière occurrence plausible.
    company = data.get("entreprise", "") or ""
    title = data.get("titre_poste", "") or ""

    # Liste de suffixes typiques pour entreprises suisses/intl.
    suffixes = r"(?:SA|AG|Sàrl|SARL|GmbH|Ltd|Inc|LLC|Co\.|S\.A\.|S\.A)"

    m_company = re.search(rf"(.+?)\b({suffixes})\b", header_short, flags=re.IGNORECASE)
    if m_company:
        # Entreprise = groupe(1)+suffixe, titre = avant l'entreprise
        company_candidate = (m_company.group(1).strip() + " " + m_company.group(2).strip()).strip()
        before = header_short[: m_company.start()].strip()
        # Si le "before" est vide, on ne force pas le titre.
        if company_candidate and not company:
            company = company_candidate
        if before and not title:
            title = before

    # Fallback: si pas de suffixe, on tente de prendre le dernier bloc "Ville de ..." / "Fondation ..." etc.
    if not company:
        m2 = re.search(r"\b(Ville de|Canton de|Fondation|Association|Groupe)\b.*$", header_short)
        if m2:
            company = header_short[m2.start():].strip()
            if not title:
                title = header_short[: m2.start()].strip()

    # Fallback final: si on n'a rien, on utilise la première ligne plausible.
    if not title:
        # On évite les titres SEO
        candidate = header_short
        if candidate and ("offres d'emploi" not in candidate.lower()):
            title = candidate

    # Nettoyage des titres anormaux (souvent issus de la page liste)
    if title and ("offres d'emploi" in title.lower() or "catégorie" in title.lower()):
        title = ""

    if title and not data.get("titre_poste"):
        data["titre_poste"] = title
    elif title:
        data["titre_poste"] = title

    if company and not data.get("entreprise"):
        data["entreprise"] = company

    # --- Description: prendre le bloc après "Lieu de travail" et avant "À propos" ---
    if not data.get("texte_annonce"):
        m_desc = re.search(r"Lieu de travail\s*:\s*[^\n\r]+\s+(.*)", detail)
        if m_desc:
            desc = m_desc.group(1)
            end_markers = [
                "À propos de l'entreprise",
                "À propos de l’entreprise",
                "Catégories:",
                "Ouvrir dans un nouvel onglet",
                "Signaler cette offre",
            ]
            for mk in end_markers:
                if mk in desc:
                    desc = desc.split(mk, 1)[0]
                    break

            # Nettoyage des répétitions de champs "Infos sur l'emploi" dans le texte
            desc = re.sub(r"\b(Date de publication\s*:\s*[^\n\r]+)\b", " ", desc)
            desc = re.sub(r"\b(Taux d'activité\s*:\s*[^\n\r]+)\b", " ", desc)
            desc = re.sub(r"\b(Type de contrat\s*:\s*[^\n\r]+)\b", " ", desc)
            desc = re.sub(r"\b(Lieu de travail\s*:\s*[^\n\r]+)\b", " ", desc)

            desc = re.sub(r"\s{2,}", " ", desc).strip()
            if len(desc) > 200:
                data["texte_annonce"] = desc[:8000]

    # Marqueur: si on a une description correcte et un titre plausible, on considère qu'on est sur une page détail.
    titre = (data.get("titre_poste") or "").lower()
    if data.get("texte_annonce") and titre and ("offres d'emploi" not in titre):
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
