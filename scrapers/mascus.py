"""
AgriScan — Scraper Mascus
Site : https://www.mascus.fr/agriculture
Structure : /agricole/categorie/marque-modele/id.html
"""

from playwright.sync_api import Page
from bs4 import BeautifulSoup
from urllib.parse import unquote
import re, logging
from .base import Machine, get_soup, clean, extract_cv, extract_year, extract_image, extract_description

log = logging.getLogger("agriscan")

BASE = "https://www.mascus.fr"
MAIN_URL = f"{BASE}/main-category/agricole"

# Mapping slug → catégorie générique AgriScan
SLUG_TO_CAT = {
    "tracteur": "Tracteurs",
    "moissonneuse-batteuse": "Moissonneuses-batteuses",
    "moissonneuse-batteuse-occasion": "Moissonneuses-batteuses",
    "ensileuse": "Ensileuses",
    "ensileuse-automotrice": "Ensileuses",
    "pulve": "Pulvérisateurs",
    "pulverisateurs-portes": "Pulvérisateurs",
    "pulverisateurs-traines": "Pulvérisateurs",
    "pulverisateurs-automoteurs": "Pulvérisateurs",
    "pulverisateur-vigne": "Pulvérisateurs",
    "chargeur-frontal-fourche": "Chargeurs frontaux",
    "chargeuse-multifonction": "Chargeurs frontaux",
    "telescopique": "Chargeurs frontaux",
    "presse-balles-rondes": "Presses",
    "presse-cubique": "Presses",
    "semoir": "Semis",
    "semoir-combine": "Semis",
    "semoir-precision": "Semis",
    "semoir-engrais": "Semis",
    "semoir-planteuse": "Semis",
    "autre-semoir": "Semis",
    "charrue": "Travail du sol",
    "charrue-a-dents": "Travail du sol",
    "charrue-non-reversible": "Travail du sol",
    "cultivateur-dechaumeur": "Travail du sol",
    "herse": "Travail du sol",
    "herse-combinee": "Travail du sol",
    "herse-rotative": "Travail du sol",
    "vibroculteur": "Travail du sol",
    "decompacteur-sarcleur": "Travail du sol",
    "outils-preparation-sol": "Travail du sol",
    "autres-outils-preparation-sol": "Travail du sol",
    "rouleau": "Travail du sol",
    "faucheuse": "Faucheuses-conditionneuses",
    "faucheuse-conditionneuse": "Faucheuses-conditionneuses",
    "faucheuse-andaineuse-automotrice": "Faucheuses-conditionneuses",
    "andaineur": "Faucheuses-conditionneuses",
    "rateau-faneur": "Faucheuses-conditionneuses",
    "epandeur": "Fertilisation",
    "epandeur-fumier": "Fertilisation",
    "epandeurs-d-engrais-liquide": "Fertilisation",
    "tonne-lisier": "Fertilisation",
    "autres-materiels-fertilisation": "Fertilisation",
    "machine-vendanger": "Viticulture",
    "materiel-viticole": "Viticulture",
    "autre-materiel-viticole": "Viticulture",
    "pulverisateur-vigne": "Viticulture",
    "travail-sol-viticole": "Viticulture",
    "enrubanneuse": "Presses",
    "remorque": "Remorques",
    "remorque-auto-chargeuse": "Remorques",
    "benne-cerealiere": "Remorques",
    "materiel-elevage": "Élevage",
    "salle-de-traite": "Élevage",
    "tank-a-lait": "Élevage",
    "melangeuse": "Élevage",
    "desileuse": "Élevage",
}

EXCLUSIONS = [
    "accessoires", "pieces", "login", "register", "contact",
    "blog", "about", "privacy", "cookie", "sitemap", "placead",
    "electronique", "moteur", "transmission", "freins", "hydraulique",
    "radiateurs", "chassis", "pneus", "cabines", "gps", "masse-avant",
]

# Années seuil pour le badge
ANNEE_ANCETRE = 1980
ANNEE_VINTAGE = 2000

def _badge(annee: str) -> str:
    try:
        a = int(annee)
        if a < ANNEE_ANCETRE:
            return "Ancêtre"
        if a < ANNEE_VINTAGE:
            return "Vintage"
    except:
        pass
    return ""

