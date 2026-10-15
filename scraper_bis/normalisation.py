"""Libellés, catégories et familles, alignés sur le site (lib/machine-catalogue.ts)."""

from __future__ import annotations

import re
import unicodedata


def sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texte or "") if unicodedata.category(c) != "Mn")


def slug(texte: str) -> str:
    """Même règle que slug() côté site : sert de code de catégorie."""
    s = sans_accents(texte).lower().replace("&", " et ")
    return re.sub(r"^_+|_+$", "", re.sub(r"[^a-z0-9]+", "_", s))


def libelle_normalise(libelle: str) -> str:
    """« Puissance mini/maxi (ch) » → « puissance mini maxi »."""
    s = re.sub(r"\([^)]*\)", " ", libelle or "")
    s = sans_accents(s).lower().replace("'", " ").replace("’", " ")
    s = re.sub(r"[^a-z0-9%]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Même ordre et mêmes mots-clés que familleDepuisLibelle() côté site, complétés
# des formes au singulier vues dans les données collectées.
FAMILLE_PAR_MOT_CLE = [
    ("tracteur", "TRACTION"),
    ("recolte", "RECOLTE"),
    ("moissonneuse", "RECOLTE"),
    ("ensileuse", "RECOLTE"),
    ("arracheuse", "RECOLTE"),
    ("semis", "SEMIS_PLANTATION"),
    ("semoir", "SEMIS_PLANTATION"),
    ("planteuse", "SEMIS_PLANTATION"),
    ("pulveris", "PROTECTION_CULTURES"),
    ("bineuse", "PROTECTION_CULTURES"),
    ("desherbage", "PROTECTION_CULTURES"),
    ("protection des cultures", "PROTECTION_CULTURES"),
    ("travail du sol", "TRAVAIL_DU_SOL"),
    ("charrue", "TRAVAIL_DU_SOL"),
    ("dechaumeur", "TRAVAIL_DU_SOL"),
    ("herse", "TRAVAIL_DU_SOL"),
    ("rouleau", "TRAVAIL_DU_SOL"),
    ("cultivateur", "TRAVAIL_DU_SOL"),
    ("combine", "TRAVAIL_DU_SOL"),
    ("epandage", "FERTILISATION"),
    ("epandeur", "FERTILISATION"),
    ("fertilisation", "FERTILISATION"),
    ("distributeur d engrais", "FERTILISATION"),
    ("fenaison", "FENAISON"),
    ("presse", "FENAISON"),
    ("faucheuse", "FENAISON"),
    ("fauche", "FENAISON"),
    ("faneu", "FENAISON"),
    ("andain", "FENAISON"),
    ("enrubann", "FENAISON"),
    ("elevage", "ELEVAGE"),
    ("distribution", "ELEVAGE"),
    ("melangeuse", "ELEVAGE"),
    ("desileuse", "ELEVAGE"),
    ("pailleuse", "ELEVAGE"),
    ("paillage", "ELEVAGE"),
    ("chargeur", "MANUTENTION"),
    ("telescopique", "MANUTENTION"),
    ("cour de ferme", "MANUTENTION"),
    ("remorqu", "TRANSPORT"),
    ("transport", "TRANSPORT"),
    ("benne", "TRANSPORT"),
    ("broy", "ENTRETIEN"),
    ("debroussaill", "ENTRETIEN"),
    ("deneigement", "ENTRETIEN"),
    ("paysage", "ENTRETIEN"),
    ("cultures specialisees", "CULTURES_SPECIALISEES"),
    ("irrigation", "CULTURES_SPECIALISEES"),
]


def famille(*libelles: str | None) -> str | None:
    """Famille de la catégorie, ou None si aucun mot-clé ne correspond."""
    texte = sans_accents(" ".join(x for x in libelles if x)).lower().replace("-", " ").replace("'", " ")
    for mot, fam in FAMILLE_PAR_MOT_CLE:
        if mot in texte:
            return fam
    return None


# Catégories du fichier Excel (singulier, minuscules) → noms du scraper (pluriel)
NOM_CATEGORIE = {
    "tracteur": "Tracteurs",
    "dechaumeur": "Déchaumeurs",
    "semoir": "Semoirs",
    "fenaison": "Fenaison",
    "presse": "Presses",
    "moissonneuse": "Moissonneuses",
    "bineuse": "Bineuses",
    "epandeur": "Épandeurs",
    "pulverisateur": "Pulvérisateurs",
    "chargeur": "Chargeurs",
    "charrue": "Charrues",
    "ensileuse": "Ensileuses",
    "broyeur": "Broyeurs",
    "telescopique": "Télescopiques",
    "faucheuse": "Fenaison",
    "autre": "Autre",
}


def nom_categorie(categorie: str | None) -> str:
    cle = sans_accents(categorie or "").lower().strip()
    if cle in NOM_CATEGORIE:
        return NOM_CATEGORIE[cle]
    propre = (categorie or "Autre").strip()
    return propre[:1].upper() + propre[1:]


MOTS_MOTORISES = ("tracteur", "moissonneuse", "ensileuse", "telescopique", "automoteur", "automotrice")
LIBELLES_MOTEUR = ("moteur", "cylindree", "cylindres", "reservoir carburant", "couple max", "boite de vitesses", "transmission")


def est_motorise(categorie: str | None, texte: str, libelles: list[str]) -> bool:
    """Tracteur ou automoteur : la puissance indiquée est celle du moteur, pas la puissance requise."""
    c = sans_accents(f"{categorie or ''} {texte}").lower()
    if any(m in c for m in MOTS_MOTORISES):
        return True
    return sum(1 for lib in libelles if any(lib.startswith(m) for m in LIBELLES_MOTEUR)) >= 2


def est_tracteur(categorie: str | None) -> bool:
    return "tracteur" in sans_accents(categorie or "").lower()
