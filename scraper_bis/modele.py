"""Structures échangées entre les étapes du pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class FicheBrute:
    """Ce que la collecte rapporte, avant toute interprétation."""

    marque: str
    nom: str
    categorie: str
    specs: dict[str, str]
    variante: str = ""
    gamme: str = ""
    sous_categorie: str = ""
    description: str = ""
    source_url: str = ""
    methode: str = "CRAWL_HTML"  # ou EXTRACTION_PDF
    image_url: str = ""
    statut: str = "active"

    def cle(self) -> str:
        return f"{self.marque}|{self.nom}|{self.variante}"


@dataclass
class Proposition:
    """Une valeur extraite pour une colonne, avec sa preuve."""

    champ: str
    valeur: object
    extrait: str
    confiance: float
    methode: str = "regles"  # ou "llm"


@dataclass
class FicheExtraite:
    brute: FicheBrute
    categorie_nom: str
    famille: str | None
    motorise: bool
    tracteur: bool
    champs: dict[str, object] = field(default_factory=dict)
    propositions: list[Proposition] = field(default_factory=list)
    non_reconnus: list[str] = field(default_factory=list)
    ecartes: list[str] = field(default_factory=list)  # valeurs lues mais rejetées (hors bornes, ambiguës)

    def en_dict(self) -> dict:
        d = asdict(self)
        d["cle"] = self.brute.cle()
        return d