def _get_categories(soup: BeautifulSoup) -> dict:
    """Découvre automatiquement toutes les catégories depuis la page principale."""
    cats = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            href = BASE + href
        href_decoded = unquote(href).lower()
        # Lien catégorie = /agricole/slug sans .html et sans sous-dossier marque
        if not href_decoded.startswith(f"{BASE}/agricole/"):
            continue
        if href_decoded.endswith(".html"):
            continue
        if any(excl in href_decoded for excl in EXCLUSIONS):
            continue
        slug = href_decoded.replace(f"{BASE}/agricole/", "").strip("/")
        if "/" in slug:  # Pas de sous-dossier marque
            continue
        if not slug:
            continue
        # Mapper vers catégorie générique ou garder le slug comme catégorie
        cat = SLUG_TO_CAT.get(slug, slug.replace("-", " ").title())
        cats[cat] = href
    return cats


def scrape(page: Page, already_done: set = None) -> list[Machine]:
    machines = []
    already_done = already_done or set()
    visited = set()
    log.info("🔵 Mascus — démarrage")

    # Découverte automatique des catégories
    soup_main = get_soup(page, MAIN_URL)
    if not soup_main:
        log.error("Impossible de charger la page principale Mascus")
        return machines

    categories = _get_categories(soup_main)
    log.info(f"  {len(categories)} catégories découvertes automatiquement")

    for categorie, cat_url in categories.items():
        soup_cat = get_soup(page, cat_url)
        if not soup_cat:
            continue

        # Collecter les fiches produits — URL se termine par .html
        product_links = set()
        for a in soup_cat.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("http"):
                href = BASE + href
            href_decoded = unquote(href).lower()
            if not href_decoded.startswith(f"{BASE}/agricole/"):
                continue
            if any(excl in href_decoded for excl in EXCLUSIONS):
                continue
            if href_decoded.endswith(".html") and href.count("/") >= 6:
                product_links.add(href)

        # Filtrer déjà scrapés
        new_links = product_links - already_done - visited
        skipped = len(product_links) - len(new_links)
        if skipped:
            log.info(f"  {categorie} → {len(product_links)} annonces ({skipped} déjà scrapées, {len(new_links)} nouvelles)")
        else:
            log.info(f"  {categorie} → {len(new_links)} annonces à visiter")

        if not new_links:
            continue

        for url in list(new_links)[:30]:
            visited.add(url)

            soup_p = get_soup(page, url)
            if not soup_p:
                continue

            m = Machine(marque="", categorie=categorie, url_source=url)

            h1 = soup_p.find("h1")
            if h1:
                titre = clean(h1.get_text())
                # Marques connues multi-mots — à compléter selon les résultats
                MARQUES_CONNUES = [
                    "John Deere", "New Holland", "Massey Ferguson",
                    "Case IH", "Same Deutz-Fahr", "Deutz Fahr", "Deutz-Fahr",
                    "McCormick International", "Landini McCormick",
                    "White Oliver", "Ford New Holland",
                ]
                m.marque = ""
                m.modele = titre
                # Chercher d'abord une marque multi-mots
                for marque_connue in MARQUES_CONNUES:
                    if titre.lower().startswith(marque_connue.lower()):
                        m.marque = marque_connue
                        m.modele = titre[len(marque_connue):].strip()
                        break
                # Sinon split sur le premier espace
                if not m.marque:
                    parts = titre.split(" ", 1)
                    m.marque = parts[0] if parts else ""
                    m.modele = parts[1] if len(parts) > 1 else titre

            if not m.modele or len(m.modele) < 2:
                continue

            texte = soup_p.get_text()
            m.puissance_cv = extract_cv(texte)
            m.annee = extract_year(texte)
            m.description = extract_description(soup_p)
            m.image_url = extract_image(soup_p)
            m.badge = _badge(m.annee)

            machines.append(m)
            log.info(f"    ✓ {m.marque} {m.modele} {m.annee} {f'— {m.badge}' if m.badge else ''}")

    log.info(f"Mascus total : {len(machines)} machines")
    return machines