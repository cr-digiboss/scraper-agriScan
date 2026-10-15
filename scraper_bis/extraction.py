"""Extraction par règles : specs brutes → colonnes techniques de Machine.

Chaque valeur retenue devient une Proposition (champ, valeur, extrait, confiance),
le format d'AttributProvenance. Les libellés non reconnus sont listés dans le
rapport pour enrichir les règles.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Callable

from .modele import FicheBrute, FicheExtraite, Proposition
from .normalisation import (
    est_motorise,
    est_tracteur,
    famille,
    libelle_normalise,
    nom_categorie,
    sans_accents,
)
from .unites import unite_du_libelle, valeurs

# Colonnes entières (les autres sont des décimaux)
ENTIERS = {
    "poidsVideKg", "ptacKg", "puissanceRequiseMinCh", "puissanceRequiseMaxCh",
    "puissanceMoteurCh", "regimePdf", "distributeursDERequis", "distributeursSERequis",
}

# Bornes de vraisemblance : au-delà, la valeur est écartée (unité mal lue, coquille…)
BORNES = {
    "largeurTravailMinM": (0.3, 60), "largeurTravailMaxM": (0.3, 60),
    "largeurTransportM": (0.5, 6), "hauteurTransportM": (0.5, 6), "longueurTransportM": (0.8, 30),
    "poidsVideKg": (20, 60000), "ptacKg": (100, 80000),
    "puissanceRequiseMinCh": (5, 1000), "puissanceRequiseMaxCh": (5, 1000), "puissanceMoteurCh": (10, 1200),
    "vitesseTravailMinKmh": (0.5, 60), "vitesseTravailMaxKmh": (0.5, 60), "vitesseMaxRouteKmh": (5, 80),
    "debitHydrauliqueRequisLmin": (5, 500), "penteMaxPct": (0, 100),
}

# Champs clés pour la recommandation (mêmes listes que lib/fiche-machine.ts)
CLES_TRACTEUR = ["puissanceMoteurCh", "poidsVideKg", "largeurTransportM", "normeAntipollution"]
CLES_AUTOMOTEUR = ["puissanceMoteurCh", "largeurTravailMinM", "largeurTransportM", "poidsVideKg"]
CLES_OUTIL = ["typeAttelage", "largeurTravailMinM", "puissanceRequiseMinCh", "largeurTransportM", "poidsVideKg"]


def champs_cles(f: FicheExtraite) -> list[str]:
    if f.tracteur:
        return CLES_TRACTEUR
    if f.champs.get("typeAttelage") == "AUTOMOTEUR" or f.motorise:
        return CLES_AUTOMOTEUR
    return CLES_OUTIL


# ── Règles ───────────────────────────────────────────────────────────────────


@dataclass
class Contexte:
    motorise: bool
    tracteur: bool


@dataclass
class Regle:
    motif: str  # expression régulière sur le libellé normalisé
    sorte: str  # plage | max | unique | attelage | norme | pdf | cat_attelage | distributeurs
    champs: tuple[str, ...]
    dimension: str | None = None
    unite: str | None = None  # unité par défaut si la valeur n'en a pas
    confiance: float = 0.9
    si: Callable[[Contexte], bool] = lambda c: True


OUTIL = lambda c: not c.motorise  # noqa: E731
MOTEUR = lambda c: c.motorise  # noqa: E731

REGLES: list[Regle] = [
    Regle(r"^(largeur de travail|largeur travail|largeur de coupe|largeur utile|largeur de travail utile|largeur de fauche|largeur de pick up|working width)\b",
          "plage", ("largeurTravailMinM", "largeurTravailMaxM"), "longueur", "m"),
    Regle(r"^largeur$", "plage", ("largeurTravailMinM", "largeurTravailMaxM"), "longueur", "m", 0.6, OUTIL),
    Regle(r"^(largeur de transport|largeur transport|largeur hors tout|largeur totale|largeur au transport|transport width)\b",
          "max", ("largeurTransportM",), "longueur", "m"),
    Regle(r"^largeur$", "max", ("largeurTransportM",), "longueur", "m", 0.6, MOTEUR),
    Regle(r"^(hauteur de transport|hauteur transport|hauteur hors tout|hauteur totale|hauteur au transport)\b",
          "max", ("hauteurTransportM",), "longueur", "m"),
    Regle(r"^hauteur$", "max", ("hauteurTransportM",), "longueur", "m", 0.6),
    Regle(r"^(longueur|longueur totale|longueur hors tout|longueur de transport|longueur au transport)$",
          "max", ("longueurTransportM",), "longueur", "m", 0.8),
    Regle(r"^(poids a vide|poids|poids total a vide|masse|poids de base|poids mini|poids a vide env|weight|masse en ordre de marche|poids en ordre de marche|poids de la machine)$",
          "unique", ("poidsVideKg",), "masse", "kg", 0.85),
    Regle(r"^(ptac|poids total autorise|poids total en charge|poids total admissible)\b",
          "unique", ("ptacKg",), "masse", "kg"),
    Regle(r"^(puissance requise|puissance necessaire|puissance tracteur|puissance tracteur requise|puissance mini maxi|puissance mini|besoin en puissance|besoin tracteur|tracteur requis|puissance tracteur mini|required power|puissance de traction|puissance du tracteur)\b",
          "plage", ("puissanceRequiseMinCh", "puissanceRequiseMaxCh"), "puissance", "ch"),
    Regle(r"^(puissance|puissance max|puissance maximale|puissance nominale|puissance moteur|puissance maxi|rated power|engine power|puissance brute|puissance nette|puissance nominale moteur)$",
          "unique", ("puissanceMoteurCh",), "puissance", "ch", 0.8, MOTEUR),
    Regle(r"^(puissance|puissance max|puissance maximale)$",
          "plage", ("puissanceRequiseMinCh", "puissanceRequiseMaxCh"), "puissance", "ch", 0.5, OUTIL),
    Regle(r"^(vitesse de travail|vitesse travail|vitesse d avancement|vitesse de semis|vitesse de travail conseillee)\b",
          "plage", ("vitesseTravailMinKmh", "vitesseTravailMaxKmh"), "vitesse", "km/h"),
    Regle(r"^(vitesse max|vitesse maximale|vitesse sur route|vitesse de transport|vitesse route|vitesse maxi)\b",
          "max", ("vitesseMaxRouteKmh",), "vitesse", "km/h", 0.85),
    Regle(r"^(debit hydraulique|debit hydraulique requis|besoin hydraulique|debit d huile)\b",
          "max", ("debitHydrauliqueRequisLmin",), "debit", "l/min", 0.7, OUTIL),
    Regle(r"^(type d attelage|attelage|type attelage|mode d attelage)$", "attelage", ("typeAttelage",), confiance=0.85),
    Regle(r"^(type|configuration|chassis|type de chassis|type de machine|version)$", "attelage", ("typeAttelage",), confiance=0.6),
    Regle(r"^(moteur|norme|norme antipollution|norme d emission|norme emissions|emissions|niveau d emission)\b",
          "norme", ("normeAntipollution",), confiance=0.85, si=MOTEUR),
    Regle(r"^(prise de force|pdf|regime pdf|regime de prise de force|pto|entrainement|regime d entrainement|vitesse pdf)\b",
          "pdf", ("regimePdf",), confiance=0.8, si=OUTIL),
    Regle(r"(attelage|categorie|cat )", "cat_attelage", ("categorieAttelage",), confiance=0.8, si=OUTIL),
    Regle(r"^(distributeurs?|distributeurs? requis|distributeurs? hydrauliques?|prises hydrauliques)\b",
          "distributeurs", ("distributeursDERequis", "distributeursSERequis"), confiance=0.7, si=OUTIL),
]

ATTELAGE_MOTS = [
    (r"semi[ -]?port|semi[ -]?mounted", "SEMI_PORTE"),
    (r"automot|self[ -]?propelled", "AUTOMOTEUR"),
    (r"train|trail|remorqu|tracte", "TRAINE"),
    (r"frontal|front", "FRONTAL"),
    (r"\bport|mounted|3 points", "PORTE"),
]

NORME = re.compile(r"(stage\s*(?:v|iv|iiib|iiia|3b|3a|5|4)\b|tier\s*(?:4\s*final|4f|4i|4|3|2)\b)", re.IGNORECASE)
CAT_ATTELAGE = re.compile(r"cat(?:egorie|\.)?\s*(iv|iii|ii|i|[1-4])\s*(n)?\b", re.IGNORECASE)
ROMAIN = {"i": "1", "ii": "2", "iii": "3", "iv": "4"}


def _borner(champ: str, v: float) -> float | None:
    lo, hi = BORNES.get(champ, (float("-inf"), float("inf")))
    if not lo <= v <= hi:
        return None
    return int(round(v)) if champ in ENTIERS else round(v, 2)


def _appliquer(regle: Regle, libelle: str, valeur: str) -> tuple[dict[str, object], str | None]:
    """Valeurs proposées par une règle, ou une raison d'écart."""
    brut = sans_accents(valeur).lower()
    if regle.sorte in ("plage", "max", "unique"):
        nombres = valeurs(valeur, regle.dimension, unite_du_libelle(libelle) or regle.unite)
        if not nombres:
            return {}, None
        if regle.sorte == "plage":
            seulement_max = bool(re.search(r"jusqu|max|<", brut)) and len(nombres) == 1
            seulement_min = bool(re.search(r"partir|min|>|des ", brut)) and len(nombres) == 1
            res: dict[str, object] = {}
            if not seulement_max:
                res[regle.champs[0]] = min(nombres)
            if not seulement_min:
                res[regle.champs[1]] = max(nombres)
        elif regle.sorte == "max":
            res = {regle.champs[0]: max(nombres)}
        else:
            distincts = sorted(set(nombres))
            if len(distincts) > 1 and distincts[-1] > distincts[0] * 1.05:
                return {}, f"{libelle} : plusieurs valeurs ({valeur})"
            res = {regle.champs[0]: distincts[0]}
        bornes = {c: _borner(c, float(v)) for c, v in res.items()}
        hors = [c for c, v in bornes.items() if v is None]
        if hors:
            return {}, f"{libelle} : valeur invraisemblable ({valeur})"
        return bornes, None

    if regle.sorte == "attelage":
        for motif, cle in ATTELAGE_MOTS:
            if re.search(motif, brut):
                return {"typeAttelage": cle}, None
        return {}, None

    if regle.sorte == "norme":
        m = NORME.search(valeur)
        if not m:
            return {}, None
        txt = re.sub(r"\s+", " ", m.group(1)).strip()
        txt = txt[0].upper() + txt[1:]
        txt = re.sub(r"(?i)^stage (\w+)", lambda x: f"Stage {x.group(1).upper()}", txt)
        txt = re.sub(r"(?i)^tier (.+)", lambda x: f"Tier {x.group(1).replace('final', 'Final')}", txt)
        return {"normeAntipollution": txt}, None

    if regle.sorte == "pdf":
        regimes = sorted({int(n) for n in re.findall(r"\b(540|750|1000|1 000)\b", valeur.replace("1 000", "1000"))})
        if len(regimes) == 1:
            return {"regimePdf": regimes[0]}, None
        if len(regimes) > 1:
            return {}, f"{libelle} : plusieurs régimes ({valeur})"
        return {}, None

    if regle.sorte == "cat_attelage":
        m = CAT_ATTELAGE.search(brut)
        if not m:
            return {}, None
        cat = ROMAIN.get(m.group(1).lower(), m.group(1))
        return {"categorieAttelage": cat + ("N" if m.group(2) else "")}, None

    if regle.sorte == "distributeurs":
        res = {}
        de = re.search(r"(\d+)\s*(?:x\s*)?(?:de|double effet|dew)\b", brut)
        se = re.search(r"(\d+)\s*(?:x\s*)?(?:se|simple effet)\b", brut)
        if de:
            res["distributeursDERequis"] = int(de.group(1))
        if se:
            res["distributeursSERequis"] = int(se.group(1))
        return res, None

    return {}, None


