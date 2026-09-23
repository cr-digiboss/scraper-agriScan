"""
AgriScan Scraper — point d'entrée unique
Récupère les fiches tracteurs sur TractorData.com et met à jour la base Neon.

Usage :
    python scraper.py
"""

import os
import re
import json
import time
import random
import logging
from dataclasses import dataclass
from datetime import date
from urllib.parse import urljoin, urlparse

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup

import db
import qdrant_sync

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("agriscan")

BASE = "https://www.tractordata.com"

# Marques scrapées → page listant tous les modèles de la marque.
# Pour ajouter une marque : trouver sa page "tractor-brands" sur tractordata.com et l'ajouter ici.
MARQUES = {
    "John Deere":      f"{BASE}/farm-tractors/tractor-brands/johndeere/johndeere-tractors.html",
    "Massey Ferguson": f"{BASE}/farm-tractors/tractor-brands/massey-ferguson/massey-ferguson-tractors.html",
    "New Holland":     f"{BASE}/farm-tractors/tractor-brands/newholland/newholland-tractors.html",
    "Case IH":         f"{BASE}/farm-tractors/tractor-brands/caseih/caseih-tractors.html",
    "Kubota":          f"{BASE}/farm-tractors/tractor-brands/kubota/kubota-tractors.html",
    "Ford":            f"{BASE}/farm-tractors/tractor-brands/ford/ford-tractors.html",
    "Fendt":           f"{BASE}/farm-tractors/tractor-brands/fendt/fendt-tractors.html",
    "Claas":           f"{BASE}/farm-tractors/tractor-brands/claas/claas-tractors.html",
    "Deutz-Fahr":      f"{BASE}/farm-tractors/tractor-brands/deutz/deutz-tractors.html",
    "Allis-Chalmers":  f"{BASE}/farm-tractors/tractor-brands/allischalmers/allischalmers-tractors.html",
    "International":   f"{BASE}/farm-tractors/tractor-brands/ih/ih-tractors.html",
    "Fiat":            f"{BASE}/farm-tractors/tractor-brands/fiat/fiat-tractors.html",
    "Mahindra":        f"{BASE}/farm-tractors/tractor-brands/mahindra/mahindra-tractors.html",
}

ONGLETS = ["Engine", "Transmission", "Dimensions"]
ANNEE_ANCETRE = 1980
ANNEE_VINTAGE = 2000

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


def extract_year(text: str) -> str:
    m = re.search(r"\b(19[0-9]\d|20[012]\d)\b", text)
    return m.group() if m else ""


def parse_production(valeur: str) -> tuple[str, str]:
    """Extrait une plage d'années depuis le champ "Production" de TractorData
    (ex. "1985 - 1992", "1965-", "2015 - present"). Retourne (anneeDebut,
    anneeFin) ; anneeFin vide si la production semble toujours en cours ou
    si on ne peut pas la déterminer — on ne devine jamais un statut à tort."""
    if not valeur:
        return "", ""
    annees = re.findall(r"\b(19[0-9]\d|20[0-2]\d)\b", valeur)
    en_cours = bool(re.search(r"present|current|date|aujourd", valeur, re.I))
    if len(annees) >= 2:
        return min(annees), max(annees)
    if len(annees) == 1:
        return (annees[0], "") if en_cours else (annees[0], annees[0])
    return "", ""


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


def _badge(annee: str) -> str:
    try:
        a = int(annee[:4]) if annee else 0
        if a and a < ANNEE_ANCETRE:
            return "Ancêtre"
        if a and a < ANNEE_VINTAGE:
            return "Vintage"
    except (ValueError, TypeError):
        pass
    return ""


def _extraire_specs(page: Page) -> dict:
    """Clique sur chaque onglet de la fiche technique et récupère les tableaux de specs."""
    specs = {}
    for onglet in ONGLETS:
        try:
            page.click(f"text={onglet}", timeout=3000)
            time.sleep(1.5)
            soup = BeautifulSoup(page.content(), "html.parser")
            for table in soup.find_all("table"):
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        k = clean(cells[0].get_text())
                        v = clean(cells[1].get_text())
                        if k and v and k != "x" and "x" not in k and len(k) > 2:
                            specs[k] = v
        except Exception:
            pass
    return specs


def _extraire_puissance(specs: dict, text: str) -> str:
    for k, v in specs.items():
        if any(x in k.lower() for x in ["power", "hp", "pto", "engine"]):
            m = re.search(r"(\d+\.?\d*)\s*hp", v, re.I)
            if m:
                return str(round(float(m.group(1)) * 0.7355))
    m = re.search(r"(\d+\.?\d*)\s*hp", text, re.I)
    if m:
        return str(round(float(m.group(1)) * 0.7355))
    return ""


