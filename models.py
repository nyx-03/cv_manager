# models.py
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, Date, DateTime, Enum, Boolean
)
from sqlalchemy.orm import relationship
from db import Base
import enum
from datetime import datetime


class CompetenceCategorie(enum.Enum):
    TECHNIQUE = "technique"
    OUTIL = "outil"
    SOFT = "soft"
    AUTRE = "autre"


class CandidatureStatut(enum.Enum):
    A_PREPARER = "a_preparer"
    A_ENVOYER = "a_envoyer"
    ENVOYEE = "envoyee"
    RELANCE = "relance"
    ENTRETIEN = "entretien"
    REFUSEE = "refusee"
    ARCHIVEE = "archivee"

    def label(self):
        mapping = {
            CandidatureStatut.A_PREPARER: "À préparer",
            CandidatureStatut.A_ENVOYER: "À envoyer",
            CandidatureStatut.ENVOYEE: "Envoyée",
            CandidatureStatut.RELANCE: "Relance",
            CandidatureStatut.ENTRETIEN: "Entretien",
            CandidatureStatut.REFUSEE: "Refusée",
            CandidatureStatut.ARCHIVEE: "Archivée",
        }
        return mapping.get(self, self.value)


class ProfilCandidat(Base):
    __tablename__ = "profil_candidat"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    email = Column(String(200), nullable=False)
    telephone = Column(String(50), nullable=True)
    ville = Column(String(100), nullable=True)
    titre = Column(String(200), nullable=True)  # ex: "Développeur Python / Data"
    resume = Column(Text, nullable=True)
    lien_linkedin = Column(String(300), nullable=True)
    lien_github = Column(String(300), nullable=True)
    lien_portfolio = Column(String(300), nullable=True)

    experiences = relationship("Experience", back_populates="profil", cascade="all, delete-orphan")
    formations = relationship("Formation", back_populates="profil", cascade="all, delete-orphan")
    competences = relationship("Competence", back_populates="profil", cascade="all, delete-orphan")

    @property
    def linkedin(self):
        return self.lien_linkedin

    @linkedin.setter
    def linkedin(self, value):
        self.lien_linkedin = value

    @property
    def github(self):
        return self.lien_github

    @github.setter
    def github(self, value):
        self.lien_github = value

    @property
    def portfolio(self):
        return self.lien_portfolio

    @portfolio.setter
    def portfolio(self, value):
        self.lien_portfolio = value


class Experience(Base):
    __tablename__ = "experience"

    id = Column(Integer, primary_key=True)
    profil_id = Column(Integer, ForeignKey("profil_candidat.id"), nullable=False)

    entreprise = Column(String(200), nullable=False)
    poste = Column(String(200), nullable=False)
    lieu = Column(String(200), nullable=True)
    date_debut = Column(String(20), nullable=True)  # tu peux passer en Date si tu veux
    date_fin = Column(String(20), nullable=True)    # idem
    description = Column(Text, nullable=True)       # texte libre
    points_forts = Column(Text, nullable=True)      # éventuellement JSON plus tard

    profil = relationship("ProfilCandidat", back_populates="experiences")


class Formation(Base):
    __tablename__ = "formation"

    id = Column(Integer, primary_key=True)
    profil_id = Column(Integer, ForeignKey("profil_candidat.id"), nullable=False)

    ecole = Column(String(200), nullable=False)
    diplome = Column(String(200), nullable=False)
    date_debut = Column(String(20), nullable=True)
    date_fin = Column(String(20), nullable=True)
    details = Column(Text, nullable=True)

    profil = relationship("ProfilCandidat", back_populates="formations")


class Competence(Base):
    __tablename__ = "competence"

    id = Column(Integer, primary_key=True)
    profil_id = Column(Integer, ForeignKey("profil_candidat.id"), nullable=False)

    nom = Column(String(200), nullable=False)
    categorie = Column(Enum(CompetenceCategorie), nullable=False, default=CompetenceCategorie.TECHNIQUE)
    niveau = Column(String(50), nullable=True)  # "Débutant / Intermédiaire / Avancé / Expert"

    profil = relationship("ProfilCandidat", back_populates="competences")


class Offre(Base):
    __tablename__ = "offre"

    id = Column(Integer, primary_key=True)
    titre_poste = Column(String(200), nullable=False)
    entreprise = Column(String(200), nullable=True)
    source = Column(String(200), nullable=True)          # Jobup, LinkedIn, etc.

    # URL saisi/visible (historique) — on le garde pour compatibilité
    url = Column(String(500), nullable=True)

    # URL d'origine de l'annonce (pour import). Peut être identique à `url`.
    source_url = Column(String(500), nullable=True, index=True, unique=True)

    # Domaine/site d'origine (ex: "jobup.ch", "hellowork.com")
    source_site = Column(String(200), nullable=True, index=True)

    # Date d'ajout/import (utile pour tri/filtre)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    localisation = Column(String(200), nullable=True)
    type_contrat = Column(String(100), nullable=True)
    texte_annonce = Column(Text, nullable=True)          # texte collé

    candidatures = relationship("Candidature", back_populates="offre", cascade="all, delete-orphan")


class Candidature(Base):
    __tablename__ = "candidature"

    id = Column(Integer, primary_key=True)
    offre_id = Column(Integer, ForeignKey("offre.id"), nullable=False)

    date_envoi = Column(Date, nullable=True)
    statut = Column(Enum(CandidatureStatut), nullable=False, default=CandidatureStatut.A_PREPARER)
    chemin_cv = Column(String(500), nullable=True)       # chemin vers le fichier généré
    chemin_lettre = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)

    offre = relationship("Offre", back_populates="candidatures")


class TemplateCV(Base):
    __tablename__ = "template_cv"

    id = Column(Integer, primary_key=True)
    nom = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    type_sortie = Column(String(20), nullable=False, default="html")  # html, md, docx...
    chemin_fichier = Column(String(500), nullable=False)


class TemplateLettre(Base):
    __tablename__ = "template_lettre"

    id = Column(Integer, primary_key=True)
    nom = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    type_sortie = Column(String(20), nullable=False, default="md")
    chemin_fichier = Column(String(500), nullable=False)