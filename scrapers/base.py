"""
AgriScan — Base commune
Structure Machine + fonctions utilitaires partagées par tous les scrapers.
"""

from playwright.sync_api import Page
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional
import time, random, re, logging

log = logging.getLogger("agriscan")

# ─────────────────────────────────────────────────────────────────────────────
# Structure de données
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Machine:
    brand: str = ""          # marque
    range: str = ""          # gamme/série
    name: str = ""           # nom du modèle
    variant: str = ""        # variante ou année
    category: str = ""       # catégorie principale
    subcategory: str = ""    # sous-catégorie
    description: str = ""
    specs: str = ""          # JSON string
    imageUrl: str = ""
    videoUrl: str = ""
    sourceUrl: str = ""

# ─────────────────────────────────────────────────────────────────────────────
# Mapping global des specs anglais → français
# Utilisé par tous les scrapers
# ─────────────────────────────────────────────────────────────────────────────

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

def traduire_specs(specs: dict) -> dict:
    """Traduit les clés des specs en français. Utilisable par tous les scrapers."""
    result = {}
    for k, v in specs.items():
        # Correspondance exacte
        if k in SPECS_TRADUCTIONS:
            result[SPECS_TRADUCTIONS[k]] = v
        else:
            # Correspondance insensible à la casse
            k_lower = k.lower()
            found = False
            for eng, fr in SPECS_TRADUCTIONS.items():
                if eng.lower() == k_lower:
                    result[fr] = v
                    found = True
                    break
            if not found:
                result[k] = v  # Garder tel quel si pas de traduction
    return result

# ─────────────────────────────────────────────────────────────────────────────
# Utilitaires
# ─────────────────────────────────────────────────────────────────────────────

def wait(min_s: float = 2.0, max_s: float = 4.5):
    time.sleep(random.uniform(min_s, max_s))

def get_soup(page: Page, url: str, wait_for: str = "networkidle") -> Optional[BeautifulSoup]:
    """Charge une URL avec Playwright et retourne un BeautifulSoup."""
    try:
        page.goto(url, timeout=60000, wait_until=wait_for)
        time.sleep(3)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(5)
        return BeautifulSoup(page.content(), "html.parser")
    except Exception as e:
        log.warning(f"Erreur GET {url} → {e}")
        try:
            log.info(f"  🔄 Retry {url}")
            page.goto(url, timeout=60000, wait_until="commit")
            time.sleep(3)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(5)
            return BeautifulSoup(page.content(), "html.parser")
        except Exception as e2:
            log.warning(f"  ❌ Échec définitif {url} → {e2}")
            return None

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def extract_cv(text: str) -> str:
    pw = re.search(r"(\d{2,4})\s*(ch|CV|kW|hp)", text, re.I)
    if pw:
        val, unit = pw.group(1), pw.group(2).upper()
        return str(round(int(val) * 1.36)) if unit == "KW" else val
    return ""

def extract_year(text: str) -> str:
    m = re.search(r"\b(19[0-9]\d|20[012]\d)\b", text)
    return m.group() if m else ""

def extract_description(soup: BeautifulSoup) -> str:
    for cls in [r"description", r"overview", r"intro", r"teaser", r"content"]:
        el = soup.find(class_=re.compile(cls, re.I))
        if el:
            desc = clean(el.get_text())
            if len(desc) > 30:
                return desc[:500]
    return ""

def extract_image(soup: BeautifulSoup) -> str:
    img = soup.find("img", class_=re.compile(r"product|hero|main", re.I))
    if not img:
        img = soup.find("img")
    if img:
        src = img.get("src") or img.get("data-src") or ""
        if src.startswith("http"):
            return src
    return ""

def is_parasite(modele: str, keywords: list[str]) -> bool:
    return any(k in modele.lower() for k in keywords)