def scrape_marque(page: Page, marque: str, liste_url: str, existing_keys: set) -> list[Machine]:
    """Scrape les modèles d'une marque non encore présents dans Neon."""
    machines = []
    try:
        page.goto(liste_url, timeout=60000, wait_until="domcontentloaded")
        time.sleep(2)
    except Exception as e:
        log.warning(f"  {marque} inaccessible : {e}")
        return machines

    soup_liste = BeautifulSoup(page.content(), "html.parser")
    model_links = set()
    for a in soup_liste.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            href = BASE + href
        # Une vraie fiche modèle a toujours un dossier numérique juste après
        # /farm-tractors/ (ex. /farm-tractors/000/0/3/35-john-deere-50.html).
        # Sans ça on récupère aussi des pages de navigation comme
        # /farm-tractors/index.html, scrapées à tort comme un "modèle".
        if (
            href.endswith(".html")
            and "tractor-brands" not in href
            and re.search(r"/farm-tractors/\d+/", href)
        ):
            model_links.add(href)

    log.info(f"  {marque} → {len(model_links)} modèles trouvés sur le site")

    for i, url in enumerate(sorted(model_links), 1):
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            time.sleep(random.uniform(1.5, 2.5))
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        soup_m = BeautifulSoup(page.content(), "html.parser")
        m = Machine(brand=marque, category="Tracteurs", sourceUrl=url)

        h1 = soup_m.find("h1")
        if h1:
            titre = clean(h1.get_text())
            # Une vraie fiche modèle commence toujours par le nom de la marque
            # (ex. "Massey Ferguson 165"). Sinon, ce n'est probablement pas
            # une fiche modèle valide (page de navigation, erreur...).
            if titre.lower().startswith(marque.lower()):
                m.name = titre[len(marque):].strip()

        if not m.name or len(m.name) < 2:
            continue

        page_text = soup_m.get_text()
        m.variant = extract_year(page_text)

        key = f"{m.brand}|{m.name}|{m.variant}"
        if key in existing_keys:
            continue

        specs = _extraire_specs(page)
        cv = _extraire_puissance(specs, page_text)
        badge = _badge(m.variant)

        m.anneeDebut, m.anneeFin = parse_production(specs.get("Production", ""))
        if m.anneeFin:
            m.statut = "discontinued" if int(m.anneeFin) < date.today().year else "active"
        elif m.anneeDebut:
            m.statut = "active"

        specs = traduire_specs(specs)
        specs["puissance_cv"] = cv
        specs["annee"] = m.variant
        specs["badge"] = badge
        m.specs = json.dumps(specs, ensure_ascii=False)

        machines.append(m)
        existing_keys.add(key)
        log.info(f"    [{i}/{len(model_links)}] ✓ {m.name} {m.variant}{f' — {badge}' if badge else ''}")

    return machines


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
        m.brand = "Kverneland"
        m.name = specs.pop("Model", "") or _clean_kverneland_title(page.title())
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

        for candidats in _machines_from_wide_table(tables[0], "Fendt", category, range_name, url):
            key = f"{candidats.brand}|{candidats.name}|{candidats.variant}"
            if key in existing_keys:
                continue
            machines.append(candidats)
            existing_keys.add(key)
            log.info(f"    [{i}/{len(product_links)}] ✓ {candidats.name}")

        time.sleep(random.uniform(1.0, 2.0))

    return machines


# ─────────────────────────────────────────────────────────────────────────────
# Massey Ferguson — masseyferguson.com
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

        for candidats in _machines_from_wide_table(tables[0], "Massey Ferguson", category, range_name, url):
            key = f"{candidats.brand}|{candidats.name}|{candidats.variant}"
            if key in existing_keys:
                continue
            machines.append(candidats)
            existing_keys.add(key)
            log.info(f"    [{i}/{len(product_links)}] ✓ {candidats.name}")

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


