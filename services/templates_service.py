from pathlib import Path
from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape

from models import ProfilCandidat, Offre

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
GENERATED_DIR = BASE_DIR / "generated" / "lettres_html"

env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(enabled_extensions=("html",)),
    trim_blocks=True,
    lstrip_blocks=True,
)

def ensure_generated_dirs():
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def render_lettre_candidature_html(
    profil: ProfilCandidat,
    offre: Offre,
    template_name: str = "lettre_modern.html.j2",
) -> Path:
    """
    Génère une lettre de motivation HTML basée sur le template graphique.
    Retourne le chemin du fichier .html généré.
    """
    ensure_generated_dirs()

    template = env.get_template(template_name)

    # Texte par défaut – tu pourras affiner plus tard, voire adapter selon l'offre
    paragraphe_intro = (
        f"Développeur Python passionné par les données, l'automatisation et la fiabilité "
        f"des systèmes, je souhaite vous proposer ma candidature au poste de {offre.titre_poste} "
        f"au sein de {offre.entreprise or 'votre entreprise'}."
    )

    paragraphe_exp1 = (
        "J’ai acquis une solide expérience dans la construction et l’optimisation de pipelines "
        "de données, l'automatisation via Python et l'exploitation d'environnements modernes. "
        "Je porte une attention particulière à la fiabilité en production, au monitoring "
        "proactif et à la traçabilité des traitements."
    )

    paragraphe_exp2 = (
        "Je maîtrise SQL, Python, le scripting, et je suis à l’aise avec les architectures "
        "orientées données ainsi que les environnements cloud. J’apprécie mettre en place "
        "des chaînes d’intégration et de déploiement continues (CI/CD) robustes, permettant "
        "des livraisons maîtrisées et reproductibles."
    )

    paragraphe_poste = (
        "Votre poste m’intéresse particulièrement pour son rôle central dans l’écosystème data : "
        "travailler en étroite collaboration avec les équipes techniques et métier, tout en "
        "garantissant la qualité et la fiabilité des solutions livrées. Cette transversalité "
        "correspond pleinement à ma manière de travailler."
    )

    paragraphe_personnalite = (
        "Curieux, autonome et orienté solution, je m’investis dans l’amélioration continue : "
        "bonnes pratiques, performance, documentation et simplification des workflows. "
        "Mon expérience d’entrepreneur m’a appris à gérer plusieurs priorités simultanément "
        "et à proposer des solutions pragmatiques, adaptées aux besoins des utilisateurs."
    )

    paragraphe_conclusion = (
        "Je serais heureux de pouvoir échanger avec vous au sujet de mes compétences, de mes projets "
        "et de la manière dont je pourrais contribuer à vos activités. "
        "Je reste à votre disposition pour un entretien."
    )

    ctx = {
        "profil": profil,
        "offre": offre,
        "date_du_jour": date.today().strftime("%d/%m/%Y"),
        "tagline": "Data pipelines · Python · Automatisation · CI/CD",
        "badge_text": "Python · SQL · Automatisation · Pipelines CI/CD",
        "reference": None,          # à terme, tu peux ajouter un champ ref dans Offre
        "lieu_entreprise": offre.localisation or "",
        "paragraphe_intro": paragraphe_intro,
        "paragraphe_exp1": paragraphe_exp1,
        "paragraphe_exp2": paragraphe_exp2,
        "paragraphe_poste": paragraphe_poste,
        "paragraphe_personnalite": paragraphe_personnalite,
        "paragraphe_conclusion": paragraphe_conclusion,
    }

    rendered_html = template.render(**ctx)

    filename = f"lettre_offre_{offre.id}.html"
    output_path = GENERATED_DIR / filename
    output_path.write_text(rendered_html, encoding="utf-8")

    return output_path