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
from urllib.parse import urlparse

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
    # "John Deere":    f"{BASE}/farm-tractors/tractor-brands/johndeere/johndeere-tractors.html",  # désactivé : catalogue trop volumineux
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
# Structure : pas de <table> pour les specs, mais un bloc "Technical
# Specification" dont le texte affiche chaque paire clé/valeur séparée par
# une tabulation (les en-têtes de catégorie n'ont pas de tabulation).
# ─────────────────────────────────────────────────────────────────────────────

MCHALE_HOME = "https://www.mchale.net/"


def _mchale_product_links(page: Page) -> set:
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "mchale.net" not in u.netloc:
            continue
        segments = [s for s in u.path.split("/") if s]
        if len(segments) == 2 and segments[0] == "products":
            links.add(href.split("?")[0].split("#")[0])
    return links


def _parse_tab_spec_block(text: str) -> dict:
    """Un bloc specs McHale mélange en-têtes de catégorie (pas de tabulation)
    et paires clé/valeur (séparées par une tabulation) sur des lignes
    distinctes."""
    specs = {}
    for line in text.split("\n"):
        parts = line.split("\t")
        if len(parts) == 2:
            k, v = clean(parts[0]), clean(parts[1])
            if k and v:
                specs[k] = v
    return specs


def scrape_mchale(page: Page, existing_keys: set) -> list[Machine]:
    """Scrape les fiches modèles McHale non encore présentes dans Neon."""
    machines = []
    try:
        page.goto(MCHALE_HOME, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
    except Exception as e:
        log.warning(f"  McHale inaccessible : {e}")
        return machines

    product_links = _mchale_product_links(page)
    log.info(f"  McHale → {len(product_links)} fiches modèles trouvées sur le site")

    for i, url in enumerate(sorted(product_links), 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            # La section "Technical Specification" (classe techspec) est montée
            # en lazy-load au scroll : sans ça, elle n'existe pas encore dans
            # le DOM et le sélecteur ci-dessous ne trouve jamais rien. On scrolle
            # jusqu'au bas réel de la page (pas une distance fixe qui peut être
            # insuffisante selon la longueur de la fiche).
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
        except Exception as e:
            log.warning(f"    Erreur {url} → {e}")
            continue

        spec_blocks = page.query_selector_all("[class*='spec' i], [class*='technical' i]")
        specs = {}
        for block in spec_blocks:
            specs.update(_parse_tab_spec_block(block.inner_text()))

        if not specs:
            continue

        m = Machine()
        m.brand = "McHale"
        m.name = clean(page.title()).split("–")[0].strip()
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