def scrape_new_holland(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles New Holland (tracteurs, presses, moissonneuses,
    ensileuses) non encore présentes dans Neon."""
    machines = []

    for category_url in NEW_HOLLAND_CATEGORIES:
        base_path = urlparse(category_url).path
        category_slug = base_path.rstrip("/").split("/")[-1]

        try:
            page.goto(category_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
        except Exception as e:
            log.warning(f"  New Holland ({category_slug}) inaccessible : {e}")
            continue

        product_links = _new_holland_product_links(page, base_path)
        log.info(f"  New Holland ({category_slug}) → {len(product_links)} fiches modèles trouvées")
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

            range_name = clean(page.title()).split("|")[0].strip()

            for candidats in _machines_from_wide_table(tables[0], "New Holland", category, range_name, url):
                key = f"{candidats.brand}|{candidats.name}|{candidats.variant}"
                if key in existing_keys:
                    continue
                machines.append(candidats)
                existing_keys.add(key)
                log.info(f"    [{i}/{len(product_links)}] ✓ {candidats.name}")

            time.sleep(random.uniform(1.0, 2.0))

    return machines


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
# Une fiche produit a un <table> unique, une colonne par modèle de la gamme,
# compatible avec le parser générique _machines_from_wide_table.
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

            for candidats in _machines_from_wide_table(tables[0], "Pöttinger", category, range_name, url):
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
# Crawl par catégories (construction + agricole). Tableau large classique
# (colonne 0 = attribut, en-tête = codes modèles), compatible avec le
# parser générique déjà utilisé pour Pöttinger/Lemken/Grimme.
# ─────────────────────────────────────────────────────────────────────────────

JCB_CATEGORIES = {
    "Chargeurs compacts sur chenilles": "https://www.jcb.com/fr-FR/products/machines/chargeurs-compacts-sur-chenilles/",
    "Chargeuses compactes sur pneus": "https://www.jcb.com/fr-FR/products/machines/skid-steer-loader/",
    "Chargeuses-pelleteuses": "https://www.jcb.com/fr-FR/products/machines/chargeuses-pelleteuses/",
    "Chargeuses sur pneumatiques": "https://www.jcb.com/fr-FR/products/machines/chargeuses-sur-pneumatiques/",
    "Chariots élévateurs tout-terrain": "https://www.jcb.com/fr-FR/products/machines/rough-terrain-forklifts/",
    "Télescopiques rotatifs": "https://www.jcb.com/fr-FR/products/machines/rotating-telehandlers/",
    "Compacteurs monobille": "https://www.jcb.com/fr-FR/products/machines/single-drum-soil-compactors/",
    "Dumpers de chantier": "https://www.jcb.com/fr-FR/products/machines/site-dumpers/",
    "Bennes": "https://www.jcb.com/fr-FR/products/machines/dumpsters/",
    "Groupes électrogènes": "https://www.jcb.com/fr-FR/products/machines/groupes-electrogenes/",
    "Hydradig": "https://www.jcb.com/fr-FR/products/machines/hydradig/",
    "Mini-pelles": "https://www.jcb.com/fr-FR/products/machines/mini-pelles/",
    "Nacelles articulées": "https://www.jcb.com/fr-FR/products/machines/articulated-booms/",
    "Nacelles ciseaux électriques": "https://www.jcb.com/fr-FR/products/machines/nacelles-ciseaux-electriques/",
    "Pelles sur chenilles": "https://www.jcb.com/fr-FR/products/machines/pelles-sur-chenilles/",
    "Pelles sur roues": "https://www.jcb.com/fr-FR/products/machines/wheeled-excavators/",
    "Pothole Pro": "https://www.jcb.com/fr-FR/products/machines/pothole-pro/",
    "Rouleaux vibrants tandem": "https://www.jcb.com/fr-FR/products/machines/vibratory-tandem-rollers/",
    "Télescopiques": "https://www.jcb.com/fr-FR/products/machines/telescopic/",
    "Télescopiques articulés": "https://www.jcb.com/fr-FR/products/machines/telescopic-articules/",
    "Chariots élévateurs industriels": "https://www.jcb.com/fr-FR/products/machines/industrial-forklifts/",
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
        page = context.new_page()

        # Sources légères en premier (catalogue complet en quelques minutes),
        # TractorData en dernier car son crawl de 12 marques est le plus long.
        for nom_source, scraper_fn in [
            ("Kverneland", scrape_kverneland),
            ("Claas (claas.com)", scrape_claas),
            ("Fendt (fendt.com)", scrape_fendt),
            ("Massey Ferguson (masseyferguson.com)", scrape_massey_ferguson),
            ("New Holland (newholland.com)", scrape_new_holland),
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
        ]:
            log.info(f"Source : {nom_source}")
            try:
                machines = scraper_fn(page, existing_keys)
            except Exception as e:
                log.error(f"  ❌ Échec {nom_source} : {e}")
                continue
            if machines:
                ok, err, q_ok, q_err = _upsert_and_index(machines)
                total_ok += ok
                total_err += err
                total_qdrant_ok += q_ok
                total_qdrant_err += q_err
                log.info(f"  → {ok} machines enregistrées dans Neon ({err} erreurs), {q_ok} indexées dans Qdrant ({q_err} erreurs)")
            else:
                log.info("  → aucune nouvelle machine")

        for marque, liste_url in MARQUES.items():
            log.info(f"Marque : {marque}")
            machines = scrape_marque(page, marque, liste_url, existing_keys)
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