def separer_variantes(fiche: FicheBrute) -> list[FicheBrute]:
    """« Porté 3m | Porté 4m | Porté 5m » avec « 3.00m - 4.00m - 5.00m » → 3 fiches."""
    parts = [p.strip() for p in (fiche.variante or "").split("|") if p.strip()]
    if len(parts) < 2:
        return [fiche]
    n = len(parts)
    fiches = []
    for i, part in enumerate(parts):
        specs = {}
        for k, v in fiche.specs.items():
            segments = re.split(r"\s+[-–]\s+", v or "")
            specs[k] = segments[i].strip() if len(segments) == n else v
        fiches.append(replace(fiche, variante=part, specs=specs))
    return fiches


def extraire(fiche: FicheBrute) -> FicheExtraite:
    libelles = {k: libelle_normalise(k) for k in fiche.specs}
    texte = f"{fiche.nom} {fiche.gamme} {fiche.sous_categorie} {fiche.description}"
    ctx = Contexte(
        motorise=est_motorise(fiche.categorie, texte, list(libelles.values())),
        tracteur=est_tracteur(fiche.categorie),
    )
    ext = FicheExtraite(
        brute=fiche,
        categorie_nom=nom_categorie(fiche.categorie),
        famille=famille(fiche.categorie, fiche.sous_categorie),
        motorise=ctx.motorise,
        tracteur=ctx.tracteur,
    )

    retenues: dict[str, Proposition] = {}
    for brut, norm in libelles.items():
        valeur = str(fiche.specs[brut] or "").strip()
        if not valeur:
            continue
        reconnu = False
        for regle in REGLES:
            if not re.search(regle.motif, norm) or not regle.si(ctx):
                continue
            res, ecart = _appliquer(regle, brut, valeur)
            if ecart:
                ext.ecartes.append(ecart)
                reconnu = True
            for champ, v in res.items():
                reconnu = True
                prop = Proposition(champ, v, f"{brut} : {valeur}"[:300], regle.confiance)
                actuelle = retenues.get(champ)
                if actuelle is None or prop.confiance > actuelle.confiance:
                    retenues[champ] = prop
        if not reconnu:
            ext.non_reconnus.append(brut)

    # ISOBUS cité n'importe où dans les specs
    tout = sans_accents(" ".join(f"{k} {v}" for k, v in fiche.specs.items())).lower()
    if "isobus" in tout and "isobus" not in retenues:
        negatif = re.search(r"(sans|non|pas d)\s+isobus", tout)
        retenues["isobus"] = Proposition("isobus", not negatif, "ISOBUS mentionné dans les caractéristiques", 0.7)

    # Type d'attelage cité dans le nom, la gamme ou la variante (« Porté 3m », « Smaragd traîné »)
    if "typeAttelage" not in retenues and not ctx.tracteur:
        nom = sans_accents(f"{fiche.nom} {fiche.gamme} {fiche.variante}").lower()
        trouves = {cle for motif, cle in ATTELAGE_MOTS if re.search(motif, nom)}
        if not trouves:
            desc = sans_accents(fiche.description).lower()
            trouves = {cle for motif, cle in ATTELAGE_MOTS if re.search(motif, desc)}
            source = f"Description : {fiche.description[:120]}"
        else:
            source = f"Nom : {fiche.nom} {fiche.variante}".strip()
        # « semi-porté » contient aussi « porté » : on garde le plus précis
        if "SEMI_PORTE" in trouves:
            trouves.discard("PORTE")
        if len(trouves) == 1:
            retenues["typeAttelage"] = Proposition("typeAttelage", trouves.pop(), source, 0.6)

    # Automoteurs déduits de la catégorie
    if "typeAttelage" not in retenues and ctx.motorise and not ctx.tracteur:
        retenues["typeAttelage"] = Proposition("typeAttelage", "AUTOMOTEUR", f"Catégorie : {fiche.categorie}", 0.6)

    # Cohérence min ≤ max
    for a, b in [("largeurTravailMinM", "largeurTravailMaxM"), ("puissanceRequiseMinCh", "puissanceRequiseMaxCh"),
                 ("vitesseTravailMinKmh", "vitesseTravailMaxKmh")]:
        if a in retenues and b in retenues and retenues[a].valeur > retenues[b].valeur:  # type: ignore[operator]
            ext.ecartes.append(f"{a} > {b} : valeurs écartées")
            del retenues[a], retenues[b]

    ext.propositions = list(retenues.values())
    ext.champs = {p.champ: p.valeur for p in ext.propositions}
    return ext


def dedoublonner(extraites: list[FicheExtraite]) -> tuple[list[FicheExtraite], list[str]]:
    """La base impose marque + nom + variante uniques.

    Même clé, gammes différentes → la gamme est ajoutée au nom (« Maximulch Série 5 Rouleau T-Sem »).
    Même clé, même gamme → on garde la fiche la plus complète ; les autres sont signalées.
    """
    groupes: dict[str, list[FicheExtraite]] = {}
    for e in extraites:
        groupes.setdefault(e.brute.cle(), []).append(e)
    res: list[FicheExtraite] = []
    signales: list[str] = []
    for cle, liste in groupes.items():
        if len(liste) == 1:
            res.append(liste[0])
            continue
        gammes = {e.brute.gamme for e in liste}
        if len(gammes) == len(liste) and all(gammes):
            for e in liste:
                if e.brute.gamme.lower() not in e.brute.nom.lower():
                    e.brute = replace(e.brute, nom=f"{e.brute.gamme} {e.brute.nom}")
                res.append(e)
            continue
        liste.sort(key=lambda e: len(e.champs), reverse=True)
        res.append(liste[0])
        signales.append(f"{cle} ({len(liste)} fiches, la plus complète est gardée)")
    return res, signales
