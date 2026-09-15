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

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup

import db

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


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def extract_year(text: str) -> str:
    m = re.search(r"\b(19[0-9]\d|20[012]\d)\b", text)
    return m.group() if m else ""


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
        if "/farm-tractors/" in href and href.endswith(".html") and "tractor-brands" not in href:
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
            m.name = titre[len(marque):].strip() if titre.lower().startswith(marque.lower()) else titre

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

        specs = traduire_specs(specs)
        specs["puissance_cv"] = cv
        specs["annee"] = m.variant
        specs["badge"] = badge
        m.specs = json.dumps(specs, ensure_ascii=False)

        machines.append(m)
        existing_keys.add(key)
        log.info(f"    [{i}/{len(model_links)}] ✓ {m.name} {m.variant}{f' — {badge}' if badge else ''}")

    return machines


def run() -> int:
    conn = db.get_connection()
    existing_keys = db.get_existing_keys(conn)
    log.info(f"Neon : {len(existing_keys)} machines déjà en base")

    total_ok, total_err = 0, 0

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

        for marque, liste_url in MARQUES.items():
            log.info(f"Marque : {marque}")
            machines = scrape_marque(page, marque, liste_url, existing_keys)
            if machines:
                ok, err = db.upsert_machines(conn, machines)
                total_ok += ok
                total_err += err
                log.info(f"  → {ok} machines enregistrées dans Neon ({err} erreurs)")
            else:
                log.info("  → aucune nouvelle machine")

        browser.close()

    conn.close()
    log.info(f"Terminé : {total_ok} machines enregistrées au total, {total_err} erreurs")
    return total_ok


if __name__ == "__main__":
    run()
