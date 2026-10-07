"""
AgriScan Scraper — point d'entrée unique
Récupère les fiches modèles sur les sites constructeurs et met à jour la base Neon.

Usage :
    python scraper.py
"""

import os
import re
import json
import time
import random
import logging
from io import BytesIO
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
import pdfplumber
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup

import db
import qdrant_sync

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("agriscan")

# Traduction des libellés de specs anglais → français
SPECS_TRADUCTIONS = {
    # Moteur
    "Displacement":             "Cylindrée",
    "Engine displacement":      "Cylindrée",
    "Bore/Stroke":              "Alésage/Course",
    "Bore stroke":              "Alésage/Course",
    "Rated RPM":                "Régime nominal",
    "Engine RPM":               "Régime moteur",
    "Rated Power (gross)":      "Puissance brute",
    "Rated Power (net)":        "Puissance nette",
    "Engine Power":             "Puissance moteur",
    "Power":                    "Puissance",
    "PTO Power":                "Puissance PDF",
    "Drawbar Power":            "Puissance à la barre",
    "Horsepower":               "Puissance (ch)",
    "Torque":                   "Couple",
    "Torque RPM":               "Régime couple max",
    "Air cleaner":              "Filtre à air",
    "Starter volts":            "Tension démarreur",
    "Starter":                  "Démarreur",
    "Firing order":             "Ordre allumage",
    "Coolant capacity":         "Capacité refroidissement",
    "Compression":              "Taux de compression",
    "Compression ratio":        "Taux de compression",
    "Fuel":                     "Carburant",
    "Fuel type":                "Type carburant",
    "Fuel capacity":            "Capacité réservoir",
    "Emissions":                "Norme émissions",
    "Engine make":              "Fabricant moteur",
    "Engine model":             "Modèle moteur",
    "Cylinders":                "Nombre cylindres",
    "Aspiration":               "Aspiration",
    "Turbo":                    "Turbo",
    # Transmission
    "Type":                     "Type transmission",
    "Transmission":             "Transmission",
    "Gears":                    "Rapports",
    "Speeds":                   "Vitesses",
    "Clutch":                   "Embrayage",
    "Oil capacity":             "Capacité huile",
    "Differential lock":        "Blocage différentiel",
    "Four wheel drive":         "4 roues motrices",
    "Front axle":               "Pont avant",
    # Dimensions & poids
    "Wheelbase":                "Empattement",
    "Length":                   "Longueur",
    "Width":                    "Largeur",
    "Height":                   "Hauteur",
    "Operating weight":         "Poids en ordre de marche",
    "Weight":                   "Poids",
    "Ballasted weight":         "Poids lesté",
    "Front tread":              "Voie avant",
    "Rear tread":               "Voie arrière",
    "Ground clearance":         "Garde au sol",
    "Turning radius":           "Rayon de braquage",
    # Pneumatiques
    "Ag front":                 "Pneus avant",
    "Ag rear":                  "Pneus arrière",
    "Front tire":               "Pneu avant",
    "Rear tire":                "Pneu arrière",
    "Tire size front":          "Dimension pneu avant",
    "Tire size rear":           "Dimension pneu arrière",
    # Hydraulique & relevage
    "Rear lift":                "Capacité relevage arrière",
    "Front lift":               "Capacité relevage avant",
    "Lift capacity":            "Capacité relevage",
    "Pump flow":                "Débit pompe hydraulique",
    "Hydraulic system":         "Système hydraulique",
    "Steering":                 "Direction",
    "Hydraulic pressure":       "Pression hydraulique",
    # Électrique
    "Electrical":               "Système électrique",
    "Battery":                  "Batterie",
    "Alternator":               "Alternateur",
    # Divers
    "Cab":                      "Cabine",
    "ROPS":                     "Arceau de sécurité",
    "Air conditioning":         "Climatisation",
    "Year":                     "Année",
    "Production":               "Période de production",
    "Series":                   "Série",
    "Type (tractor)":           "Type de tracteur",
    # Kverneland (charrues, presses, etc.)
    "Working width cm":         "Largeur de travail (cm)",
    "Interbody clearance cm":   "Dégagement entre corps (cm)",
    "Underbeam clearance cm":   "Dégagement sous poutre (cm)",
    "Head- stock":              "Attelage",
    "Headstock":                "Attelage",
    "Leg protection":           "Protection des éléments",
    "No. of furrows":           "Nombre de corps",
    "Leaf springs":             "Ressorts lame",
    "Release Pressure kN":      "Pression de déclenchement (kN)",
}


@dataclass
class Machine:
    brand: str = ""
    range: str = ""
    name: str = ""
    variant: str = ""
    category: str = ""
    subcategory: str = ""
    description: str = ""
    specs: str = ""
    imageUrl: str = ""
    videoUrl: str = ""
    sourceUrl: str = ""
    statut: str = ""       # "active" | "discontinued" ; vide = défaut de la table ("active")
    anneeDebut: str = ""
    anneeFin: str = ""


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def traduire_specs(specs: dict) -> dict:
    """Traduit les clés des specs en français quand une correspondance existe."""
    result = {}
    for k, v in specs.items():
        if k in SPECS_TRADUCTIONS:
            result[SPECS_TRADUCTIONS[k]] = v
            continue
        k_lower = k.lower()
        for eng, fr in SPECS_TRADUCTIONS.items():
            if eng.lower() == k_lower:
                result[fr] = v
                break
        else:
            result[k] = v
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Normalisation des catégories — appliquée à toutes les sources pour que le
# catalogue reste cohérent quel que soit le site d'origine (slug d'URL anglais
# chez Kverneland, catégorie déjà fixée chez TractorData/Claas, etc.)
# ─────────────────────────────────────────────────────────────────────────────

# Mot-clé (anglais ou français, en minuscules) → catégorie officielle AgriScan.
# Le premier mot-clé trouvé dans le texte l'emporte : l'ordre compte pour les
# cas ambigus (ex. "disc harrow" doit matcher avant le "harrow" générique).
CATEGORIE_MOTS_CLES = [
    ("tractor", "Tracteurs"),
    ("tracteur", "Tracteurs"),
    ("combine", "Moissonneuses"),
    ("moissonneuse", "Moissonneuses"),
    ("forage harvester", "Ensileuses"),
    ("ensileuse", "Ensileuses"),
    ("plough", "Charrues"),
    ("plow", "Charrues"),
    ("charrue", "Charrues"),
    ("disc harrow", "Déchaumeurs"),
    ("dechaumeur", "Déchaumeurs"),
    ("déchaumeur", "Déchaumeurs"),
    ("cultivator", "Déchaumeurs"),
    ("power harrow", "Travail du sol"),
    ("harrow", "Travail du sol"),
    ("herse", "Travail du sol"),
    ("roller", "Travail du sol"),
    ("rouleau", "Travail du sol"),
    ("subsoiler", "Travail du sol"),
    ("tillage", "Travail du sol"),
    ("seed drill", "Semoirs"),
    ("seeder", "Semoirs"),
    ("planter", "Semoirs"),
    ("semoir", "Semoirs"),
    ("drill", "Semoirs"),
    ("sprayer", "Pulvérisateurs"),
    ("pulverisateur", "Pulvérisateurs"),
    ("pulvérisateur", "Pulvérisateurs"),
    ("spreader", "Épandeurs"),
    ("fertiliser", "Épandeurs"),
    ("fertilizer", "Épandeurs"),
    ("epandeur", "Épandeurs"),
    ("épandeur", "Épandeurs"),
    ("manure", "Épandeurs"),
    ("baler", "Presses"),
    ("presse", "Presses"),
    ("wrapper", "Presses"),
    ("enrubanneuse", "Presses"),
    ("mower", "Fenaison"),
    ("faucheuse", "Fenaison"),
    ("tedder", "Fenaison"),
    ("faneuse", "Fenaison"),
    ("rake", "Fenaison"),
    ("andaineur", "Fenaison"),
    ("merger", "Fenaison"),
    ("hoe", "Bineuses"),
    ("bineuse", "Bineuses"),
    ("weeder", "Bineuses"),
    ("chopper", "Broyeurs"),
    ("shredder", "Broyeurs"),
    ("mulcher", "Broyeurs"),
    ("broyeur", "Broyeurs"),
    ("flail", "Broyeurs"),
    ("front loader", "Chargeurs"),
    ("chargeur frontal", "Chargeurs"),
    ("loader", "Chargeurs"),
    ("telehandler", "Télescopiques"),
    ("telescopique", "Télescopiques"),
    ("télescopique", "Télescopiques"),
    ("trailer", "Remorques agricoles"),
    ("remorque", "Remorques agricoles"),
    ("wagon", "Remorques agricoles"),
    ("mixer feeder", "Élevage & stabulation"),
    ("desileuse", "Élevage & stabulation"),
    ("désileuse", "Élevage & stabulation"),
    ("melangeuse", "Élevage & stabulation"),
    ("mélangeuse", "Élevage & stabulation"),
    ("livestock", "Élevage & stabulation"),
    ("milking", "Élevage & stabulation"),
    ("vineyard", "Vendange"),
    ("vigne", "Vendange"),
    ("viticole", "Vendange"),
    ("potato", "Cultures spécialisées"),
    ("pomme de terre", "Cultures spécialisées"),
    ("planteuse", "Cultures spécialisées"),
    ("silo", "Stockage & séchage"),
    ("grain dryer", "Stockage & séchage"),
    ("sechoir", "Stockage & séchage"),
    ("séchoir", "Stockage & séchage"),
    ("irrigation", "Matériel d'irrigation"),
    ("snow", "Déneigement"),
    ("neige", "Déneigement"),
]


def normaliser_categorie(*textes: str) -> str:
    """Normalise vers une catégorie officielle AgriScan par mot-clé.

    Accepte plusieurs textes bruts (slug de catégorie, sous-catégorie, nom du
    modèle...) et cherche le premier mot-clé qui matche dans l'ensemble.
    Retourne "Autre" si rien ne correspond, plutôt que de laisser passer une
    catégorie brute non maîtrisée (slug anglais, etc.) dans le catalogue.
    """
    # Les slugs d'URL utilisent des tirets ("disc-harrows") : on les
    # normalise en espaces pour que les mots-clés à plusieurs mots matchent.
    combined = " ".join(t or "" for t in textes).lower().replace("-", " ")
    for mot_cle, categorie in CATEGORIE_MOTS_CLES:
        if mot_cle in combined:
            return categorie
    return "Autre"


# ─────────────────────────────────────────────────────────────────────────────
# Kverneland (matériel de travail du sol, semis, etc.)
# Structure : catégorie/sous-catégorie/modèle — chaque fiche modèle a des
# tableaux clé/valeur exploitables directement.
# ─────────────────────────────────────────────────────────────────────────────

KVERNELAND_HOME = "https://www.kverneland.com/"


def _humanize_slug(slug: str) -> str:
    return slug.replace("-", " ").strip().capitalize()


def _clean_kverneland_title(raw_title: str) -> str:
    """Nettoie un <title> de page Kverneland pour n'en garder que le nom du modèle.

    Le <title> mélange nom de produit et accroche marketing, dans un ordre
    incohérent selon les pages :
      "Kverneland 6500F FW Baler-Wrapper Combo | Efficient Bale & Wrap"
      "Rigid coulterbar to complement f-drill model range... | Kverneland f-drill CB"
      "Kverneland FHP - Kverneland"
    On garde la partie qui commence par "Kverneland" (ou la plus courte à
    défaut), puis on retire les mentions de la marque en trop.
    """
    parts = [p.strip() for p in raw_title.split("|") if p.strip()]
    if not parts:
        return clean(raw_title)

    kverneland_parts = [p for p in parts if p.lower().startswith("kverneland")]
    chosen = kverneland_parts[0] if kverneland_parts else min(parts, key=len)

    if chosen.lower().startswith("kverneland"):
        chosen = chosen[len("kverneland"):].strip()
    chosen = re.sub(r"\s*-\s*Kverneland\s*$", "", chosen, flags=re.I)

    return clean(chosen)


def _kverneland_product_links(page: Page) -> set:
    """Une fiche modèle Kverneland a toujours une URL à 3 segments :
    /categorie/sous-categorie/modele. Les pages de catégorie/sous-catégorie
    n'ont que 1 ou 2 segments, ce qui les exclut naturellement."""
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "kverneland.com" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) == 3:
            links.add(href.split("?")[0].split("#")[0])
    return links


def _kverneland_parse_tables(tables) -> list:
    """Retourne une liste de (nom_modele, specs) à partir des tables d'une
    fiche produit Kverneland. Deux formats rencontrés :
    - clé/valeur classique (2 colonnes, une ligne par attribut, avec souvent
      une clé "Model" donnant le nom du modèle) ;
    - "une ligne par modèle" (une colonne "Model" en tête, les colonnes
      suivantes sont les attributs, une ligne par modèle de la gamme —
      ex. tableaux de comparaison des tailles d'une mélangeuse). Sans cette
      distinction, la ligne d'en-tête de ce 2e format est prise pour une
      paire clé/valeur ("Model" → le libellé du 1er attribut), et aucun des
      modèles de la gamme n'est capturé individuellement.
    """
    results = []
    kv_specs = {}
    for table in tables:
        rows = table.query_selector_all("tr")
        if not rows:
            continue
        header = [clean(c.inner_text()) for c in rows[0].query_selector_all("td, th")]
        if header and header[0].lower() == "model" and len(header) > 2:
            for row in rows[1:]:
                values = [clean(c.inner_text()) for c in row.query_selector_all("td, th")]
                if len(values) < 2 or not values[0]:
                    continue
                specs = {
                    header[j]: values[j]
                    for j in range(1, min(len(header), len(values)))
                    if values[j]
                }
                if specs:
                    results.append((values[0], specs))
        else:
            for row in rows:
                cells = row.query_selector_all("td, th")
                if len(cells) >= 2:
                    k = clean(cells[0].inner_text())
                    v = clean(cells[1].inner_text())
                    if k and v:
                        kv_specs[k] = v
    if kv_specs:
        results.append((kv_specs.pop("Model", ""), kv_specs))
    return results


