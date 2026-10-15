"""Lecture des nombres et des unités dans les valeurs brutes des fiches.

Exemples gérés : « 180-320ch », « 3.00m - 4.00m - 5.00m », « 90-175 kW / 120-240 Ch »,
« 13,6 t », « 650 l à 1 730 l », « jusqu'à 8800 kg », « ~8 tonnes », « 2,9-3,5m ».
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Unités reconnues → (dimension, facteur vers l'unité de référence de la dimension)
UNITES: dict[str, tuple[str, float]] = {
    "ch": ("puissance", 1.0),
    "cv": ("puissance", 1.0),
    "ps": ("puissance", 1.0),
    "hp": ("puissance", 1.01387),
    "kw": ("puissance", 1.35962),
    "kg": ("masse", 1.0),
    "t": ("masse", 1000.0),
    "tonne": ("masse", 1000.0),
    "tonnes": ("masse", 1000.0),
    "m": ("longueur", 1.0),
    "cm": ("longueur", 0.01),
    "mm": ("longueur", 0.001),
    "km/h": ("vitesse", 1.0),
    "l/min": ("debit", 1.0),
    "%": ("pourcentage", 1.0),
    "tr/min": ("regime", 1.0),
    "rpm": ("regime", 1.0),
    "l": ("volume", 1.0),
}

# Quand plusieurs unités d'une même dimension coexistent (« 107 kW / 150 ch »),
# on garde la première de cette liste : évite de compter deux fois la même valeur.
PREFERENCE = {
    "puissance": ["ch", "cv", "ps", "hp", "kw"],
    "masse": ["kg", "t", "tonne", "tonnes"],
    "longueur": ["m", "cm", "mm"],
}

_NOMBRE = r"(\d{1,3}(?:[   ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
_UNITE = r"(km/h|l/min|tr/min|tonnes|tonne|kw|kg|mm|cm|ch|cv|hp|ps|rpm|m|l|t|%)"
_JETON = re.compile(_NOMBRE + r"\s*(?:" + _UNITE + r"(?![\w³²]))?", re.IGNORECASE)
# Séparateurs de plage entre deux nombres : la 2e unité s'applique au 1er nombre
_LIEN_PLAGE = re.compile(r"^\s*(?:-|–|à|a|to|et|ou|,|/)?\s*$", re.IGNORECASE)


@dataclass
class Jeton:
    valeur: float
    unite: str | None
    debut: int
    fin: int


def _nombre(texte: str) -> float:
    return float(re.sub(r"[   ]", "", texte).replace(",", "."))


def jetons(texte: str) -> list[Jeton]:
    """Nombres trouvés dans le texte, avec leur unité (propagée dans les plages)."""
    texte = texte or ""
    # « 9'1" (2.7 m) », « 2 425 lbs (1 100 kg) » : la valeur métrique est entre parenthèses
    if re.search(r"\d\s*['\"′″]|\blbs?\b|\bft\b", texte) and "(" in texte:
        texte = " ".join(re.findall(r"\(([^)]*)\)", texte))
    propre = re.sub(r"\([^)]*\)", " ", texte)  # « 121 (89) », « 110 l/min (load sensing) »
    res = [
        Jeton(_nombre(m.group(1)), (m.group(2) or "").lower() or None, m.start(), m.end())
        for m in _JETON.finditer(propre)
    ]
    # « 70-140 ch » : l'unité du 2e nombre vaut aussi pour le 1er
    for i in range(len(res) - 2, -1, -1):
        if res[i].unite is None and res[i + 1].unite and _LIEN_PLAGE.match(propre[res[i].fin : res[i + 1].debut]):
            res[i].unite = res[i + 1].unite
    return res


def valeurs(texte: str, dimension: str, unite_par_defaut: str | None = None) -> list[float]:
    """Valeurs du texte dans l'unité de référence de la dimension.

    Les nombres sans unité prennent `unite_par_defaut` (indice du libellé, ex. « Poids (kg) »).
    """
    toks = jetons(texte)
    candidats: dict[str, list[float]] = {}
    for t in toks:
        u = t.unite or unite_par_defaut
        if not u or u not in UNITES or UNITES[u][0] != dimension:
            continue
        candidats.setdefault(u, []).append(t.valeur)
    if not candidats:
        return []
    ordre = PREFERENCE.get(dimension, list(candidats))
    unite = next((u for u in ordre if u in candidats), next(iter(candidats)))
    facteur = UNITES[unite][1]
    return [round(v * facteur, 4) for v in candidats[unite]]


def unite_du_libelle(libelle: str) -> str | None:
    """« Poids (kg) » → « kg », « Largeur de travail (m) » → « m »."""
    m = re.search(r"\(\s*([^)]+?)\s*\)", libelle or "")
    if not m:
        return None
    u = m.group(1).lower().replace(" ", "")
    return u if u in UNITES else None