def scrape_kverneland(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles Kverneland non encore présentes dans Neon."""
    machines = []
    try:
        page.goto(KVERNELAND_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
    except Exception as e:
        log.warning(f"  Kverneland inaccessible : {e}")
        return machines

    product_links = _kverneland_product_links(page)
    log.info(f"  Kverneland → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        model_specs = _kverneland_parse_tables(page.query_selector_all("table"))
        if not model_specs:
            continue

        segments = [s for s in urlparse(url).path.split("/") if s]
        category_slug, subcategory_slug = segments[0], segments[1]
        page_title = _clean_kverneland_title(page.title())

        for name, specs in model_specs:
            m = Machine()
            m.brand = "Kverneland"
            m.name = name or page_title
            m.category = normaliser_categorie(category_slug, subcategory_slug, m.name)
            m.subcategory = _humanize_slug(subcategory_slug)
            m.sourceUrl = url
            m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
            # Catalogue constructeur actuel : tout ce qu'on y trouve est en vente aujourd'hui
            m.statut = "active"

            if not m.name or len(m.name) < 2:
                continue

            key = f"{m.brand}|{m.name}|{m.variant}"
            if key in existing_keys:
                continue

            machines.append(m)
            existing_keys.add(key)
            log.info(f"    [{i}/{len(product_links)}] ✓ {m.name}")

        time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Claas (tracteurs) — claas.com
# Structure : une page "gamme" (ex. Arion 400) contient un tableau où chaque
# ligne est un modèle précis de la gamme (ex. 470 TREND, 460, 450 TREND...).
# ─────────────────────────────────────────────────────────────────────────────

CLAAS_TRACTEURS_URL = "https://www.claas.com/fr-fr/machines-agricoles/tracteurs"

# Slugs qui ne sont pas des gammes de tracteurs mais des pages annexes
CLAAS_EXCLUSIONS = [
    "decouvrir-tous-les-tracteurs",
    "assistance-connectivite",
    "confort-de-conduite",
    "efficacite-du-train",
    "qualite-et-fiabilite",
    "chargeurs-frontaux",
    "first-claas-used",
    "actions-commerciales",
    "configurateur-produit",
]


def _claas_candidate_links(page: Page) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "claas.com" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) == 4 and segments[:3] == ["fr-fr", "machines-agricoles", "tracteurs"]:
            slug = segments[3]
            if any(x in slug for x in CLAAS_EXCLUSIONS):
                continue
            links.add(href.split("?")[0].split("#")[0])
    return links


def scrape_claas(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les gammes de tracteurs Claas non encore présentes dans Neon.

    Certaines pages regroupent seulement des liens vers d'autres gammes
    (ex. "tracteurs compacts") au lieu d'un tableau de specs : dans ce cas
    on explore aussi leurs liens plutôt que de les ignorer."""
    machines = []
    try:
        page.goto(CLAAS_TRACTEURS_URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
    except Exception as e:
        log.warning(f"  Claas inaccessible : {e}")
        return machines

    to_visit = _claas_candidate_links(page)
    visited = set()
    log.info(f"  Claas → {len(to_visit)} gammes candidates trouvées")

    while to_visit:
        url = to_visit.pop()
        if url in visited:
            continue
        visited.add(url)

        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        tables = page.query_selector_all("table")
        if not tables:
            # Page de regroupement plutôt qu'une gamme : on explore ses liens
            to_visit |= (_claas_candidate_links(page) - visited)
            continue

        range_name = clean(page.title()).replace(" | CLAAS", "")
        rows = tables[0].query_selector_all("tr")
        if not rows:
            continue
        headers = [clean(c.inner_text()) for c in rows[0].query_selector_all("td, th")]

        for row in rows[1:]:
            cells = row.query_selector_all("td, th")
            values = [clean(c.inner_text()) for c in cells]
            if not values or not values[0]:
                continue

            specs = {
                headers[i]: values[i]
                for i in range(1, min(len(headers), len(values)))
                if headers[i] and values[i]
            }

            m = Machine()
            m.brand = "Claas"
            m.range = range_name
            m.name = values[0]
            m.category = "Tracteurs"
            m.sourceUrl = url
            # Catalogue constructeur actuel : tout ce qu'on y trouve est en vente aujourd'hui
            m.statut = "active"
            # Transmission différente = modèle différent malgré le même nom
            transmission = next((v for k, v in specs.items() if "transmission" in k.lower()), "")
            m.variant = transmission.split()[0] if transmission else ""
            m.specs = json.dumps(specs, ensure_ascii=False)

            key = f"{m.brand}|{m.name}|{m.variant}"
            if key in existing_keys:
                continue

            machines.append(m)
            existing_keys.add(key)
            log.info(f"    ✓ {range_name} — {m.name}")

        time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Tableaux "larges" — Fendt, Massey Ferguson, New Holland
# Structure : chaque COLONNE du tableau est un modèle/finition, chaque LIGNE
# (après la 1ère) est un attribut technique avec une valeur par colonne.
# ─────────────────────────────────────────────────────────────────────────────

def _parse_wide_models_table(table) -> dict:
    """Table où chaque colonne est un modèle et chaque ligne un attribut."""
    rows = table.query_selector_all("tr")
    if not rows:
        return {}
    header_cells = rows[0].query_selector_all("td, th")
    # La colonne 0 est toujours le nom de l'attribut (ligne), jamais un modèle.
    models = [(i, clean(c.inner_text())) for i, c in enumerate(header_cells) if i > 0 and clean(c.inner_text())]
    result = {name: {} for _, name in models}
    for row in rows[1:]:
        cells = row.query_selector_all("td, th")
        if len(cells) < 2:
            continue
        attr_name = clean(cells[0].inner_text())
        if not attr_name:
            continue
        for idx, name in models:
            if idx < len(cells):
                val = clean(cells[idx].inner_text())
                if val:
                    result[name][attr_name] = val
    return result


def _machines_from_wide_table(table, brand: str, category: str, range_name: str, source_url: str) -> list[Machine]:
    models = _parse_wide_models_table(table)
    machines = []
    for name, specs in models.items():
        if not specs or len(name) < 2:
            continue
        m = Machine()
        m.brand = brand
        m.range = range_name
        m.name = name
        m.category = category
        m.sourceUrl = source_url
        # Catalogue constructeur actuel : tout ce qu'on y trouve est en vente aujourd'hui
        m.statut = "active"
        m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
        machines.append(m)
    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Fendt — fendt.com
# Piège découvert après mise en prod : le site n'utilise plus un vrai
# tableau "une cellule = un modèle". Chaque cellule d'en-tête/valeur
# regroupe tous les modèles dans des <div class="techdata-column"> imbriqués
# (un par modèle) à l'intérieur d'une seule <th>/<td> — le parseur "large"
# générique (une cellule HTML = un modèle) ne peut donc pas s'appliquer ici.
# ─────────────────────────────────────────────────────────────────────────────

FENDT_HOME = "https://www.fendt.com/fr/"

# Sections du site qui ne sont pas des fiches produits
FENDT_EXCLUSIONS = [
    "smart-farming",
    "accessoires-originaux-technologie",
    "domaines-dapplication",
]


def _fendt_product_links(page: Page) -> set:
    """Une fiche produit Fendt a une URL à 4 segments :
    /fr/machines-agricoles/<categorie>/<modele>."""
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "fendt.com" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) == 4 and segments[0] == "fr" and segments[1] == "machines-agricoles":
            if any(x in segments[2] for x in FENDT_EXCLUSIONS):
                continue
            links.add(href.split("?")[0].split("#")[0])
    return links


def _parse_fendt_specs_table(table) -> dict:
    """Table où l'en-tête et chaque ligne regroupent tous les modèles dans
    des <div class="techdata-column"> imbriqués (un par modèle), dans le
    même ordre entre l'en-tête et les lignes de valeurs."""
    header_row = table.query_selector("thead tr") or table.query_selector("tr")
    if not header_row:
        return {}
    model_names = [clean(c.inner_text()) for c in header_row.query_selector_all(".techdata-column")]
    if not any(model_names):
        return {}
    result = {name: {} for name in model_names if name}

    for row in table.query_selector_all("tbody tr"):
        attr_cell = row.query_selector(".techdata-firstColumn")
        if not attr_cell:
            continue
        attr_name = clean(attr_cell.inner_text())
        if not attr_name:
            continue
        value_cols = row.query_selector_all(".techdata-columns .techdata-column")
        for idx, val_cell in enumerate(value_cols):
            if idx >= len(model_names) or not model_names[idx]:
                continue
            val = clean(val_cell.inner_text())
            if val:
                result[model_names[idx]][attr_name] = val

    return result


def scrape_fendt(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles Fendt non encore présentes dans Neon."""
    machines = []
    try:
        page.goto(FENDT_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
    except Exception as e:
        log.warning(f"  Fendt inaccessible : {e}")
        return machines

    product_links = _fendt_product_links(page)
    log.info(f"  Fendt → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        tables = page.query_selector_all("table")
        if not tables:
            continue

        segments = [s for s in urlparse(url).path.split("/") if s]
        category_slug = segments[2]
        range_name = clean(page.title()).split("|")[0].strip()
        category = normaliser_categorie(category_slug, range_name)

        for table in tables:
            models = _parse_fendt_specs_table(table)
            for model_name, specs in models.items():
                if not specs:
                    continue
                key = f"Fendt|{model_name}|"
                if key in existing_keys:
                    continue
                m = Machine()
                m.brand = "Fendt"
                m.range = range_name
                m.name = model_name
                m.category = category
                m.sourceUrl = url
                m.statut = "active"
                m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
                machines.append(m)
                existing_keys.add(key)
                log.info(f"    [{i}/{len(product_links)}] ✓ {model_name}")

        time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Massey Ferguson — masseyferguson.com
# Piège découvert après mise en prod : contrairement à Fendt/New Holland, le
# tableau de specs n'est pas au format "large" (colonne = modèle). C'est
# l'inverse : la 1re ligne contient les en-têtes d'attributs (dont "MODÈLE"
# en colonne 0), et chaque ligne suivante est un modèle — même format que
# Güttler/Actisol/Valtra. Le parseur large produisait des noms de machine
# qui étaient en fait des libellés de specs ("FORMAT DES BALLES (MM)").
# ─────────────────────────────────────────────────────────────────────────────

MF_HOME = "https://www.masseyferguson.com/fr_fr.html"


def _mf_product_links(page: Page) -> set:
    """Une fiche produit Massey Ferguson est sous /product/<categorie>/<modele>.html."""
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "masseyferguson.com" not in u.netloc:
            continue
        if "/product/" in u.path and u.path.endswith(".html"):
            links.add(href.split("?")[0].split("#")[0])
    return links


def _parse_mf_specs_table(table) -> dict:
    """Table où la 1re ligne est l'en-tête (colonne 0 = "MODÈLE") et chaque
    ligne suivante est un modèle (col 0 = nom du modèle, colonnes suivantes
    = valeurs). Certaines fiches ont d'autres tableaux avant/après celui des
    modèles (options, versions...) : on ne traite que celui dont l'en-tête
    commence bien par "MODÈLE", sinon on ignore (retour vide) plutôt que de
    remonter des lignes d'un tableau non pertinent comme si c'était des
    machines."""
    rows = table.query_selector_all("tr")
    if len(rows) < 2:
        return {}
    header = [clean(c.inner_text()) for c in rows[0].query_selector_all("td, th")]
    if not header or header[0].strip().upper() != "MODÈLE":
        return {}
    result = {}
    for row in rows[1:]:
        cells = row.query_selector_all("td, th")
        if not cells:
            continue
        model_name = clean(cells[0].inner_text())
        if not model_name:
            continue
        specs = {}
        for i, cell in enumerate(cells[1:], start=1):
            if i < len(header) and header[i]:
                val = clean(cell.inner_text())
                if val:
                    specs[header[i]] = val
        if not specs:
            continue
        key = model_name
        if key in result:
            n = 2
            while f"{key} ({n})" in result:
                n += 1
            key = f"{key} ({n})"
        result[key] = specs
    return result


def scrape_massey_ferguson(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles Massey Ferguson non encore présentes dans Neon."""
    machines = []
    try:
        page.goto(MF_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
    except Exception as e:
        log.warning(f"  Massey Ferguson inaccessible : {e}")
        return machines

    product_links = _mf_product_links(page)
    log.info(f"  Massey Ferguson → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        tables = page.query_selector_all("table")
        if not tables:
            continue

        segments = [s for s in urlparse(url).path.split("/") if s]
        category_slug = segments[-2] if len(segments) >= 2 else ""
        range_name = clean(page.title()).split("|")[0].strip()
        category = normaliser_categorie(category_slug, range_name)

        for table in tables:
            models = _parse_mf_specs_table(table)
            for model_name, specs in models.items():
                key = f"Massey Ferguson|{model_name}|"
                if key in existing_keys:
                    continue
                m = Machine()
                m.brand = "Massey Ferguson"
                m.range = range_name
                m.name = model_name
                m.category = category
                m.sourceUrl = url
                m.statut = "active"
                m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
                machines.append(m)
                existing_keys.add(key)
                log.info(f"    [{i}/{len(product_links)}] ✓ {model_name}")

        time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# New Holland — agriculture.newholland.com
# La page d'accueil mélange des liens agricoles et BTP (construction) : on
# part directement des 4 catégories agricoles connues plutôt que d'un crawl
# générique, pour éviter de remonter du matériel de chantier.
# ─────────────────────────────────────────────────────────────────────────────

NEW_HOLLAND_CATEGORIES = [
    "https://agriculture.newholland.com/fr-be/europe/produits/tracteurs",
    "https://agriculture.newholland.com/fr-be/europe/produits/presses",
    "https://agriculture.newholland.com/fr-be/europe/produits/moissonneuses-batteuses",
    "https://agriculture.newholland.com/fr-be/europe/produits/ensileuses",
]


def _new_holland_product_links(page: Page, base_path: str) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "newholland.com" not in u.netloc:
            continue
        if u.path.startswith(base_path) and u.path != base_path and u.path.rstrip("/") != base_path.rstrip("/"):
            links.add(href.split("?")[0].split("#")[0])
    return links


def _wait_for_new_holland_links(page: Page, base_path: str, max_wait_ms: int = 15000, interval_ms: int = 1500) -> set:
    """La liste de produits par catégorie se charge de façon asynchrone et
    parfois lente (déjà vu : 0 lien trouvé après 4s, 22 après 6s sur le même
    essai). On sonde plutôt qu'on attend un délai fixe, pour rester robuste
    aux chargements lents sans pénaliser les chargements rapides."""
    waited = 0
    links = _new_holland_product_links(page, base_path)
    while not links and waited < max_wait_ms:
        page.wait_for_timeout(interval_ms)
        waited += interval_ms
        links = _new_holland_product_links(page, base_path)
    return links


def _dismiss_new_holland_cookies(page: Page) -> None:
    """La bannière cookies OneTrust intercepte les clics (ex. "voir plus de
    modèles") si elle n'est pas fermée au préalable."""
    try:
        accept = page.locator("#onetrust-accept-btn-handler")
        if accept.is_visible(timeout=3000):
            accept.click(timeout=3000)
            page.wait_for_timeout(1000)
    except Exception:
        pass


def _new_holland_reveal_all_models(page: Page) -> None:
    """Certaines fiches famille (ex. barres de coupe Varifeed) cachent une
    partie des modèles derrière un bouton "VOIR PLUS DE MODÈLES" : la
    galerie de cartes grossit au clic mais le <table> de specs techniques,
    lui, ne bouge jamais (vérifié : les codes des modèles révélés
    n'existent nulle part dans son DOM, même après clic)."""
    for _ in range(10):
        try:
            btn = page.get_by_text("VOIR PLUS DE MODÈLES", exact=False).first
            if not btn.is_visible(timeout=1000):
                break
            btn.scroll_into_view_if_needed(timeout=2000)
            btn.click(timeout=2000)
            page.wait_for_timeout(1200)
        except Exception:
            break


def _new_holland_models_from_cards(page: Page) -> dict:
    """Specs minimales (nom + caractéristiques affichées) extraites
    directement de la galerie de cartes "MODÈLES" : seule source pour les
    modèles absents du <table> technique (le tableau n'a pas toujours été
    mis à jour avec les modèles ajoutés depuis à la gamme)."""
    return page.evaluate(
        """
        () => {
            const cards = Array.from(document.querySelectorAll('.model-listing__card'));
            const result = {};
            cards.forEach(card => {
                const titleEl = card.querySelector('.model-listing-card__title');
                if (!titleEl) return;
                const name = titleEl.innerText.trim();
                if (!name) return;
                const specs = {};
                card.querySelectorAll('.model-listing-card__spec-text').forEach(label => {
                    const value = label.nextElementSibling;
                    if (!value || !value.classList.contains('model-listing-card__spec-value')) return;
                    const l = label.innerText.trim();
                    const v = value.innerText.trim();
                    if (l && v) specs[l] = v;
                });
                result[name] = specs;
            });
            return result;
        }
        """
    )


def scrape_new_holland(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles New Holland (tracteurs, presses, moissonneuses,
    ensileuses) non encore présentes dans Neon."""
    machines = []
    cookies_dismissed = False

    for category_url in NEW_HOLLAND_CATEGORIES:
        base_path = urlparse(category_url).path
        category_slug = base_path.rstrip("/").split("/")[-1]

        try:
            page.goto(category_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
        except Exception as e:
            log.warning(f"  New Holland ({category_slug}) inaccessible : {e}")
            continue

        if not cookies_dismissed:
            _dismiss_new_holland_cookies(page)
            cookies_dismissed = True

        product_links = _wait_for_new_holland_links(page, base_path)
        log.info(f"  New Holland ({category_slug}) → {len(product_links)} fiches modèles trouvées")
        category = normaliser_categorie(category_slug)

        for i, url in enumerate(sorted(product_links), 1):
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
            except Exception as e:
                log.warning(f"    Erreur {url} → {e}")
                continue

            _new_holland_reveal_all_models(page)

            range_name = clean(page.title()).split("|")[0].strip()

            tables = page.query_selector_all("table")
            table_machines = (
                _machines_from_wide_table(tables[0], "New Holland", category, range_name, url)
                if tables
                else []
            )
            table_names = {m.name for m in table_machines}

            candidats_list = list(table_machines)
            for name, specs in _new_holland_models_from_cards(page).items():
                if name in table_names or not specs or len(name) < 2:
                    continue
                m = Machine()
                m.brand = "New Holland"
                m.range = range_name
                m.name = name
                m.category = category
                m.sourceUrl = url
                m.statut = "active"
                m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
                candidats_list.append(m)

            if not candidats_list:
                continue

            for candidats in candidats_list:
                key = f"{candidats.brand}|{candidats.name}|{candidats.variant}"
                if key in existing_keys:
                    continue
                machines.append(candidats)
                existing_keys.add(key)
                log.info(f"    [{i}/{len(product_links)}] ✓ {candidats.name}")

            time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Case IH — caseih.com (CNH Industrial, même plateforme que New Holland)
# Pas de <table> sur ce site : les pages catégorie affichent directement des
# cartes ".product-card" avec des specs résumées (une carte par GAMME, ex.
# "Gamme Magnum™", pas par modèle individuel — la sous-page de la gamme n'a
# aucun détail supplémentaire par modèle, vérifié par sondage).
# ─────────────────────────────────────────────────────────────────────────────

CASEIH_CATEGORIES = [
    "https://www.caseih.com/fr-fr/france/produits/tracteurs",
    "https://www.caseih.com/fr-fr/france/produits/chargeurs",
    "https://www.caseih.com/fr-fr/france/produits/chargeurs-telescopiques",
    "https://www.caseih.com/fr-fr/france/produits/materiels-de-recolte",
    "https://www.caseih.com/fr-fr/france/produits/paille-et-fourrage",
]


def _caseih_cards(page: Page) -> list:
    return page.evaluate(
        """
        () => {
            const cards = Array.from(document.querySelectorAll('.product-card'));
            return cards.map(c => {
                const titleEl = c.querySelector('.product-card__title');
                const name = titleEl ? titleEl.innerText.trim() : '';
                const href = c.getAttribute('href') || '';
                const specs = {};
                c.querySelectorAll('.product-card__summary-specs-item').forEach(item => {
                    const label = item.querySelector('.product-card__summary-specs-headline');
                    const value = item.querySelector('.product-card__summary-specs-value');
                    if (label && value) {
                        const l = label.innerText.trim();
                        const v = value.innerText.trim();
                        if (l && v) specs[l] = v;
                    }
                });
                return {name, href, specs};
            });
        }
        """
    )


def scrape_case_ih(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les gammes Case IH non encore présentes dans Neon (granularité
    gamme, pas modèle individuel — voir note en tête de section)."""
    machines = []

    for category_url in CASEIH_CATEGORIES:
        category_slug = category_url.rstrip("/").split("/")[-1]

        try:
            page.goto(category_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
        except Exception as e:
            log.warning(f"  Case IH ({category_slug}) inaccessible : {e}")
            continue

        category = normaliser_categorie(category_slug)
        cards = _caseih_cards(page)
        log.info(f"  Case IH ({category_slug}) → {len(cards)} gammes trouvées")

        for card in cards:
            name = clean(card["name"])
            specs = card["specs"]
            if not name or not specs:
                continue
            href = card["href"]
            m = Machine()
            m.brand = "Case IH"
            m.name = name
            m.category = category
            m.sourceUrl = href if href.startswith("http") else f"https://www.caseih.com{href}"
            m.statut = "active"
            m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
            key = f"{m.brand}|{m.name}|{m.variant}"
            if key in existing_keys:
                continue
            machines.append(m)
            existing_keys.add(key)
            log.info(f"    ✓ {m.name}")

        time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Monosem — monosem.com (semoirs de précision)
# Pas de <table> HTML sur ce site. Les seules specs structurées disponibles
# sont dans un PDF "tableau général châssis" lié depuis chaque fiche famille
# (ex. Tableau-general-chassis_NG-PLUS_EN.pdf) : 2 lignes d'en-tête (type de
# châssis, sous-type), cellules fusionnées visuellement dans le PDF et
# restituées par pdfplumber comme des colonnes à None répétés. Un autre PDF
# vu sur le site ("tableau distribution") est une image sans texte
# exploitable — couverture donc partielle, acceptée comme telle.
# ─────────────────────────────────────────────────────────────────────────────

MONOSEM_CATEGORIES = [
    "https://www.monosem.com/precision-planters/",
    "https://www.monosem.com/cultivators/",
    "https://www.monosem.com/fertilizers/",
]

MONOSEM_EXCLUSIONS = ["technologies", "guidance-systems"]


def _monosem_product_links(page: Page, base_path: str) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "monosem.com" not in u.netloc:
            continue
        if not u.path.startswith(base_path) or u.path.rstrip("/") == base_path.rstrip("/"):
            continue
        if any(x in u.path for x in MONOSEM_EXCLUSIONS):
            continue
        links.add(href.split("?")[0].split("#")[0])
    return links


def _monosem_chassis_pdf_url(page: Page) -> str | None:
    hrefs = page.eval_on_selector_all("a[href$='.pdf']", "els => els.map(e => e.href)")
    for href in hrefs:
        if "general" in href.lower():
            return href
    return None


def _monosem_forward_fill(row: list) -> list:
    """Remplit les None d'une ligne d'en-tête PDF avec la valeur non vide
    précédente : une cellule fusionnée visuellement dans le PDF est
    restituée par pdfplumber comme une valeur suivie de None répétés sur
    les colonnes qu'elle couvre."""
    filled = []
    last = None
    for cell in row:
        v = clean(cell)
        if v:
            last = v
        filled.append(last)
    return filled


# Certains PDF Monosem ont des en-têtes de groupe en texte pivoté
# (colonne latérale) que pdfplumber restitue à l'envers (ex. "EVIRD" pour
# "DRIVE"). Constaté sur plusieurs familles, liste fermée des cas vus.
MONOSEM_GARBLED_LABELS = {"EVIRD", "REZILITREF", "MESORCIM"}


def _monosem_parse_chassis_table(pdf_bytes: bytes) -> dict:
    """Parse le "tableau général châssis" : 2 lignes d'en-tête (type de
    châssis, sous-type) qui forment par colonne un intitulé composite
    (ex. "Rigid Monobar"), puis des lignes de specs (largeur, nombre
    d'éléments de dosage...)."""
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        if not pdf.pages:
            return {}
        tables = pdf.pages[0].extract_tables()
    if not tables:
        return {}

    table = tables[0]
    if len(table) < 3:
        return {}

    n_cols = max(len(r) for r in table)
    normalized = [list(r) + [None] * (n_cols - len(r)) for r in table]

    # Colonnes jamais renseignées sur aucune ligne : espacement purement
    # visuel dans le PDF, à ignorer.
    used_cols = [
        j for j in range(1, n_cols)
        if any(clean(normalized[i][j]) for i in range(len(normalized)))
    ]
    if not used_cols:
        return {}

    header1 = _monosem_forward_fill(normalized[0])
    header2 = _monosem_forward_fill(normalized[1])

    variants = {}
    for j in used_cols:
        variant = " ".join(p for p in (header1[j], header2[j]) if p).strip()
        if variant:
            variants[j] = {"variant": variant, "specs": {}}

    for row in normalized[2:]:
        label = clean(row[0])
        if not label or label.upper() in MONOSEM_GARBLED_LABELS:
            continue
        for j, data in variants.items():
            val = clean(row[j]) if j < len(row) else ""
            if val:
                data["specs"][label] = val

    return variants


def scrape_monosem(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les gammes Monosem non encore présentes dans Neon, à partir du
    "tableau général châssis" en PDF (voir note en tête de section —
    couverture partielle : seules les specs châssis/largeurs sont
    disponibles sous cette forme)."""
    machines = []

    for category_url in MONOSEM_CATEGORIES:
        base_path = urlparse(category_url).path
        category_slug = base_path.strip("/").split("/")[-1]

        try:
            page.goto(category_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        except Exception as e:
            log.warning(f"  Monosem ({category_slug}) inaccessible : {e}")
            continue

        product_links = _monosem_product_links(page, base_path)
        log.info(f"  Monosem ({category_slug}) → {len(product_links)} fiches produit trouvées")
        category = normaliser_categorie(category_slug)

        for i, url in enumerate(sorted(product_links), 1):
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
            except Exception as e:
                log.warning(f"    Erreur {url} → {e}")
                continue

            pdf_url = _monosem_chassis_pdf_url(page)
            if not pdf_url:
                continue

            try:
                resp = requests.get(pdf_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
            except Exception as e:
                log.warning(f"    PDF inaccessible {pdf_url} → {e}")
                continue

            variants = _monosem_parse_chassis_table(resp.content)
            if not variants:
                continue

            range_name = re.sub(r"\s*-\s*MONOSEM\s*$", "", clean(page.title()), flags=re.IGNORECASE)

            for data in variants.values():
                specs = data["specs"]
                if not specs:
                    continue
                # Colonne légende (texte descriptif plutôt que de vraies
                # valeurs, ex. "Number of rows") plutôt qu'une vraie
                # variante produit : on l'écarte.
                long_values = sum(1 for v in specs.values() if len(v.split()) >= 3)
                if long_values > len(specs) / 2:
                    continue
                m = Machine()
                m.brand = "Monosem"
                m.range = range_name
                m.name = range_name
                m.variant = data["variant"]
                m.category = category
                m.sourceUrl = url
                m.statut = "active"
                m.specs = json.dumps(traduire_specs(data["specs"]), ensure_ascii=False)
                key = f"{m.brand}|{m.name}|{m.variant}"
                if key in existing_keys:
                    continue
                machines.append(m)
                existing_keys.add(key)
                log.info(f"    [{i}/{len(product_links)}] ✓ {m.name} ({m.variant})")

            time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Same (same-tractors.com) — plateforme SDF Group
# Le tableau de specs HTML de la fiche produit (SPA Vue.js) reste vide (aucune
# requête réseau ni état embarqué, confirmé par sondage). En revanche certaines
# fiches ont un PDF "brochure" téléchargeable (lien /media/*.pdf) avec de
# vrais tableaux par modèle, au format "large" (une colonne = un modèle).
# Pièges rencontrés (mêmes que Monosem) : en-tête à 2 lignes (groupe de
# transmission + code modèle, nécessitant un forward-fill), tableaux
# parasites en texte pivoté/illisible (ignorés car ils ne contiennent pas de
# ligne d'en-tête reconnaissable), lignes de titre de section sans valeur
# (ex. "MOTEUR") à ignorer. Couverture partielle : seules les fiches avec un
# PDF brochure direct (pas Issuu, non exploitable) sont capturées.
#
# Deutz-Fahr (même plateforme, deutz-fahr.com) a été testé avec le même
# code mais est bloqué par une protection anti-bot (Cloudflare, page "Just a
# moment..." systématique dès la 2e/3e page visitée) depuis les runners
# GitHub Actions — confirmé sur 3 essais successifs, non lié à la logique de
# parsing. Non implémenté pour cette raison.
# ─────────────────────────────────────────────────────────────────────────────

SDF_SITES = {
    "Same": "https://www.same-tractors.com/fr-fr",
}


def _sdf_product_links(page: Page, home: str) -> set:
    """Ouvre le menu principal (nécessaire pour révéler toute la nav sur
    cette SPA) et retourne les fiches modèle /tracteurs/<slug>."""
    for sel in ["[class*='menu-toggle']", "[class*='hamburger']", "button[aria-label*='menu' i]", "nav button"]:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click(force=True, timeout=3000)
                page.wait_for_timeout(2000)
                break
        except Exception:
            pass

    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if u.netloc not in urlparse(home).netloc:
            continue
        parts = [p for p in u.path.split("/") if p]
        if len(parts) >= 3 and parts[-2] == "tracteurs":
            links.add(href.split("?")[0].split("#")[0])
    return links


def _sdf_brochure_pdf_url(page: Page) -> str | None:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    for href in hrefs:
        if "/media/" in href and href.lower().split("?")[0].endswith(".pdf"):
            return href
    return None


def _sdf_forward_fill(row: list) -> list:
    """Remplit les None/vides d'une ligne d'en-tête avec la valeur précédente non vide."""
    filled = []
    last = None
    for cell in row:
        v = clean(cell)
        if v:
            last = v
        filled.append(last)
    return filled


def _sdf_find_header_rows(table: list) -> tuple:
    """Cherche la ligne d'en-tête contenant les codes modèle (jetons courts
    alphanumériques dans les colonnes >= 1), et la ligne de groupe éventuelle
    juste au-dessus (ex. type de transmission : Powershift / RVshift)."""

    def short_token_count(row) -> int:
        count = 0
        for c in row[1:]:
            v = clean(c)
            if v and len(v) <= 15 and re.match(r"^[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9 .+/-]*$", v):
                count += 1
        return count

    best_idx, best_count = None, 0
    for i in range(min(3, len(table))):
        # Une vraie ligne de codes modèle n'a jamais de libellé d'attribut en
        # colonne 0 (cette colonne est réservée au nom de l'attribut sur les
        # lignes de données) — sans ce filtre, une ligne de données comme
        # ['Avec pneus avant', 'Taille', '300/70 R20'] peut être prise pour
        # une ligne d'en-tête (ex. tableau "un modèle par table" où le vrai
        # nom du modèle, trop long, ne passe pas le test de jeton court).
        if table[i] and clean(table[i][0]):
            continue
        cnt = short_token_count(table[i])
        if cnt > best_count:
            best_count, best_idx = cnt, i
    if best_idx is None or best_count < 2:
        return None, None

    group_idx = None
    if best_idx > 0 and any(clean(c) for c in table[best_idx - 1][1:]):
        group_idx = best_idx - 1
    return group_idx, best_idx


def _sdf_parse_spec_table(table: list) -> dict:
    """Table "large" issue d'un PDF brochure : une colonne = un modèle (+
    éventuellement un groupe de transmission sur la ligne au-dessus)."""
    group_idx, model_idx = _sdf_find_header_rows(table)
    if model_idx is None:
        return {}

    n_cols = max(len(r) for r in table)
    normalized = [list(r) + [None] * (n_cols - len(r)) for r in table]
    model_row = normalized[model_idx]
    group_row = normalized[group_idx] if group_idx is not None else None
    group_ff = _sdf_forward_fill(group_row) if group_row else None

    variants = {}
    for j in range(1, n_cols):
        code = clean(model_row[j])
        if not code:
            continue
        variants[j] = {"code": code, "group": clean(group_ff[j]) if group_ff else "", "specs": {}}
    if not variants:
        return {}

    # Le libellé de groupe ne distingue les modèles que s'il existe plusieurs
    # groupes différents (ex. "Powershift"/"RVshift") — sinon c'est juste un
    # titre de page sans valeur discriminante (ex. "SÉRIE 6 TTV" partout).
    distinct_groups = {d["group"] for d in variants.values() if d["group"]}
    use_group = len(distinct_groups) > 1

    data_start = (group_idx if group_idx is not None else model_idx) + (2 if group_idx is not None else 1)
    for row in normalized[data_start:]:
        label = clean(row[0])
        if not label:
            continue
        if len(label) > 120:
            # Texte pivoté/illisible détecté (cellule géante concaténée) :
            # toute la table est suspecte, on l'abandonne.
            return {}
        if not any(clean(row[j]) for j in variants if j < len(row)):
            continue  # titre de section sans valeur (ex. "MOTEUR", "CABINE")
        for j, data in variants.items():
            val = clean(row[j]) if j < len(row) else ""
            if val:
                data["specs"][label] = val

    result = {}
    for data in variants.values():
        if not data["specs"]:
            continue
        variant = f"{data['group']} {data['code']}".strip() if use_group else data["code"]
        result[variant] = data["specs"]
    return result


def _sdf_scrape_brand(page: Page, brand: str, home: str, existing_keys: set) -> list[Machine]:
    machines = []
    try:
        page.goto(home, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
    except Exception as e:
        log.warning(f"  {brand} inaccessible : {e}")
        return machines

    for sel in ["#onetrust-accept-btn-handler", "button:has-text('Accept')", "button:has-text('Accepter')"]:
        try:
            btn = page.query_selector(sel)
            if btn:
                btn.click(force=True, timeout=3000)
                page.wait_for_timeout(1500)
                break
        except Exception:
            pass

    product_links = _sdf_product_links(page, home)
    log.info(f"  {brand} → {len(product_links)} fiches modèles trouvées")
    category = normaliser_categorie("tracteurs")
    seen_pdfs = set()

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            # Le bouton "Télécharger la brochure" est chargé paresseusement :
            # il ne devient présent dans le DOM qu'après défilement (constaté
            # par sondage).
            for _ in range(8):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(300)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        pdf_url = _sdf_brochure_pdf_url(page)
        if not pdf_url or pdf_url in seen_pdfs:
            # PDF absent, ou déjà traité via une autre fiche produit de la
            # même sous-gamme (ex. Krypton / Krypton F / Krypton M partagent
            # la même brochure) — éviter d'injecter les mêmes variantes
            # plusieurs fois sous des noms de gamme différents.
            continue
        seen_pdfs.add(pdf_url)
        try:
            resp = requests.get(pdf_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
        except Exception as e:
            log.warning(f"    PDF inaccessible {pdf_url} → {e}")
            continue

        # Le titre de page peut être une phrase marketing complète (ex.
        # "SAME Dorado Natural, tracteur puissant le plus polyvalent...") :
        # on tronque à la première virgule/deux-points/barre verticale.
        range_name = re.split(r"\s+[-–]\s+|[|,:]", clean(page.title()))[0].strip()

        try:
            with pdfplumber.open(BytesIO(resp.content)) as pdf:
                page_tables = []
                for pg in pdf.pages:
                    page_tables.extend(pg.extract_tables())
        except Exception as e:
            log.warning(f"    Erreur lecture PDF {pdf_url} → {e}")
            continue

        seen_variants = set()
        for table in page_tables:
            variants = _sdf_parse_spec_table(table)
            for variant, specs in variants.items():
                if variant in seen_variants or not specs:
                    continue
                seen_variants.add(variant)
                m = Machine()
                m.brand = brand
                m.range = range_name
                m.name = range_name
                m.variant = variant
                m.category = category
                m.sourceUrl = url
                m.statut = "active"
                m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
                key = f"{m.brand}|{m.name}|{m.variant}"
                if key in existing_keys:
                    continue
                machines.append(m)
                existing_keys.add(key)
                log.info(f"    [{i}/{len(product_links)}] ✓ {m.name} ({m.variant})")

        time.sleep(random.uniform(1.0, 2.0))

    return machines


def scrape_same(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les modèles Same via les PDF brochure (couverture partielle)."""
    return _sdf_scrape_brand(page, "Same", SDF_SITES["Same"], existing_keys)


# ─────────────────────────────────────────────────────────────────────────────
# AVR — avrmachinery.com (matériel pomme de terre)
# Structure : chaque fiche produit a un petit tableau clé/valeur (la première
# ligne affiche juste le nom du modèle, sans clé).
# ─────────────────────────────────────────────────────────────────────────────

AVR_CATEGORIES = [
    "https://www.avrmachinery.com/en/products/harvesters",
    "https://www.avrmachinery.com/en/products/soil-cultivators",
    "https://www.avrmachinery.com/en/products/potato-planters",
    "https://www.avrmachinery.com/en/products/haulm-toppers",
    "https://www.avrmachinery.com/en/products/crop-handling",
]


def _avr_product_links(page: Page) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "avrmachinery.com" not in u.netloc:
            continue
        if "/en/product/" in u.path:
            links.add(href.split("?")[0].split("#")[0])
    return links


def scrape_avr(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles AVR non encore présentes dans Neon."""
    machines = []

    for category_url in AVR_CATEGORIES:
        category_slug = category_url.rstrip("/").split("/")[-1]

        try:
            page.goto(category_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
        except Exception as e:
            log.warning(f"  AVR ({category_slug}) inaccessible : {e}")
            continue

        product_links = _avr_product_links(page)
        log.info(f"  AVR ({category_slug}) → {len(product_links)} fiches modèles trouvées")
        category = normaliser_categorie(category_slug)

        for i, url in enumerate(sorted(product_links), 1):
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
            except Exception as e:
                log.warning(f"    Erreur {url} → {e}")
                continue

            tables = page.query_selector_all("table")
            if not tables:
                continue

            rows = tables[0].query_selector_all("tr")
            specs = {}
            for row in rows[1:]:
                cells = row.query_selector_all("td, th")
                if len(cells) < 2:
                    continue
                k = clean(cells[0].inner_text())
                v = clean(cells[1].inner_text())
                if k and v:
                    specs[k] = v

            if not specs:
                continue

            m = Machine()
            m.brand = "AVR"
            m.name = clean(page.title()).replace("AVR", "").strip()
            m.category = category
            m.sourceUrl = url
            m.statut = "active"
            m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)

            if not m.name or len(m.name) < 2:
                continue

            key = f"{m.brand}|{m.name}|{m.variant}"
            if key in existing_keys:
                continue

            machines.append(m)
            existing_keys.add(key)
            log.info(f"    [{i}/{len(product_links)}] ✓ {m.name}")
            time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# McHale — mchale.net (presses, enrubanneuses, faneuses)
# La section "Technical Specification" (classe techspec) est en fait rendue
# côté serveur, mais Chromium/Playwright ne la reçoit jamais : dès qu'un
# deuxième chargement de page (home puis fiche produit) a lieu dans la même
# session navigateur, le HTML renvoyé est tronqué avant cette section -
# scroll, délai, page dédiée, rien n'y change (confirmé par sondage). Une
# simple requête HTTP (requests + BeautifulSoup) reçoit le HTML complet,
# où la section contient un <table> classique <td>label</td><td>valeur</td>.
# ─────────────────────────────────────────────────────────────────────────────

MCHALE_HOME = "https://www.mchale.net/"
_MCHALE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


def _mchale_product_links() -> set:
    resp = requests.get(MCHALE_HOME, headers=_MCHALE_HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(MCHALE_HOME, a["href"])
        u = urlparse(href)
        if "mchale.net" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) == 2 and segments[0] == "products":
            links.add(href.split("?")[0].split("#")[0])
    return links


def _parse_mchale_spec_table(soup: BeautifulSoup) -> dict:
    """La section specs (classe contenant "spec"/"technical") contient un
    <table> label/valeur classique ; les autres <table> de la page (listes
    de points forts, etc.) n'en font pas partie et doivent être ignorées."""
    container = soup.select_one("[class*='spec' i], [class*='technical' i]")
    if not container:
        return {}
    table = container.find("table")
    if not table:
        return {}
    specs = {}
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) == 2:
            k, v = clean(cells[0].get_text()), clean(cells[1].get_text())
            if k and v:
                specs[k] = v
    return specs


def scrape_mchale(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles McHale non encore présentes dans Neon."""
    machines = []
    try:
        product_links = _mchale_product_links()
    except Exception as e:
        log.warning(f"  McHale inaccessible : {e}")
        return machines

    log.info(f"  McHale → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            resp = requests.get(url, headers=_MCHALE_HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        specs = _parse_mchale_spec_table(soup)
        if not specs:
            continue

        m = Machine()
        m.brand = "McHale"
        m.name = clean(soup.title.get_text()).split("–")[0].strip() if soup.title else ""
        m.category = normaliser_categorie(url)
        m.sourceUrl = url
        m.statut = "active"
        m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)

        if not m.name or len(m.name) < 2:
            continue

        key = f"{m.brand}|{m.name}|{m.variant}"
        if key in existing_keys:
            continue

        machines.append(m)
        existing_keys.add(key)
        log.info(f"    [{i}/{len(product_links)}] ✓ {m.name}")
        time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Kemper — kemper-stadtlohn.de (becs de récolte maïs)
# Structure : pas de <table>, mais un bloc "Données techniques" où chaque
# attribut est suivi de sa valeur sur la ligne suivante (valeur = nombre +
# unité, ex. "LONGUEUR" puis "1.60M").
# ─────────────────────────────────────────────────────────────────────────────

KEMPER_HOME = "https://www.kemper-stadtlohn.de/fr"


def _kemper_product_links(page: Page) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "kemper-stadtlohn.de" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) >= 3 and segments[0] == "fr" and segments[1] == "produkte" and "uebersicht" not in segments[-1]:
            links.add(href.split("?")[0].split("#")[0])
    return links


def _parse_label_next_line_spec_block(text: str) -> dict:
    """Un bloc specs Kemper alterne label et valeur sur des lignes
    successives ; seule une ligne "nombre + unité" confirme une vraie
    paire (ex. "LONGUEUR" suivi de "1.60M")."""
    lines = [l.strip() for l in text.split("\n")]
    specs = {}
    for i in range(len(lines) - 1):
        label, valeur = lines[i], lines[i + 1]
        if not label or not valeur:
            continue
        if re.match(r"^[\d.,]+\s*(m|cm|mm|kg|t|l)$", valeur, re.I):
            specs[label.lower().capitalize()] = valeur
    return specs


def scrape_kemper(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles Kemper non encore présentes dans Neon."""
    machines = []
    try:
        page.goto(KEMPER_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
    except Exception as e:
        log.warning(f"  Kemper inaccessible : {e}")
        return machines

    product_links = _kemper_product_links(page)
    log.info(f"  Kemper → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        spec_blocks = page.query_selector_all("[class*='spec' i], [class*='technical' i], [class*='daten' i]")
        specs = {}
        for block in spec_blocks:
            specs.update(_parse_label_next_line_spec_block(block.inner_text()))

        if not specs:
            continue

        m = Machine()
        m.brand = "Kemper"
        m.name = clean(page.title()).split("|")[0].strip()
        m.category = normaliser_categorie(url)
        m.sourceUrl = url
        m.statut = "active"
        m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)

        if not m.name or len(m.name) < 2:
            continue

        key = f"{m.brand}|{m.name}|{m.variant}"
        if key in existing_keys:
            continue

        machines.append(m)
        existing_keys.add(key)
        log.info(f"    [{i}/{len(product_links)}] ✓ {m.name}")
        time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Pöttinger — poettinger.at
# La page catégorie (/produkte/kategorie/<code>/<slug>) liste directement les
# fiches produit (/produkte/detail/<slug>/<nom>) : pas de crawl à 3 niveaux.
# Une fiche produit a un ou plusieurs <table>, une colonne par modèle de la
# gamme — certaines séries à plusieurs lignes de finition (ex. "Alpha Motion")
# étalent leurs modèles sur 2+ tables distinctes qu'il faut toutes parcourir
# (bug corrigé : seule tables[0] était lue, ce qui faisait disparaître les
# modèles des tables suivantes). Chaque table reste compatible avec le parser
# générique _machines_from_wide_table.
# ─────────────────────────────────────────────────────────────────────────────

POTTINGER_CATEGORIES = {
    "Faucheuses": "https://www.poettinger.at/fr_be/produkte/kategorie/mw/faucheuses",
    "Faneuses": "https://www.poettinger.at/fr_be/produkte/kategorie/zk/faneuses",
    "Technique d'andainage": "https://www.poettinger.at/fr_be/produkte/kategorie/sk/technique-dandainage",
    "Remorques autochargeuses": "https://www.poettinger.at/fr_be/produkte/kategorie/lw/remorques-autochargeuses",
    "Presse à balles rondes": "https://www.poettinger.at/fr_be/produkte/kategorie/rp/presse-a-balles-rondes",
    "Autres produits fenaison": "https://www.poettinger.at/fr_be/produkte/kategorie/gs/autres-produits-fenaison",
    "Charrues": "https://www.poettinger.at/fr_be/produkte/kategorie/pf/charrues",
    "Déchaumeurs à dents": "https://www.poettinger.at/fr_be/produkte/kategorie/gr/dechaumeurs-a-dents",
    "Déchaumeurs à disques": "https://www.poettinger.at/fr_be/produkte/kategorie/se/dechaumeurs-a-disques",
    "Herses rotatives": "https://www.poettinger.at/fr_be/produkte/kategorie/ke/herses-rotatives",
    "Combinés compacts": "https://www.poettinger.at/fr_be/produkte/kategorie/kk/combines-compacts",
    "Semoirs": "https://www.poettinger.at/fr_be/produkte/kategorie/sm/semoirs",
    "Outils d'entretien des cultures": "https://www.poettinger.at/fr_be/produkte/kategorie/kp/outils-dentretien-des-cultures",
    "Autres produits culture": "https://www.poettinger.at/fr_be/produkte/kategorie/bs/autres-produits-culture_",
}


def _pottinger_product_links(page: Page) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "poettinger.at" not in u.netloc:
            continue
        if "/produkte/detail/" in u.path:
            links.add(href.split("?")[0].split("#")[0])
    return links


def scrape_pottinger(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles Pöttinger non encore présentes dans Neon."""
    machines = []

    for category_name, category_url in POTTINGER_CATEGORIES.items():
        try:
            page.goto(category_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
        except Exception as e:
            log.warning(f"  Pöttinger ({category_name}) inaccessible : {e}")
            continue

        product_links = _pottinger_product_links(page)
        log.info(f"  Pöttinger ({category_name}) → {len(product_links)} fiches modèles trouvées")
        category = normaliser_categorie(category_url, category_name)

        for i, url in enumerate(sorted(product_links), 1):
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
            except Exception as e:
                log.warning(f"    Erreur {url} → {e}")
                continue

            tables = page.query_selector_all("table")
            if not tables:
                continue

            range_name = clean(page.title()).split("|")[0].strip()

            # Certaines fiches produit (ex. séries à plusieurs lignes de finition
            # comme "Alpha Motion") ont PLUSIEURS <table>, chacune couvrant un
            # sous-ensemble de modèles différents (constaté : 2 tables donnant
            # 5 modèles distincts au total) — il faut donc toutes les parcourir,
            # pas seulement la première.
            for table in tables:
                for candidats in _machines_from_wide_table(table, "Pöttinger", category, range_name, url):
                    key = f"{candidats.brand}|{candidats.name}|{candidats.variant}"
                    if key in existing_keys:
                        continue
                    machines.append(candidats)
                    existing_keys.add(key)
                    log.info(f"    [{i}/{len(product_links)}] ✓ {candidats.name}")

            time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Grimme — grimme.com (arracheuses/tamiseuses pommes de terre)
# Fiches produit sur le sous-domaine products.grimme.com, tableau large
# classique (une colonne par modèle), compatible avec le parser générique.
# ─────────────────────────────────────────────────────────────────────────────

GRIMME_HOME = "https://www.grimme.com/fr/"


def _grimme_product_links(page: Page) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "grimme.com" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) == 3 and segments[1] == "p":
            links.add(href.split("?")[0].split("#")[0])
    return links


def scrape_grimme(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles Grimme non encore présentes dans Neon."""
    machines = []
    try:
        page.goto(GRIMME_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
    except Exception as e:
        log.warning(f"  Grimme inaccessible : {e}")
        return machines

    product_links = _grimme_product_links(page)
    log.info(f"  Grimme → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        tables = page.query_selector_all("table")
        if not tables:
            continue

        category = normaliser_categorie(url, clean(page.title()))
        range_name = clean(page.title()).split("|")[0].strip()

        for candidats in _machines_from_wide_table(tables[0], "Grimme", category, range_name, url):
            key = f"{candidats.brand}|{candidats.name}|{candidats.variant}"
            if key in existing_keys:
                continue
            machines.append(candidats)
            existing_keys.add(key)
            log.info(f"    [{i}/{len(product_links)}] ✓ {candidats.name}")

        time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Väderstad — vaderstad.com (travail du sol, semoirs)
# Fiches produit trouvées directement depuis la home (liens /fr/... à au
# moins 3 segments). Le tableau specs a un format particulier : la ligne
# d'en-tête ne porte que la largeur (ex. "400"), pas le nom complet du
# modèle — il faut préfixer avec le nom de la gamme (ex. "Opus 400").
# ─────────────────────────────────────────────────────────────────────────────

VADERSTAD_HOME = "https://www.vaderstad.com/fr/"


def _vaderstad_product_links(page: Page) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "vaderstad.com" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) >= 3 and segments[0] == "fr":
            links.add(href.split("?")[0].split("#")[0])
    return links


def scrape_vaderstad(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles Väderstad non encore présentes dans Neon."""
    machines = []
    try:
        page.goto(VADERSTAD_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
    except Exception as e:
        log.warning(f"  Väderstad inaccessible : {e}")
        return machines

    product_links = _vaderstad_product_links(page)
    log.info(f"  Väderstad → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        tables = page.query_selector_all("table")
        if not tables:
            continue

        range_name = clean(page.title()).split("|")[0].strip()
        category = normaliser_categorie(url, range_name)
        family = range_name.split(" - ")[0].strip() if range_name else ""

        models = _parse_wide_models_table(tables[0])
        for raw_name, specs in models.items():
            if not specs or len(raw_name) < 1:
                continue
            m = Machine()
            m.brand = "Väderstad"
            m.range = range_name
            m.name = f"{family} {raw_name}".strip() if family and family not in raw_name else raw_name
            m.category = category
            m.sourceUrl = url
            m.statut = "active"
            m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)

            key = f"{m.brand}|{m.name}|{m.variant}"
            if key in existing_keys:
                continue
            machines.append(m)
            existing_keys.add(key)
            log.info(f"    [{i}/{len(product_links)}] ✓ {m.name}")

        time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Lemken — lemken.com (travail du sol, semis)
# Crawl à 2 niveaux : catégorie -> fiche produit. Tableau large classique.
# ─────────────────────────────────────────────────────────────────────────────

LEMKEN_CATEGORIES = {
    "Travail du sol": "https://lemken.com/fr-fr/machines-agricoles/travail-du-sol",
    "Semis": "https://lemken.com/fr-fr/machines-agricoles/semis",
    "Protection des cultures": "https://lemken.com/fr-fr/machines-agricoles/protection-des-cultures",
}


def _lemken_product_links(page: Page, base_path: str) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "lemken.com" not in u.netloc:
            continue
        if u.path.rstrip("/").startswith(base_path) and u.path.rstrip("/") != base_path:
            links.add(href.split("?")[0].split("#")[0])
    return links


def scrape_lemken(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles Lemken non encore présentes dans Neon."""
    machines = []

    for category_name, category_url in LEMKEN_CATEGORIES.items():
        base_path = urlparse(category_url).path
        try:
            page.goto(category_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
        except Exception as e:
            log.warning(f"  Lemken ({category_name}) inaccessible : {e}")
            continue

        product_links = _lemken_product_links(page, base_path)
        log.info(f"  Lemken ({category_name}) → {len(product_links)} fiches trouvées")
        category = normaliser_categorie(category_url, category_name)

        for i, url in enumerate(sorted(product_links), 1):
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
            except Exception as e:
                log.warning(f"    Erreur {url} → {e}")
                continue

            tables = page.query_selector_all("table")
            if not tables:
                continue

            range_name = clean(page.title()).split("|")[0].strip()

            for candidats in _machines_from_wide_table(tables[0], "Lemken", category, range_name, url):
                key = f"{candidats.brand}|{candidats.name}|{candidats.variant}"
                if key in existing_keys:
                    continue
                machines.append(candidats)
                existing_keys.add(key)
                log.info(f"    [{i}/{len(product_links)}] ✓ {candidats.name}")

            time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Kuhn — kuhn.fr
# Crawl par catégories (grande culture, fourrages, élevage, paysage).
# Format de tableau particulier : chaque section de specs est scindée en
# deux <table> consécutives (une colonne de libellés, avec une 1ère ligne
# vide en coin, + une table de données dont la 1ère ligne porte les noms
# de modèles) — répété section par section sur la même fiche, contrairement
# au tableau large classique à une seule table.
# ─────────────────────────────────────────────────────────────────────────────

KUHN_CATEGORIES = {
    "Travail du sol": "https://www.kuhn.fr/grande-culture/materiels-de-travail-du-sol",
    "Semis": "https://www.kuhn.fr/grande-culture/semoirs",
    "Fertilisation": "https://www.kuhn.fr/grande-culture/distributeurs-dengrais",
    "Pulvérisation": "https://www.kuhn.fr/grande-culture/pulverisateurs",
    "Désherbage mécanique": "https://www.kuhn.fr/grande-culture/desherbage-mecanique",
    "Broyage grande culture": "https://www.kuhn.fr/grande-culture/broyeurs",
    "Fauche": "https://www.kuhn.fr/herbe-fourrages/faucheuses",
    "Fenaison": "https://www.kuhn.fr/herbe-fourrages/faneurs",
    "Andainage": "https://www.kuhn.fr/herbe-fourrages/andaineurs",
    "Pressage": "https://www.kuhn.fr/herbe-fourrages/presses",
    "Enrubannage": "https://www.kuhn.fr/herbe-fourrages/enrubanneuses",
    "Broyage polyvalent": "https://www.kuhn.fr/herbe-fourrages/broyeurs-polyvalents",
    "Désilage-distribution": "https://www.kuhn.fr/elevage/desileuses-distributrices",
    "Paillage": "https://www.kuhn.fr/elevage/pailleuses-et-pailleuses-distributrices",
    "Désilage-paillage": "https://www.kuhn.fr/elevage/desileuses-pailleuses",
    "Mélange traîné": "https://www.kuhn.fr/elevage/melangeuses-trainees",
    "Mélange automoteur": "https://www.kuhn.fr/elevage/melangeuses-automotrices",
    "Mélange stationnaire": "https://www.kuhn.fr/elevage/melangeuses-stationnaires",
    "Entretien du paysage": "https://www.kuhn.fr/paysage-voirie/materiels-dentretien-du-paysage",
    "Broyage paysage": "https://www.kuhn.fr/paysage-voirie/broyeurs",
}


def _kuhn_product_links(page: Page, base_path: str) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "kuhn.fr" not in u.netloc:
            continue
        if u.path.rstrip("/").startswith(base_path) and u.path.rstrip("/") != base_path:
            links.add(href.split("?")[0].split("#")[0])
    return links


def _parse_kuhn_spec_tables(tables) -> dict:
    """Les specs Kuhn sont scindées en paires de tables consécutives : une
    table à 1 colonne (libellés, 1ère ligne vide en coin) et une table de
    données (1ère ligne = noms de modèles, lignes suivantes = valeurs
    alignées sur les libellés de la table jumelle)."""
    result: dict = {}
    model_names: list = []
    for i in range(0, len(tables) - 1, 2):
        label_rows = tables[i].query_selector_all("tr")
        data_rows = tables[i + 1].query_selector_all("tr")
        if not data_rows:
            continue
        header_cells = data_rows[0].query_selector_all("td, th")
        header = [clean(c.inner_text()) for c in header_cells]
        if not any(header):
            continue
        if not model_names:
            model_names = header
            for name in model_names:
                if name:
                    result.setdefault(name, {})
        for row_idx in range(1, min(len(label_rows), len(data_rows))):
            label_cells = label_rows[row_idx].query_selector_all("td, th")
            label = clean(label_cells[0].inner_text()) if label_cells else ""
            if not label:
                continue
            value_cells = data_rows[row_idx].query_selector_all("td, th")
            for col_idx, name in enumerate(model_names):
                if not name or col_idx >= len(value_cells):
                    continue
                val = clean(value_cells[col_idx].inner_text())
                if val:
                    result[name][label] = val
    return result


def scrape_kuhn(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles Kuhn non encore présentes dans Neon."""
    machines = []

    for category_name, category_url in KUHN_CATEGORIES.items():
        base_path = urlparse(category_url).path
        try:
            page.goto(category_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        except Exception as e:
            log.warning(f"  Kuhn ({category_name}) inaccessible : {e}")
            continue

        product_links = _kuhn_product_links(page, base_path)
        log.info(f"  Kuhn ({category_name}) → {len(product_links)} fiches trouvées")
        category = normaliser_categorie(category_url, category_name)

        for i, url in enumerate(sorted(product_links), 1):
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                for _ in range(6):
                    page.mouse.wheel(0, 1500)
                    page.wait_for_timeout(250)
            except Exception as e:
                log.warning(f"    Erreur {url} → {e}")
                continue

            tables = page.query_selector_all("table")
            if len(tables) < 2:
                continue

            range_name = clean(page.title()).split("|")[0].strip()
            models = _parse_kuhn_spec_tables(tables)

            for name, specs in models.items():
                if not specs or len(name) < 2:
                    continue
                key = f"Kuhn|{name}|"
                if key in existing_keys:
                    continue
                m = Machine()
                m.brand = "Kuhn"
                m.range = range_name
                m.name = name
                m.category = category
                m.sourceUrl = url
                m.statut = "active"
                m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
                machines.append(m)
                existing_keys.add(key)
                log.info(f"    [{i}/{len(product_links)}] ✓ {name}")

            time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# JCB — jcb.com
# JCB vend surtout des engins de chantier (pelles, chargeuses-pelleteuses,
# compacteurs, nacelles, chariots élévateurs industriels, groupes
# électrogènes...) ; seules les catégories ci-dessous sont de l'équipement
# agricole (signalé par l'utilisateur : des produits non-agricoles étaient
# remontés). Tableau large classique (colonne 0 = attribut, en-tête = codes
# modèles), compatible avec le parser générique déjà utilisé pour
# Pöttinger/Lemken/Grimme.
# ─────────────────────────────────────────────────────────────────────────────

JCB_CATEGORIES = {
    "Télescopiques rotatifs": "https://www.jcb.com/fr-FR/products/machines/rotating-telehandlers/",
    "Télescopiques": "https://www.jcb.com/fr-FR/products/machines/telescopic/",
    "Télescopiques articulés": "https://www.jcb.com/fr-FR/products/machines/telescopic-articules/",
    "Tracteurs": "https://www.jcb.com/fr-FR/products/machines/tracteurs/",
}


def _jcb_product_links(page: Page, base_path: str) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "jcb.com" not in u.netloc:
            continue
        if u.path.rstrip("/").startswith(base_path.rstrip("/")) and u.path.rstrip("/") != base_path.rstrip("/"):
            links.add(href.split("?")[0].split("#")[0])
    return links


def scrape_jcb(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles JCB non encore présentes dans Neon."""
    machines = []

    for category_name, category_url in JCB_CATEGORIES.items():
        base_path = urlparse(category_url).path
        try:
            page.goto(category_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        except Exception as e:
            log.warning(f"  JCB ({category_name}) inaccessible : {e}")
            continue

        product_links = _jcb_product_links(page, base_path)
        log.info(f"  JCB ({category_name}) → {len(product_links)} fiches trouvées")
        category = normaliser_categorie(category_url, category_name)

        for i, url in enumerate(sorted(product_links), 1):
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
            except Exception as e:
                log.warning(f"    Erreur {url} → {e}")
                continue

            tables = page.query_selector_all("table")
            if not tables:
                continue

            range_name = clean(page.title()).split("|")[0].strip()

            for candidats in _machines_from_wide_table(tables[0], "JCB", category, range_name, url):
                key = f"{candidats.brand}|{candidats.name}|{candidats.variant}"
                if key in existing_keys:
                    continue
                machines.append(candidats)
                existing_keys.add(key)
                log.info(f"    [{i}/{len(product_links)}] ✓ {candidats.name}")

            time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Valtra — valtra.fr (tracteurs)
# Une page par série (pas de crawl catégorie -> produit). Le tableau specs
# est "inversé" par rapport au format large classique : chaque LIGNE est un
# modèle (ex. "T145"), avec un en-tête sur 2 lignes (regroupement + unité,
# ex. "PUISSANCE MAX." -> "CH"/"kW"). On utilise la dernière ligne d'en-tête
# (la plus fine) et on désambiguïse les libellés répétés (ex. deux "CH").
# ─────────────────────────────────────────────────────────────────────────────

VALTRA_SERIES = {
    "Série A": "https://www.valtra.fr/produits/seriea.html",
    "Série F": "https://www.valtra.fr/produits/serief.html",
    "Série G": "https://www.valtra.fr/produits/serieg.html",
    "Série N": "https://www.valtra.fr/produits/serien.html",
    "Série T": "https://www.valtra.fr/produits/seriet.html",
    "Série Q": "https://www.valtra.fr/produits/serieq.html",
    "Série S": "https://www.valtra.fr/produits/series.html",
}

_VALTRA_MODEL_RE = re.compile(r"^[A-Za-z]{1,4}\s?-?\d")


def _parse_valtra_series_table(table) -> dict:
    rows = table.query_selector_all("tr")
    if not rows:
        return {}

    header_rows = []
    data_start = None
    data_cell_count = None
    for idx, row in enumerate(rows):
        cells = row.query_selector_all("td, th")
        texts = [clean(c.inner_text()) for c in cells]
        first = texts[0] if texts else ""
        if first and _VALTRA_MODEL_RE.match(first):
            data_start = idx
            data_cell_count = len(texts)
            break
        header_rows.append(texts)

    if data_start is None or not header_rows or not data_cell_count:
        return {}

    # Certaines pages (ex. série F) ont un en-tête imbriqué sur plusieurs
    # lignes fragmentées/quasi-vides (rowspan/colspan) qu'on ne peut pas
    # reconstruire fiablement en lisant les <tr> un par un. On ne garde que
    # les lignes d'en-tête dont le nombre de cellules correspond exactement
    # aux lignes de données : mieux vaut ne rien extraire de ces pages que
    # produire des specs mal alignées (ex. une puissance associée au mauvais
    # libellé).
    aligned_headers = [h for h in header_rows if len(h) == data_cell_count and any(h)]
    if not aligned_headers:
        return {}
    header = aligned_headers[-1]
    seen: dict = {}
    labels = []
    for i, h in enumerate(header):
        label = h or f"col{i}"
        if label in seen:
            seen[label] += 1
            label = f"{label} ({seen[label]})"
        else:
            seen[label] = 1
        labels.append(label)

    result = {}
    for row in rows[data_start:]:
        cells = row.query_selector_all("td, th")
        texts = [clean(c.inner_text()) for c in cells]
        if not texts or not texts[0]:
            continue
        model_name = texts[0]
        specs = {}
        for i, val in enumerate(texts[1:], start=1):
            if i < len(labels) and val:
                specs[labels[i]] = val
        if specs:
            result[model_name] = specs
    return result


def scrape_valtra(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les modèles Valtra non encore présents dans Neon."""
    machines = []

    for series_name, url in VALTRA_SERIES.items():
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            for _ in range(6):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(300)
        except Exception as e:
            log.warning(f"  Valtra ({series_name}) inaccessible : {e}")
            continue

        tables = page.query_selector_all("table")
        if not tables:
            continue

        category = normaliser_categorie("tracteur")
        models = _parse_valtra_series_table(tables[0])
        log.info(f"  Valtra ({series_name}) → {len(models)} modèles trouvés")

        for name, specs in models.items():
            if not specs or len(name) < 2:
                continue
            key = f"Valtra|{name}|"
            if key in existing_keys:
                continue
            m = Machine()
            m.brand = "Valtra"
            m.range = series_name
            m.name = name
            m.category = category
            m.sourceUrl = url
            m.statut = "active"
            m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
            machines.append(m)
            existing_keys.add(key)
            log.info(f"    ✓ {name}")

        time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# John Deere — deere.fr
# Catalogue actuel uniquement (pas TractorData, désactivé pour cette marque
# car son historique complet est bien trop volumineux). Le site a deux
# espaces d'URL pour la même arborescence : "/produits-et-solutions/..."
# (catégories) et "/produits-solutions/..." (catégories ET fiches modèles
# — les fiches modèles ont un suffixe de code aléatoire, ex.
# ".../2032r-tracteur-compact-mtuzmurn"). La profondeur avant d'atteindre
# une vraie fiche modèle varie selon la famille (2 à 3 niveaux), donc on
# crawle récursivement et on ne garde que les pages dont le tableau de
# specs est reconnaissable, plutôt que de fixer une profondeur fixe.
# Format de tableau specific : chaque ligne a une seule cellule contenant
# "libellé\n\nvaleur".
# ─────────────────────────────────────────────────────────────────────────────

JOHNDEERE_CATEGORIES = {
    "Tracteurs": "https://www.deere.fr/fr-fr/produits-et-solutions/tracteurs",
    "Récolte": "https://www.deere.fr/fr-fr/produits-et-solutions/recolte",
    "Tondeuses": "https://www.deere.fr/fr-fr/produits-et-solutions/tondeuses",
    "Gator": "https://www.deere.fr/fr-fr/produits-et-solutions/vehicules-utilitaires-gator",
    "Foin et fourrage": "https://www.deere.fr/fr-fr/produits-et-solutions/equipement-pour-le-foin-et-le-fourrage",
}

# Profondeur maximale de crawl sous une catégorie (limite le temps total
# si le site a une arborescence anormalement profonde ou cyclique).
_JOHNDEERE_MAX_DEPTH = 3


def _johndeere_sub_links(page, scope_segment: str) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "deere.fr" not in u.netloc:
            continue
        if "/produits-solutions/" not in href and "/produits-et-solutions/" not in href:
            continue
        if scope_segment not in u.path:
            continue
        links.add(href.split("?")[0].split("#")[0])
    return links


def _parse_johndeere_spec_tables(tables) -> dict:
    """Chaque ligne pertinente a une seule cellule au format
    "libellé\\n\\nvaleur" (deux sauts de ligne entre le libellé et la
    valeur). Les autres tables/lignes de la page (mise en page, galeries)
    ne matchent pas ce format et sont ignorées."""
    specs: dict = {}
    for table in tables:
        for row in table.query_selector_all("tr"):
            cells = row.query_selector_all("td, th")
            if len(cells) != 1:
                continue
            raw = cells[0].inner_text()
            parts = [clean(p) for p in raw.split("\n\n") if clean(p)]
            if len(parts) != 2:
                continue
            label, value = parts
            if not label or not value:
                continue
            if label in specs:
                n = 2
                while f"{label} ({n})" in specs:
                    n += 1
                label = f"{label} ({n})"
            specs[label] = value
    return specs


def scrape_johndeere(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles John Deere non encore présentes dans Neon."""
    machines = []

    for category_name, category_url in JOHNDEERE_CATEGORIES.items():
        scope_segment = urlparse(category_url).path.rstrip("/").rsplit("/", 1)[-1]
        visited: set = set()
        to_visit: list = [(category_url, 0)]
        found = 0

        while to_visit:
            url, depth = to_visit.pop()
            if url in visited:
                continue
            visited.add(url)

            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                for _ in range(6):
                    page.mouse.wheel(0, 2000)
                    page.wait_for_timeout(250)
            except Exception as e:
                log.warning(f"    Erreur {url} → {e}")
                continue

            tables = page.query_selector_all("table")
            specs = _parse_johndeere_spec_tables(tables)

            if len(specs) >= 3:
                title = clean(page.title()).split("|")[0].strip()
                # Le titre est "<modèle complet> <mot générique de catégorie>"
                # (ex. "7R 330 Tracteur", "2032R Tracteur compact") : on
                # coupe au premier mot générique connu pour garder tout
                # l'identifiant du modèle (ex. "7R 330", pas juste "7R" —
                # sinon deux variantes de puissance de la même série
                # entreraient en collision sur la même clé).
                name = re.split(
                    r"\b(?:Tracteur|Moissonneuse|Tondeuse|Gator|Ensileuse|Presse|Faucheuse)\b",
                    title,
                    maxsplit=1,
                    flags=re.IGNORECASE,
                )[0].strip()
                if not name:
                    name = title.split(" ")[0] if title else ""
                if not name or len(name) < 2:
                    continue
                key = f"John Deere|{name}|"
                if key in existing_keys:
                    continue
                category = normaliser_categorie(category_name, url, title)
                m = Machine()
                m.brand = "John Deere"
                m.range = title
                m.name = name
                m.category = category
                m.sourceUrl = url
                m.statut = "active"
                m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
                machines.append(m)
                existing_keys.add(key)
                found += 1
                log.info(f"    ✓ {name}")
            elif depth < _JOHNDEERE_MAX_DEPTH:
                for link in _johndeere_sub_links(page, scope_segment):
                    if link not in visited:
                        to_visit.append((link, depth + 1))

            time.sleep(random.uniform(0.5, 1.2))

        log.info(f"  John Deere ({category_name}) → {found} machines trouvées")

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Kubota (ke.kubota-eu.com) : catalogue France sur un sous-domaine dédié
# (kubota-eu.com/fr redirige avec un certificat invalide, kubota.com est le
# site corporate global). Les fiches produit n'ont pas de vraies <table>
# HTML : les caractéristiques sont dans un div.models-table stylé en
# tableau (.row.thead pour l'en-tête, .row pour chaque variante). Chaque
# cellule contient en plus un span.col-title parasite dont le texte est
# une clé i18n mal alignée (ex. "Modello", "Hubraum / Zylinder" pour des
# colonnes françaises) : il faut le retirer pour ne garder que la valeur
# réelle en fin de cellule.
# ─────────────────────────────────────────────────────────────────────────────

KUBOTA_CATEGORIES = {
    "Tracteurs agricoles": "https://ke.kubota-eu.com/agriculture/fr/product-category/tracteurs-agricoles/",
    "Tracteurs spécialisés": "https://ke.kubota-eu.com/agriculture/fr/product-category/tracteurs-specialises/",
    "Chargeurs frontaux": "https://ke.kubota-eu.com/agriculture/fr/product-category/chargeurs-frontaux/",
    "Véhicules utilitaires": "https://ke.kubota-eu.com/agriculture/fr/product-category/vehicules-utilitaires/",
    "Manutention": "https://ke.kubota-eu.com/agriculture/fr/product-category/manutention/",
}


def _kubota_product_links(page: Page, category_url: str) -> set:
    page.goto(category_url, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    for _ in range(8):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(250)
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        if "kubota-eu.com" not in href:
            continue
        if "/agriculture/fr/products/" not in href:
            continue
        clean_href = href.split("?")[0].split("#")[0]
        if clean_href.rstrip("/").endswith("/products"):
            continue
        links.add(clean_href)
    return links


def _parse_kubota_models_table(container) -> dict:
    rows = container.query_selector_all(":scope > .row")
    header: list = []
    data_rows = []
    for row in rows:
        cls = row.get_attribute("class") or ""
        cols = row.query_selector_all(":scope > .col")
        if "thead" in cls:
            header = [clean(c.inner_text()) for c in cols]
        else:
            data_rows.append(cols)
    if not header or not data_rows:
        return {}

    decl_idx = header.index("Déclinaison") if "Déclinaison" in header else None

    result: dict = {}
    for cols in data_rows:
        values = []
        for c in cols:
            title_el = c.query_selector(".col-title")
            title_txt = clean(title_el.inner_text()) if title_el else ""
            full_txt = clean(c.inner_text())
            if title_txt and full_txt.startswith(title_txt):
                val = full_txt[len(title_txt):].strip()
            else:
                val = full_txt
            values.append(val)
        if not values or not values[0]:
            continue

        model_name = values[0]
        if decl_idx is not None and decl_idx < len(values) and values[decl_idx]:
            declinaison = values[decl_idx]
            # Certaines fiches (ex. gamme "N" spécialisée) fusionnent les
            # variantes Arceau et Cabine dans une seule ligne au lieu de
            # deux lignes séparées (comme le fait le reste du site) : les
            # valeurs des autres colonnes sont alors concaténées sans
            # séparateur (ex. "94 ch96 ch") et impossibles à attribuer de
            # façon fiable à l'une ou l'autre variante. On ignore la ligne
            # plutôt que produire des specs erronées.
            if "Arceau" in declinaison and "Cabine" in declinaison:
                continue
            model_name = f"{model_name} {declinaison}"

        specs = {}
        for i, val in enumerate(values[1:], start=1):
            if i < len(header) and val:
                specs[header[i]] = val
        if not specs:
            continue

        key = model_name
        if key in result:
            n = 2
            while f"{key} ({n})" in result:
                n += 1
            key = f"{key} ({n})"
        result[key] = specs

    return result


def scrape_kubota(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape le catalogue France de Kubota (ke.kubota-eu.com)."""
    machines = []

    for category_name, category_url in KUBOTA_CATEGORIES.items():
        try:
            links = _kubota_product_links(page, category_url)
        except Exception as e:
            log.warning(f"  Kubota ({category_name}) erreur catégorie → {e}")
            continue

        found = 0
        for url in sorted(links):
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                for _ in range(8):
                    page.mouse.wheel(0, 2000)
                    page.wait_for_timeout(250)
            except Exception as e:
                log.warning(f"    Erreur {url} → {e}")
                continue

            container = page.query_selector(".models-table")
            if not container:
                continue
            models = _parse_kubota_models_table(container)
            if not models:
                continue

            title = clean(page.title()).split("|")[0].strip()
            category = normaliser_categorie(category_name, title, url)

            for model_name, specs in models.items():
                key = f"Kubota|{model_name}|"
                if key in existing_keys:
                    continue
                m = Machine()
                m.brand = "Kubota"
                m.range = title
                m.name = model_name
                m.category = category
                m.sourceUrl = url
                m.statut = "active"
                m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
                machines.append(m)
                existing_keys.add(key)
                found += 1
                log.info(f"    ✓ {model_name}")

            time.sleep(random.uniform(0.5, 1.2))

        log.info(f"  Kubota ({category_name}) → {found} machines trouvées")

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Krone — krone.fr (fenaison, récolte fourrage, transport)
# Toutes les fiches produit sont listées directement dans le méga-menu de la
# page /produits (une seule page à crawler, pas de catégorie par catégorie).
# Les fiches ont un tableau large classique (_machines_from_wide_table) mais
# avec deux pièges : une colonne "Configurer" (CTA répété sur chaque ligne,
# pas un modèle) et, sur certaines pages, une 2e table parasite (sélecteur
# de pays/langue) dont l'unique "modèle" est en réalité un gros bloc de texte
# CSS/pays agrégé — filtrée par une limite de longueur sur le nom.
# ─────────────────────────────────────────────────────────────────────────────

KRONE_CATALOGUE_URL = "https://www.krone.fr/produits"


def _krone_product_links(page: Page) -> set:
    page.goto(KRONE_CATALOGUE_URL, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    for _ in range(10):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(250)
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        if "krone.fr" not in href:
            continue
        u = urlparse(href)
        parts = [p for p in u.path.split("/") if p]
        if len(parts) == 3 and parts[0] == "produits":
            links.add(href.split("?")[0].split("#")[0])
    return links


def scrape_krone(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape le catalogue France de Krone (krone.fr)."""
    machines = []

    try:
        links = _krone_product_links(page)
    except Exception as e:
        log.warning(f"  Krone erreur page catalogue → {e}")
        return machines

    found = 0
    for url in sorted(links):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            for _ in range(8):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(250)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        tables = page.query_selector_all("table")
        if not tables:
            continue

        title = clean(page.title()).split("|")[0].strip()
        parts = [p for p in urlparse(url).path.split("/") if p]
        category_slug = parts[1] if len(parts) > 1 else ""
        category = normaliser_categorie(category_slug, title, url)

        for table in tables:
            page_machines = _machines_from_wide_table(table, "Krone", category, title, url)
            for m in page_machines:
                name = m.name.strip()
                if name.lower() == "configurer" or len(name) > 60 or "{" in name:
                    continue
                # Table parasite (sélecteur pays/langue en pied de page) :
                # ses libellés d'attribut sont en fait des définitions CSS
                # (ex. ".cls-1{fill:none;}..."), jamais le cas sur une vraie
                # fiche technique.
                specs_dict = json.loads(m.specs)
                if any("{" in k for k in specs_dict.keys()):
                    continue
                key = f"Krone|{m.name}|"
                if key in existing_keys:
                    continue
                machines.append(m)
                existing_keys.add(key)
                found += 1
                log.info(f"    ✓ {m.name}")

        time.sleep(random.uniform(0.5, 1.2))

    log.info(f"  Krone → {found} machines trouvées")
    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Güttler — guttler.org (rouleaux, packers, préparation du lit de semis)
# Piège découvert pendant le sondage : guttler.com appartient à un musicien
# homonyme (Ludwig Güttler), rien à voir avec le fabricant — le vrai site est
# guttler.org. La page catalogue française (/fr/produits/) ne liste qu'un
# sous-ensemble restreint du catalogue (12 produits) ; le sitemap WooCommerce
# (produits en allemand, langue par défaut) donne la liste complète, chaque
# fiche renvoyant vers sa version FR via un lien hreflang. Les fiches ont un
# vrai tableau WooCommerce/TablePress, mais au format "chaque ligne = un
# modèle" (comme Valtra), pas le format large classique — d'où un parseur
# dédié.
# ─────────────────────────────────────────────────────────────────────────────

GUTTLER_SITEMAP_URL = "https://guttler.org/wp-sitemap-posts-product-1.xml"


def _guttler_product_links(page: Page) -> set:
    """La page catalogue FR (/fr/produits/) ne liste qu'un sous-ensemble
    restreint des produits. Le sitemap WooCommerce liste tout le catalogue
    (en allemand, langue par défaut du site) ; chaque fiche produit porte un
    lien hreflang="fr" vers sa version française, utilisée quand elle existe."""
    resp = requests.get(GUTTLER_SITEMAP_URL, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    de_urls = re.findall(r"<loc>(.*?)</loc>", resp.text)

    links = set()
    for de_url in de_urls:
        try:
            page.goto(de_url, timeout=30000, wait_until="domcontentloaded")
        except Exception as e:
            log.warning(f"    Güttler erreur page {de_url} → {e}")
            continue
        fr_hrefs = page.eval_on_selector_all(
            "link[rel='alternate'][hreflang='fr']", "els => els.map(e => e.href)"
        )
        target = fr_hrefs[0] if fr_hrefs else de_url
        links.add(target.split("?")[0].split("#")[0])
    return links


def _parse_guttler_specs_table(table) -> dict:
    """Table où la 1re ligne est l'en-tête et chaque ligne suivante est un
    modèle (col 0 = nom du modèle, colonnes suivantes = valeurs)."""
    rows = table.query_selector_all("tr")
    if len(rows) < 2:
        return {}
    header = [clean(c.inner_text()) for c in rows[0].query_selector_all("td, th")]
    if not header or not header[0]:
        return {}
    result = {}
    for row in rows[1:]:
        cells = row.query_selector_all("td, th")
        if not cells:
            continue
        model_name = clean(cells[0].inner_text())
        if not model_name:
            continue
        specs = {}
        for i, cell in enumerate(cells[1:], start=1):
            if i < len(header) and header[i]:
                val = clean(cell.inner_text())
                if val:
                    specs[header[i]] = val
        if not specs:
            continue
        key = model_name
        if key in result:
            n = 2
            while f"{key} ({n})" in result:
                n += 1
            key = f"{key} ({n})"
        result[key] = specs
    return result


def scrape_guttler(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape le catalogue France de Güttler (guttler.org)."""
    machines = []

    try:
        links = _guttler_product_links(page)
    except Exception as e:
        log.warning(f"  Güttler erreur page catalogue → {e}")
        return machines

    found = 0
    for url in sorted(links):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            for _ in range(8):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(250)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        tables = page.query_selector_all("table")
        if not tables:
            continue

        title = clean(page.title()).split("–")[0].strip()
        category = normaliser_categorie(title, url)

        for table in tables:
            models = _parse_guttler_specs_table(table)
            for model_name, specs in models.items():
                key = f"Güttler|{model_name}|"
                if key in existing_keys:
                    continue
                m = Machine()
                m.brand = "Güttler"
                m.range = title
                m.name = model_name
                m.category = category
                m.sourceUrl = url
                m.statut = "active"
                m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
                machines.append(m)
                existing_keys.add(key)
                found += 1
                log.info(f"    ✓ {model_name}")

        time.sleep(random.uniform(0.5, 1.2))

    log.info(f"  Güttler → {found} machines trouvées")
    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Actisol — actisol-agri.fr (travail du sol : fissuration, déchaumage,
# strip-till, entretien des prairies, viticulture, maraîchage)
# Les pages catégorie listent directement les fiches produit (pas de
# sous-catégorie à crawler séparément). Même format de tableau que Güttler :
# 1re ligne = en-tête ("Désignation" + attributs), chaque ligne suivante =
# un modèle (col 0 = désignation, ex. "D255").
# ─────────────────────────────────────────────────────────────────────────────

ACTISOL_CATEGORIES = {
    "Grande culture": "https://actisol-agri.fr/categorie-produit/grande-culture/",
    "Viticulture": "https://actisol-agri.fr/categorie-produit/viticulture/",
    "Maraîchage": "https://actisol-agri.fr/categorie-produit/maraichage/",
    "Espace vert": "https://actisol-agri.fr/categorie-produit/espace-vert/",
}


def _actisol_product_links(page: Page, category_url: str) -> set:
    page.goto(category_url, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    for _ in range(10):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(250)
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        if "actisol-agri.fr/produit/" not in href:
            continue
        links.add(href.split("?")[0].split("#")[0])
    return links


def _parse_actisol_specs_table(table) -> dict:
    """Table où la 1re ligne est l'en-tête et chaque ligne suivante est un
    modèle (col 0 = désignation du modèle, colonnes suivantes = valeurs)."""
    rows = table.query_selector_all("tr")
    if len(rows) < 2:
        return {}
    header = [clean(c.inner_text()) for c in rows[0].query_selector_all("td, th")]
    if not header or not header[0]:
        return {}
    result = {}
    for row in rows[1:]:
        cells = row.query_selector_all("td, th")
        if not cells:
            continue
        model_name = clean(cells[0].inner_text())
        if not model_name:
            continue
        specs = {}
        for i, cell in enumerate(cells[1:], start=1):
            if i < len(header) and header[i]:
                val = clean(cell.inner_text())
                if val:
                    specs[header[i]] = val
        if not specs:
            continue
        key = model_name
        if key in result:
            n = 2
            while f"{key} ({n})" in result:
                n += 1
            key = f"{key} ({n})"
        result[key] = specs
    return result


def scrape_actisol(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape le catalogue France d'Actisol (actisol-agri.fr)."""
    machines = []

    for category_name, category_url in ACTISOL_CATEGORIES.items():
        try:
            links = _actisol_product_links(page, category_url)
        except Exception as e:
            log.warning(f"  Actisol ({category_name}) erreur catégorie → {e}")
            continue

        found = 0
        for url in sorted(links):
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                for _ in range(8):
                    page.mouse.wheel(0, 2000)
                    page.wait_for_timeout(250)
            except Exception as e:
                log.warning(f"    Erreur {url} → {e}")
                continue

            tables = page.query_selector_all("table")
            if not tables:
                continue

            title = clean(page.title()).split("-")[0].strip()
            category = normaliser_categorie(category_name, title, url)

            for table in tables:
                models = _parse_actisol_specs_table(table)
                for model_name, specs in models.items():
                    key = f"Actisol|{model_name}|"
                    if key in existing_keys:
                        continue
                    m = Machine()
                    m.brand = "Actisol"
                    m.range = title
                    m.name = model_name
                    m.category = category
                    m.sourceUrl = url
                    m.statut = "active"
                    m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
                    machines.append(m)
                    existing_keys.add(key)
                    found += 1
                    log.info(f"    ✓ {model_name}")

            time.sleep(random.uniform(0.5, 1.2))

        log.info(f"  Actisol ({category_name}) → {found} machines trouvées")

    return machines


MCCORMICK_HOME = "https://mccormick-tractors.com/fr/fr.html"
MCCORMICK_CATALOGUE_URL = "https://mccormick-tractors.com/fr/fr/produits.html"


def _mccormick_product_links(page: Page) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "mccormick-tractors.com" not in u.netloc:
            continue
        if "/fr/fr/produits/" in u.path and u.path.endswith(".html"):
            links.add(href.split("?")[0].split("#")[0])
    return links


def scrape_mccormick(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles McCormick (tracteurs) non encore présentes dans Neon."""
    machines = []
    try:
        page.goto(MCCORMICK_CATALOGUE_URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
    except Exception as e:
        log.warning(f"  McCormick inaccessible : {e}")
        return machines

    product_links = _mccormick_product_links(page)
    log.info(f"  McCormick → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        spec_items = page.query_selector_all(".product-hero-specs .spec-item")
        if not spec_items:
            continue

        specs = {}
        for item in spec_items:
            lines = [clean(t) for t in item.inner_text().split("\n") if clean(t)]
            if len(lines) >= 2:
                specs[lines[0]] = lines[1]

        name = clean(page.title()).split("|")[0].strip()
        if not name or len(name) < 2:
            continue

        key = f"McCormick|{name}|"
        if key in existing_keys:
            continue

        m = Machine()
        m.brand = "McCormick"
        m.range = name
        m.name = name
        m.category = "Tracteurs"
        m.sourceUrl = url
        m.statut = "active"
        m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
        machines.append(m)
        existing_keys.add(key)
        log.info(f"    [{i}/{len(product_links)}] ✓ {name}")

        time.sleep(random.uniform(1.0, 2.0))

    return machines


FRANQUET_HOME = "https://www.franquet.com/"
FRANQUET_CATEGORIES = [
    "https://www.franquet.com/travail-du-sol/",
    "https://www.franquet.com/desherbage-mecanique/",
    "https://www.franquet.com/equipements-pour-semis/",
    "https://www.franquet.com/materiels-recolte-betteraviere/",
]


def _franquet_product_links(page: Page, base_path: str) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "franquet.com" not in u.netloc:
            continue
        if u.path.startswith(base_path) and u.path.rstrip("/") != base_path.rstrip("/"):
            links.add(href.split("?")[0].split("#")[0])
    return links


def _franquet_table_grid(table) -> list:
    """Construit une grille 2D en développant les cellules fusionnées
    (colspan/rowspan). Les tableaux de gamme FRANQUET comparent plusieurs
    variantes d'un même produit (largeur, type de bâti...) avec des cellules
    fusionnées qui désalignent un simple comptage "une ligne = une liste de
    cellules" ; lire colSpan/rowSpan directement dans le DOM via JS est le
    seul moyen fiable de retrouver le bon alignement de colonnes."""
    return table.evaluate(
        """
        (table) => {
            const rows = Array.from(table.querySelectorAll('tr'));
            const grid = [];
            rows.forEach((row, rIdx) => {
                const cells = Array.from(row.querySelectorAll('td, th'));
                if (!grid[rIdx]) grid[rIdx] = [];
                let colIdx = 0;
                cells.forEach(cell => {
                    while (grid[rIdx][colIdx] !== undefined) colIdx++;
                    const colspan = cell.colSpan || 1;
                    const rowspan = cell.rowSpan || 1;
                    const text = cell.innerText.trim();
                    for (let r = 0; r < rowspan; r++) {
                        if (!grid[rIdx + r]) grid[rIdx + r] = [];
                        for (let c = 0; c < colspan; c++) {
                            grid[rIdx + r][colIdx + c] = text;
                        }
                    }
                    colIdx += colspan;
                });
            });
            return grid;
        }
        """
    )


def _franquet_is_titre(texte: str) -> bool:
    """Un intitulé de produit FRANQUET est toujours tout en majuscules
    (ex. 'BINEUSE BETTERAVES', 'BISYNCHRO TF'), ce qui le distingue des
    lignes d'en-tête de variante (largeurs, types...) et des lignes
    d'attribut (casse normale)."""
    return bool(texte) and texte == texte.upper() and texte != texte.lower()


def _franquet_machines_from_table(table, brand: str, category: str, source_url: str) -> list[Machine]:
    """Un tableau de gamme FRANQUET compare les variantes (largeur, type de
    bâti...) d'UN SEUL produit, dont le nom est dans la première ligne tout
    en majuscules rencontrée en partant du haut ; les lignes au-dessus sont
    des en-têtes de variante par colonne, celles en-dessous des attributs
    techniques. Une colonne = une variante = une Machine (le nom du produit
    partagé, la variante distinguant largeur/type)."""
    grid = _franquet_table_grid(table)
    if not grid:
        return []

    name_row_idx = None
    for i, row in enumerate(grid):
        cell0 = clean(row[0]) if row and row[0] else ""
        if cell0 and _franquet_is_titre(cell0):
            name_row_idx = i
            break
    if name_row_idx is None:
        return []

    name = clean(grid[name_row_idx][0])
    if name.upper().startswith("OPTION"):
        return []  # tableaux d'accessoires/options, pas des fiches machine

    n_cols = max(len(r) for r in grid)

    variant_labels = {}
    for j in range(1, n_cols):
        parts = []
        for i in range(name_row_idx + 1):
            row = grid[i]
            v = clean(row[j]) if j < len(row) and row[j] else ""
            if v and v not in parts:
                parts.append(v)
        variant_labels[j] = " ".join(parts)

    specs_per_col: dict = {}
    for row in grid[name_row_idx + 1:]:
        if not row:
            continue
        attr_name = clean(row[0]) if row[0] else ""
        if not attr_name:
            continue
        for j in range(1, len(row)):
            val = clean(row[j]) if row[j] else ""
            if val:
                specs_per_col.setdefault(j, {})[attr_name] = val

    machines = []
    for j, specs in specs_per_col.items():
        if not specs:
            continue
        m = Machine()
        m.brand = brand
        m.name = name
        m.variant = variant_labels.get(j, "")
        m.category = category
        m.sourceUrl = source_url
        m.statut = "active"
        m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
        machines.append(m)
    return machines


def scrape_franquet(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles Franquet non encore présentes dans Neon.
    Les pages de sous-catégorie contiennent plusieurs tableaux de gamme
    (un par produit), chacun comparant les variantes de ce produit."""
    machines = []

    for category_url in FRANQUET_CATEGORIES:
        base_path = urlparse(category_url).path
        category_slug = base_path.rstrip("/").split("/")[-1]

        try:
            page.goto(category_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        except Exception as e:
            log.warning(f"  Franquet ({category_slug}) inaccessible : {e}")
            continue

        product_links = _franquet_product_links(page, base_path)
        log.info(f"  Franquet ({category_slug}) → {len(product_links)} fiches trouvées")
        category = normaliser_categorie(category_slug)

        for i, url in enumerate(sorted(product_links), 1):
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                for _ in range(6):
                    page.mouse.wheel(0, 1500)
                    page.wait_for_timeout(250)
            except Exception as e:
                log.warning(f"    Erreur {url} → {e}")
                continue

            tables = page.query_selector_all("table")
            if not tables:
                continue

            for table in tables:
                for candidats in _franquet_machines_from_table(table, "Franquet", category, url):
                    key = f"{candidats.brand}|{candidats.name}|{candidats.variant}"
                    if key in existing_keys:
                        continue
                    machines.append(candidats)
                    existing_keys.add(key)
                    log.info(f"    [{i}/{len(product_links)}] ✓ {candidats.name} ({candidats.variant})")

            time.sleep(random.uniform(1.0, 2.0))

    return machines


VICON_HOME = "https://fr.vicon.eu/"


def _clean_vicon_title(raw_title: str) -> str:
    """'Vicon ANDEX 644 - Vicon' -> 'ANDEX 644'"""
    t = clean(raw_title)
    t = re.sub(r"^Vicon\s+", "", t, flags=re.I)
    t = re.sub(r"\s*-\s*Vicon\s*$", "", t, flags=re.I)
    return clean(t)


def _vicon_product_links(page: Page) -> set:
    """Une fiche modèle Vicon a toujours une URL à 3 segments :
    /categorie/sous-categorie/modele (même structure que Kverneland, même
    groupe/plateforme)."""
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "vicon.eu" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) == 3:
            links.add(href.split("?")[0].split("#")[0])
    return links


def scrape_vicon(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles Vicon (marque du groupe Kverneland) non
    encore présentes dans Neon. Même structure de site que Kverneland."""
    machines = []
    try:
        page.goto(VICON_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
    except Exception as e:
        log.warning(f"  Vicon inaccessible : {e}")
        return machines

    product_links = _vicon_product_links(page)
    log.info(f"  Vicon → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        specs = {}
        for table in page.query_selector_all("table"):
            for row in table.query_selector_all("tr"):
                cells = row.query_selector_all("td, th")
                if len(cells) >= 2:
                    k = clean(cells[0].inner_text())
                    v = clean(cells[1].inner_text())
                    if k and v:
                        specs[k] = v

        if not specs:
            continue

        segments = [s for s in urlparse(url).path.split("/") if s]
        category_slug, subcategory_slug = segments[0], segments[1]

        m = Machine()
        m.brand = "Vicon"
        # La 1ère ligne du tableau donne le nom exact du modèle ; le <title>
        # de la page combine parfois plusieurs modèles proches (ex. "705 EVO
        # - 705 VARIO") et est donc moins fiable.
        m.name = specs.pop("Caractéristiques", "") or _clean_vicon_title(page.title())
        m.category = normaliser_categorie(category_slug, subcategory_slug, m.name)
        m.subcategory = _humanize_slug(subcategory_slug)
        m.sourceUrl = url
        m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
        m.statut = "active"

        if not m.name or len(m.name) < 2:
            continue

        key = f"{m.brand}|{m.name}|{m.variant}"
        if key in existing_keys:
            continue

        machines.append(m)
        existing_keys.add(key)
        log.info(f"    [{i}/{len(product_links)}] ✓ {m.name}")
        time.sleep(random.uniform(1.0, 2.0))

    return machines


HORSCH_HOME = "https://www.horsch.com/fr/produits"
HORSCH_MAX_PAGES = 200


def _horsch_facts(page) -> dict:
    """Les fiches produit HORSCH n'ont pas de <table> : les caractéristiques
    sont regroupées dans un conteneur dont la classe contient 'fact' (ex.
    'keyfacts'), sous forme de blocs texte "label\\nvaleur" séparés par une
    ligne vide. La structure DOM interne (classes des divs) varie et n'est
    pas fiable ; le texte brut du conteneur, lui, est stable."""
    specs = {}
    try:
        container = page.wait_for_selector("[class*='fact']", timeout=6000, state="attached")
    except Exception:
        return specs
    text = container.inner_text()
    for block in text.split("\n\n"):
        lines = [clean(l) for l in block.split("\n") if clean(l)]
        if len(lines) >= 2:
            label, value = lines[0], " ".join(lines[1:])
            specs[label] = value
    return specs


def scrape_horsch(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles HORSCH (horsch.com/fr) non encore présentes
    dans Neon. Catalogue à 3 niveaux (catégorie > sous-catégorie > modèle) ;
    on descend par BFS et on reconnaît une fiche modèle à la présence du
    conteneur de caractéristiques techniques."""
    machines = []
    to_visit = [HORSCH_HOME]
    visited = set()
    found = 0

    while to_visit and len(visited) < HORSCH_MAX_PAGES:
        url = to_visit.pop()
        if url in visited:
            continue
        visited.add(url)

        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        specs = _horsch_facts(page)
        if specs:
            segments = [s for s in urlparse(url).path.split("/") if s]
            # /fr/produits/<categorie>/<sous-categorie>/<modele>
            category_slug = segments[2] if len(segments) > 2 else ""
            name = clean(page.title()).split("|")[0].strip()
            if not name or len(name) < 2:
                continue

            key = f"Horsch|{name}|"
            if key in existing_keys:
                continue

            m = Machine()
            m.brand = "Horsch"
            m.name = name
            m.category = normaliser_categorie(category_slug, name)
            m.sourceUrl = url
            m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
            m.statut = "active"
            machines.append(m)
            existing_keys.add(key)
            found += 1
            log.info(f"    [{found}] ✓ {name}")
            time.sleep(random.uniform(1.0, 2.0))
            continue  # une fiche modèle n'a pas de sous-pages produits utiles

        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        for href in hrefs:
            u = urlparse(href)
            if "horsch.com" not in u.netloc:
                continue
            if "/fr/produits/" not in u.path:
                continue
            clean_href = href.split("?")[0].split("#")[0]
            segments = [s for s in urlparse(clean_href).path.split("/") if s]
            # /fr/produits (2) / catégorie (3) / sous-catégorie (4) / modèle (5)
            if len(segments) <= 5 and clean_href not in visited:
                to_visit.append(clean_href)

    log.info(f"  Horsch → {found} machines trouvées")
    return machines


SULKY_HOME = "https://sky-agriculture.com/produits/"
SULKY_MAX_PAGES = 150


def scrape_sulky(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles Sulky (marque du groupe Burel, catalogue
    désormais publié sous sky-agriculture.com) non encore présentes dans
    Neon. Catalogue à plusieurs niveaux (catégorie > sous-catégorie éventuelle
    > fiche modèle), parcouru en DFS ; une fiche modèle est reconnue par la
    présence d'un tableau de specs au format "large" (une colonne par
    variante), déjà géré par _machines_from_wide_table."""
    machines = []
    to_visit = [SULKY_HOME]
    visited = set()
    found = 0

    while to_visit and len(visited) < SULKY_MAX_PAGES:
        url = to_visit.pop()
        if url in visited:
            continue
        visited.add(url)

        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        tables = page.query_selector_all("table")
        if tables:
            range_name = clean(page.title()).split("|")[0].strip()
            segments = [s for s in urlparse(url).path.split("/") if s]
            category_slug = segments[1] if len(segments) > 1 else ""
            category = normaliser_categorie(category_slug, range_name)
            for table in tables:
                for candidats in _machines_from_wide_table(table, "Sulky", category, range_name, url):
                    key = f"{candidats.brand}|{candidats.name}|{candidats.variant}"
                    if key in existing_keys:
                        continue
                    machines.append(candidats)
                    existing_keys.add(key)
                    found += 1
                    log.info(f"    [{found}] ✓ {candidats.name}")
            time.sleep(random.uniform(1.0, 2.0))
            continue

        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        for href in hrefs:
            u = urlparse(href)
            if "sky-agriculture.com" not in u.netloc:
                continue
            if "/produits/" not in u.path:
                continue
            clean_href = href.split("?")[0].split("#")[0]
            segments = [s for s in urlparse(clean_href).path.split("/") if s]
            if len(segments) <= 3 and clean_href not in visited:
                to_visit.append(clean_href)

    log.info(f"  Sulky (sky-agriculture.com) → {found} machines trouvées")
    return machines


BERTHOUD_GAMME_URL = "https://www.berthoud.com/gamme-grandes-cultures/"

# Pages de navigation trouvées dans le même menu que les fiches produit,
# à exclure car ce ne sont pas des machines.
BERTHOUD_EXCLUSIONS = [
    "notre-histoire", "services-et-assistance", "services-dedies",
    "solution-de-financement", "gamme-vignes", "gamme-grandes-cultures",
    "innovations-et-technologies", "contact", "la-solution-air-drive",
    "katch-panneaux-recuperateurs",
]


def _berthoud_product_links(page: Page) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "berthoud.com" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) == 1 and segments[0] not in BERTHOUD_EXCLUSIONS:
            links.add(href.split("?")[0].split("#")[0])
    return links


def scrape_berthoud(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles Berthoud (pulvérisation agricole
    professionnelle, berthoud.com) non encore présentes dans Neon. Les
    caractéristiques techniques sont sous un onglet à cliquer pour faire
    apparaître le tableau de specs ; les pages qui n'ont pas cet onglet (ou
    pas de tableau après clic) ne sont pas des fiches machine et sont
    ignorées."""
    machines = []
    try:
        page.goto(BERTHOUD_GAMME_URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
    except Exception as e:
        log.warning(f"  Berthoud inaccessible : {e}")
        return machines

    product_links = _berthoud_product_links(page)
    log.info(f"  Berthoud → {len(product_links)} fiches candidates trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        try:
            tab = page.get_by_text("Caractéristiques techniques", exact=False).first
            tab.click(timeout=3000)
            page.wait_for_timeout(2000)
        except Exception:
            continue

        specs = {}
        for table in page.query_selector_all("table"):
            for row in table.query_selector_all("tr"):
                cells = row.query_selector_all("td, th")
                if len(cells) >= 2:
                    k = clean(cells[0].inner_text())
                    v = clean(cells[1].inner_text())
                    if k and v:
                        specs[k] = v

        if not specs:
            continue

        name = clean(page.title()).split("-")[0].strip()
        if not name or len(name) < 2:
            continue

        key = f"Berthoud|{name}|"
        if key in existing_keys:
            continue

        m = Machine()
        m.brand = "Berthoud"
        m.name = name
        m.category = normaliser_categorie(name)
        m.sourceUrl = url
        m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
        m.statut = "active"
        machines.append(m)
        existing_keys.add(key)
        log.info(f"    [{i}/{len(product_links)}] ✓ {name}")
        time.sleep(random.uniform(1.0, 2.0))

    return machines


HARDI_HOME = "https://hardi.com/fr/sprayers"
HARDI_EXCLUSIONS = ["campaigns", "resale"]


def _hardi_product_links(page: Page) -> set:
    """Une fiche modèle HARDI a une URL à 4 segments :
    /fr/sprayers/<type>/<modele>. Les pages catégorie n'ont que 3 segments
    (/fr/sprayers/<type>), ce qui les exclut naturellement."""
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "hardi.com" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) != 4 or segments[:2] != ["fr", "sprayers"]:
            continue
        if segments[2] in HARDI_EXCLUSIONS or segments[3] == "technical-specifications":
            continue
        links.add(href.split("?")[0].split("#")[0])
    return links


def _accept_cookies(page) -> bool:
    """Ferme le bandeau de consentement cookies s'il est présent, pour ne
    pas bloquer les clics sur les onglets/éléments de la page."""
    for text in ["Tout accepter", "Accepter tout", "Accept all", "J'accepte", "Accepter"]:
        try:
            btn = page.get_by_text(text, exact=False).first
            if btn.is_visible(timeout=1500):
                btn.click(timeout=1500)
                page.wait_for_timeout(1000)
                return True
        except Exception:
            continue
    return False


def _hardi_specs(page) -> dict:
    """Les caractéristiques HARDI sont sous un onglet 'Spécifications
    techniques' à cliquer pour afficher le tableau (souvent multi-sections :
    capacités de cuve en colonnes, plusieurs rampes/dimensions en lignes)."""
    try:
        page.get_by_text("Spécifications techniques", exact=False).first.click(timeout=3000)
        page.wait_for_timeout(2000)
    except Exception:
        return {}

    specs = {}
    for table in page.query_selector_all("table"):
        for row in table.query_selector_all("tr"):
            cells = row.query_selector_all("td, th")
            if not cells:
                continue
            label = clean(cells[0].inner_text())
            values = [clean(c.inner_text()) for c in cells[1:]]
            values = [v for v in values if v]
            if label and values:
                specs[label] = " / ".join(values)
    return specs


def scrape_hardi(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles HARDI (pulvérisation, hardi.com/fr) non
    encore présentes dans Neon."""
    machines = []
    try:
        page.goto(HARDI_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        _accept_cookies(page)
    except Exception as e:
        log.warning(f"  Hardi inaccessible : {e}")
        return machines

    product_links = _hardi_product_links(page)
    log.info(f"  Hardi → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            _accept_cookies(page)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        # Le nom doit être capturé AVANT de cliquer sur l'onglet specs : le
        # clic modifie le <title> de la page (routage client), qui devient
        # par ex. "Spécifications techniques :: HARDI" au lieu du modèle.
        name = clean(page.title()).split("–")[0].strip()
        if not name or len(name) < 2:
            continue

        specs = _hardi_specs(page)
        if not specs:
            continue

        segments = [s for s in urlparse(url).path.split("/") if s]
        category_slug = segments[2] if len(segments) > 2 else ""

        key = f"Hardi|{name}|"
        if key in existing_keys:
            continue

        m = Machine()
        m.brand = "Hardi"
        m.name = name
        m.category = normaliser_categorie(category_slug, name)
        m.sourceUrl = url
        m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
        m.statut = "active"
        machines.append(m)
        existing_keys.add(key)
        log.info(f"    [{i}/{len(product_links)}] ✓ {name}")
        time.sleep(random.uniform(1.0, 2.0))

    return machines


ROPA_HOME = "https://www.ropa-maschinenbau.de/fr/produits/"


def _ropa_product_links(page: Page) -> set:
    """Une fiche modèle ROPA a une URL à 2 segments sous /fr/produits/ :
    /fr/produits/<famille>/<modele>/. Toutes sont listées directement sur
    la page /fr/produits/, pas de crawl récursif nécessaire."""
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "ropa-maschinenbau.de" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) == 4 and segments[:2] == ["fr", "produits"]:
            links.add(href.split("?")[0].split("#")[0])
    return links


def _ropa_specs(text: str) -> dict:
    """Les fiches produit ROPA n'ont pas de <table> pour les caractéristiques
    techniques : après clic sur l'onglet 'Caractéristiques techniques', le
    contenu est du texte libre où chaque ligne ou groupe de lignes est séparé
    par une ligne vide. Un bloc tout en majuscules est un intitulé de
    caractéristique (ex. 'LONGUEUR', 'CAPACITÉ DE TRÉMIE') ; les blocs
    suivants jusqu'au prochain intitulé sont ses valeurs (parfois plusieurs,
    ex. plusieurs largeurs selon variante), jointes par ' / '."""
    specs = {}
    label = None
    values = []
    for block in text.split("\n\n"):
        lines = [clean(l) for l in block.split("\n") if clean(l)]
        if not lines:
            continue
        block_clean = " ".join(lines)
        is_heading = block_clean == block_clean.upper() and len(block_clean) < 80
        if is_heading:
            if label and values:
                specs[label] = " / ".join(values)
            label = block_clean
            values = []
        elif label:
            values.append(block_clean)
    if label and values:
        specs[label] = " / ".join(values)
    return specs


def scrape_ropa(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles ROPA (arracheuses de betteraves et machines
    pour pommes de terre, ropa-maschinenbau.de) non encore présentes dans
    Neon."""
    machines = []
    try:
        page.goto(ROPA_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        _accept_cookies(page)
    except Exception as e:
        log.warning(f"  Ropa inaccessible : {e}")
        return machines

    product_links = _ropa_product_links(page)
    log.info(f"  Ropa → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            _accept_cookies(page)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        # Le nom doit être capturé AVANT de cliquer sur l'onglet specs : le
        # clic modifie le <title> de la page (routage client), qui devient
        # "Caractéristiques techniques" au lieu du modèle.
        name = clean(page.title()).split("|")[0].strip()
        if not name or len(name) < 2:
            continue

        try:
            page.get_by_text("CARACTÉRISTIQUES TECHNIQUES", exact=False).first.click(timeout=3000)
            page.wait_for_timeout(2000)
        except Exception:
            continue

        text = page.inner_text("body")
        idx = text.rfind("CARACTÉRISTIQUES TECHNIQUES")
        if idx == -1:
            continue
        spec_text = text[idx:]
        footer_idx = spec_text.find("SUIVEZ-NOUS SUR LES RÉSEAUX SOCIAUX")
        if footer_idx != -1:
            spec_text = spec_text[:footer_idx]
        specs = _ropa_specs(spec_text)
        if not specs:
            continue

        segments = [s for s in urlparse(url).path.split("/") if s]
        category_slug = segments[2] if len(segments) > 2 else ""

        key = f"Ropa|{name}|"
        if key in existing_keys:
            continue

        m = Machine()
        m.brand = "Ropa"
        m.name = name
        m.category = normaliser_categorie(category_slug, name)
        m.sourceUrl = url
        m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
        m.statut = "active"
        machines.append(m)
        existing_keys.add(key)
        log.info(f"    [{i}/{len(product_links)}] ✓ {name}")
        time.sleep(random.uniform(1.0, 2.0))

    log.info(f"  Ropa → {len(machines)} machines trouvées")
    return machines


SAMSON_HOME = "https://www.samson-agro.com/fr/"
SAMSON_CATEGORIES = ["epandeurs", "tonnes-a-lisier", "autres-equipements", "techniques-application"]

# Intitulés de la navigation d'en-tête/pied de page (identiques sur toutes
# les fiches), à retirer des specs car ce ne sont pas des caractéristiques.
SAMSON_FOOTER_HEADINGS = [
    "CONTACT", "SOLUTIONS", "ENTREPRISE", "SERVICE ET PIÈCES",
    "SAMSON ACADEMY", "UN PROJET ?", "SERVICES ET PIÈCES",
]


def _samson_product_links(page: Page) -> set:
    """Une fiche modèle SAMSON a une URL à 2 segments sous /fr/ :
    /fr/<categorie>/<modele>/, où <categorie> est une des catégories connues
    du catalogue (les autres pages à 2 segments sont du contenu institutionnel
    : à-propos, carrière, contact...)."""
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "samson-agro.com" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) == 3 and segments[0] == "fr" and segments[1] in SAMSON_CATEGORIES:
            links.add(href.split("?")[0].split("#")[0])
    return links


def _samson_specs(text: str) -> dict:
    """Les fiches produit SAMSON n'ont pas de <table> : le texte est composé
    de lignes, chaque ligne toute en majuscules étant un intitulé de section
    (ex. 'CONCEPTION POLYVALENTE'), suivi de phrases descriptives (valeurs)
    jusqu'à l'intitulé suivant. Contrairement à HORSCH/ROPA, les lignes ne
    sont pas séparées par une ligne vide, d'où un parsing ligne à ligne
    plutôt que par bloc."""
    specs = {}
    label = None
    values = []
    for raw_line in text.split("\n"):
        line = clean(raw_line)
        if not line:
            continue
        is_heading = line == line.upper() and len(line) < 80
        if is_heading:
            if label and values:
                specs[label] = " / ".join(values)
            label = line
            values = []
        elif label:
            values.append(line)
    if label and values:
        specs[label] = " / ".join(values)
    return specs


def scrape_samson(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles SAMSON (matériel d'épandage/tonnes à lisier,
    samson-agro.com, groupe Samson/Pichon) non encore présentes dans Neon."""
    machines = []
    try:
        page.goto(SAMSON_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        _accept_cookies(page)
    except Exception as e:
        log.warning(f"  Samson inaccessible : {e}")
        return machines

    product_links = _samson_product_links(page)
    log.info(f"  Samson → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            _accept_cookies(page)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        name = clean(page.title()).split("|")[0].strip()
        name = name.replace("Épandeurs", "").replace("Tonnes à lisier", "").strip()
        if not name or len(name) < 2:
            continue

        # Le contenu technique (CHIFFRES CLÉS, sections descriptives) est en
        # chargement différé : il ne s'affiche qu'après défilement de la page.
        for _ in range(8):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(300)
        page.wait_for_timeout(1000)

        text = page.inner_text("body")
        footer_idx = text.find("Copyright ©")
        if footer_idx != -1:
            text = text[:footer_idx]
        specs = _samson_specs(text)
        for noise_key in SAMSON_FOOTER_HEADINGS:
            specs.pop(noise_key, None)
        if not specs:
            continue

        segments = [s for s in urlparse(url).path.split("/") if s]
        category_slug = segments[1] if len(segments) > 1 else ""

        key = f"Samson|{name}|"
        if key in existing_keys:
            continue

        m = Machine()
        m.brand = "Samson"
        m.name = name
        m.category = normaliser_categorie(category_slug, name)
        m.sourceUrl = url
        m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
        m.statut = "active"
        machines.append(m)
        existing_keys.add(key)
        log.info(f"    [{i}/{len(product_links)}] ✓ {name}")
        time.sleep(random.uniform(1.0, 2.0))

    log.info(f"  Samson → {len(machines)} machines trouvées")
    return machines


BOGBALLE_MODELES_URL = "https://www.bogballe.com/fr/epandeurs-dengrais/modeles/"


def _bogballe_product_links(page: Page) -> set:
    """Une fiche modèle BOGBALLE a une URL à 1 segment sous /modeles/
    (ex. /fr/epandeurs-dengrais/modeles/m60w-plus/). Les "unités de
    contrôle" (boîtiers électroniques, pas des machines) sont dans un
    dossier séparé (/unites-de-controle/) et ne sont donc jamais
    confondues avec des épandeurs."""
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "bogballe.com" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if (
            len(segments) == 4
            and segments[:3] == ["fr", "epandeurs-dengrais", "modeles"]
            and re.fullmatch(r"[a-z0-9-]+", segments[3])
        ):
            links.add(href.split("?")[0].split("#")[0])
    return links


def _bogballe_specs(text: str) -> dict:
    """Les fiches produit BOGBALLE n'ont pas de <table> : le texte est une
    alternance stricte de blocs "intitulé" / "valeur" séparés par une ligne
    vide. Certains blocs d'intitulé contiennent un titre de section glissé
    juste avant le vrai intitulé, sur une ligne séparée au sein du même bloc
    (ex. "Kits de pilotages\\nCALIBRATOR ZURF") : ne garder que la dernière
    ligne de chaque bloc élimine ces titres de section."""
    items = []
    for block in text.split("\n\n"):
        lines = [clean(l) for l in block.split("\n") if clean(l)]
        if lines:
            items.append(lines[-1])

    specs = {}
    label = None
    for item in items:
        if label is None:
            label = item
        else:
            specs[label] = item
            label = None
    return specs


def scrape_bogballe(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles BOGBALLE (épandeurs d'engrais,
    bogballe.com/fr) non encore présentes dans Neon."""
    machines = []
    try:
        page.goto(BOGBALLE_MODELES_URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        _accept_cookies(page)
    except Exception as e:
        log.warning(f"  Bogballe inaccessible : {e}")
        return machines

    product_links = _bogballe_product_links(page)
    log.info(f"  Bogballe → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            _accept_cookies(page)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        segments = [s for s in urlparse(url).path.split("/") if s]
        name = segments[-1].upper().replace("-", " ") if segments else ""
        if not name or len(name) < 2:
            continue

        text = page.inner_text("body")
        idx = text.find(name)
        spec_text = text[idx:] if idx != -1 else text
        footer_idx = spec_text.find("Liste des pièces de rechange")
        if footer_idx != -1:
            spec_text = spec_text[:footer_idx]
        specs = _bogballe_specs(spec_text)
        if not specs:
            continue

        key = f"Bogballe|{name}|"
        if key in existing_keys:
            continue

        m = Machine()
        m.brand = "Bogballe"
        m.name = name
        m.category = normaliser_categorie("épandeurs d'engrais", name)
        m.sourceUrl = url
        m.specs = json.dumps(traduire_specs(specs), ensure_ascii=False)
        m.statut = "active"
        machines.append(m)
        existing_keys.add(key)
        log.info(f"    [{i}/{len(product_links)}] ✓ {name}")
        time.sleep(random.uniform(1.0, 2.0))

    log.info(f"  Bogballe → {len(machines)} machines trouvées")
    return machines


def _upsert(machines: list[Machine]) -> tuple[int, int]:
    """Ouvre une connexion Neon dédiée, insère, puis referme aussitôt.

    Le scraping d'une seule marque/source peut prendre plusieurs minutes ;
    garder une connexion PostgreSQL ouverte pendant tout ce temps la fait
    couper par Neon (timeout d'inactivité). Une connexion courte par lot
    évite complètement le problème.
    """
    conn = db.get_connection()
    try:
        return db.upsert_machines(conn, machines)
    finally:
        conn.close()


def _upsert_and_index(machines: list[Machine]) -> tuple[int, int, int, int]:
    """Enregistre les machines dans Neon puis les indexe dans Qdrant pour
    que l'assistant IA (AgriBot) reste à jour. L'indexation Qdrant ne
    bloque jamais le scraping : ses erreurs sont seulement journalisées."""
    neon_ok, neon_err = _upsert(machines)
    try:
        qdrant_ok, qdrant_err = qdrant_sync.index_machines(machines)
    except Exception as e:
        log.warning(f"  Qdrant : échec indexation ({len(machines)} machines) : {e}")
        qdrant_ok, qdrant_err = 0, len(machines)
    return neon_ok, neon_err, qdrant_ok, qdrant_err


def run() -> int:
    conn = db.get_connection()
    existing_keys = db.get_existing_keys(conn)
    conn.close()
    log.info(f"Neon : {len(existing_keys)} machines déjà en base")

    total_ok, total_err = 0, 0
    total_qdrant_ok, total_qdrant_err = 0, 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="fr-FR",
        )
        for nom_source, scraper_fn in [
            ("Kverneland", scrape_kverneland),
            ("Claas (claas.com)", scrape_claas),
            ("Fendt (fendt.com)", scrape_fendt),
            ("Massey Ferguson (masseyferguson.com)", scrape_massey_ferguson),
            ("New Holland (newholland.com)", scrape_new_holland),
            ("Case IH (caseih.com)", scrape_case_ih),
            ("Monosem (monosem.com)", scrape_monosem),
            ("Same (same-tractors.com)", scrape_same),
            ("AVR (avrmachinery.com)", scrape_avr),
            ("McHale (mchale.net)", scrape_mchale),
            ("Kemper (kemper-stadtlohn.de)", scrape_kemper),
            ("Pöttinger (poettinger.at)", scrape_pottinger),
            ("Grimme (grimme.com)", scrape_grimme),
            ("Väderstad (vaderstad.com)", scrape_vaderstad),
            ("Lemken (lemken.com)", scrape_lemken),
            ("Kuhn (kuhn.fr)", scrape_kuhn),
            ("JCB (jcb.com)", scrape_jcb),
            ("Valtra (valtra.fr)", scrape_valtra),
            ("John Deere (deere.fr)", scrape_johndeere),
            ("Kubota (ke.kubota-eu.com)", scrape_kubota),
            ("Krone (krone.fr)", scrape_krone),
            ("Güttler (guttler.org)", scrape_guttler),
            ("Actisol (actisol-agri.fr)", scrape_actisol),
            ("McCormick (mccormick-tractors.com)", scrape_mccormick),
            ("Franquet (franquet.com)", scrape_franquet),
            ("Vicon (fr.vicon.eu)", scrape_vicon),
            ("Horsch (horsch.com)", scrape_horsch),
            ("Sulky (sky-agriculture.com)", scrape_sulky),
            ("Hardi (hardi.com)", scrape_hardi),
            ("Berthoud (berthoud.com)", scrape_berthoud),
            ("Ropa (ropa-maschinenbau.de)", scrape_ropa),
            ("Samson (samson-agro.com)", scrape_samson),
            ("Bogballe (bogballe.com)", scrape_bogballe),
        ]:
            log.info(f"Source : {nom_source}")
            # Une page dédiée par source : une redirection asynchrone tardive
            # d'un site (ex. Berthoud) peut sinon interrompre le goto() de la
            # source suivante sur une page partagée, en cascade sur tout le
            # reste de la liste (observé en production : Ropa + les 12
            # marques TractorData annulées d'un coup par ce mécanisme).
            page = context.new_page()
            try:
                machines = scraper_fn(page, existing_keys)
            except Exception as e:
                log.error(f"  ❌ Échec {nom_source} : {e}")
                page.close()
                continue
            page.close()
            if machines:
                ok, err, q_ok, q_err = _upsert_and_index(machines)
                total_ok += ok
                total_err += err
                total_qdrant_ok += q_ok
                total_qdrant_err += q_err
                log.info(f"  → {ok} machines enregistrées dans Neon ({err} erreurs), {q_ok} indexées dans Qdrant ({q_err} erreurs)")
            else:
                log.info("  → aucune nouvelle machine")

        browser.close()

    log.info(
        f"Terminé : {total_ok} machines enregistrées au total ({total_err} erreurs Neon), "
        f"{total_qdrant_ok} indexées dans Qdrant ({total_qdrant_err} erreurs)"
    )
    return total_ok


if __name__ == "__main__":
    run()
