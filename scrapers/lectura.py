"""
AgriScan - Scraper Lectura Specs
Stratégie : URLs directes par catégorie+marque (pas de pagination = pas de Cloudflare)
"""

from playwright.sync_api import Page
from bs4 import BeautifulSoup
from urllib.parse import unquote
import re, json, logging, time, random
from .base import Machine, clean, extract_cv, extract_year, extract_image

log = logging.getLogger("agriscan")
BASE = "https://www.lectura-specs.fr"
SPEC = f"{BASE}/fr/specification/machine-agricole"

# URLs directes par catégorie+marque - pas de pagination, pas de Cloudflare
URLS = {
    # Tracteurs
    "Tracteurs": [
        f"{SPEC}/tracteurs-4wd-john-deere",
        f"{SPEC}/tracteurs-4wd-new-holland",
        f"{SPEC}/tracteurs-4wd-case-ih",
        f"{SPEC}/tracteurs-4wd-massey-ferguson",
        f"{SPEC}/tracteurs-4wd-fendt",
        f"{SPEC}/tracteurs-4wd-claas",
        f"{SPEC}/tracteurs-4wd-kubota",
        f"{SPEC}/tracteurs-4wd-deutz-fahr",
        f"{SPEC}/tracteurs-4wd-valtra",
        f"{SPEC}/tracteurs-4wd-same",
        f"{SPEC}/tracteurs-4wd-landini",
        f"{SPEC}/tracteurs-4wd-mccormick",
        f"{SPEC}/tracteurs-4wd-steyr",
        f"{SPEC}/tracteurs-a-chenilles-fendt",
        f"{SPEC}/tracteurs-a-chenilles-john-deere",
        f"{SPEC}/tracteurs-a-chenilles-goldoni",
        f"{SPEC}/tracteurs-roues-arriere-goldoni",
        f"{SPEC}/valet-de-ferme-schaffer",
        f"{SPEC}/valet-de-ferme-thaler",
        f"{SPEC}/valet-de-ferme-weidemann",
    ],
    # Moissonneuses
    "Moissonneuses": [
        f"{SPEC}/moissonneuse-batteuses-john-deere",
        f"{SPEC}/moissonneuse-batteuses-claas",
        f"{SPEC}/moissonneuse-batteuses-new-holland",
        f"{SPEC}/moissonneuse-batteuses-case-ih",
        f"{SPEC}/moissonneuse-batteuses-massey-ferguson",
        f"{SPEC}/moissonneuse-batteuses-fendt",
    ],
    # Ensileuses
    "Ensileuses": [
        f"{SPEC}/ensileuses-traction-2-roues-claas",
        f"{SPEC}/ensileuses-traction-2-roues-john-deere",
        f"{SPEC}/ensileuses-traction-2-roues-krone",
        f"{SPEC}/ensileuses-traction-4-roues-claas",
        f"{SPEC}/ensileuses-traction-4-roues-john-deere",
        f"{SPEC}/ensileuses-traction-4-roues-new-holland",
    ],
    # Travail du sol
    "Travail du sol": [
        f"{SPEC}/charrue-kuhn",
        f"{SPEC}/charrue-kverneland",
        f"{SPEC}/charrue-lemken",
        f"{SPEC}/charrue-amazone",
        f"{SPEC}/charrue-unia",
        f"{SPEC}/charrue-vogel-noot",
        f"{SPEC}/charrue-kongskilde",
        f"{SPEC}/charrue-pottinger",
        f"{SPEC}/charrue-rabe",
        f"{SPEC}/charrue-yto",
        f"{SPEC}/charrue-pietro-moro",
        f"{SPEC}/cultivateurs-amazone",
        f"{SPEC}/cultivateurs-horsch",
        f"{SPEC}/cultivateurs-kverneland",
        f"{SPEC}/herses-rotatives-kuhn",
        f"{SPEC}/herses-rotatives-lemken",
        f"{SPEC}/herses-rotatives-rabe",
        f"{SPEC}/herse-a-disques-en-zinc-amazone",
        f"{SPEC}/herse-a-disques-en-zinc-kuhn",
        f"{SPEC}/herse-a-disques-en-zinc-vogel-noot",
        f"{SPEC}/rouleaux-pour-des-champs-et-prairies-amazone",
        f"{SPEC}/rouleaux-pour-des-champs-et-prairies-bremer",
        f"{SPEC}/rouleaux-pour-des-champs-et-prairies-kverneland",
        f"{SPEC}/rouleaux-pour-des-champs-et-prairies-dal-bo",
    ],
    # Semois
    "Semoirs": [
        f"{SPEC}/semoirs-amazone",
        f"{SPEC}/semoirs-john-deere",
        f"{SPEC}/semoirs-kuhn",
        f"{SPEC}/semoirs-horsch",
        f"{SPEC}/semoirs-kverneland",
    ],
    # Pulvérisateurs
    "Pulvérisateurs": [
        f"{SPEC}/pulverisateurs-automoteurs-john-deere",
        f"{SPEC}/pulverisateurs-automoteurs-fendt",
        f"{SPEC}/pulverisateurs-automoteurs-berthoud",
        f"{SPEC}/pulverisateurs-portes-john-deere",
        f"{SPEC}/pulverisateurs-portes-kuhn",
        f"{SPEC}/pulverisateurs-portes-berthoud",
        f"{SPEC}/pulverisateurs-traines-amazone",
        f"{SPEC}/pulverisateurs-traines-john-deere",
        f"{SPEC}/pulverisateurs-traines-kuhn",
    ],
    # Fenaison
    "Fenaison": [
        f"{SPEC}/andaineurs-rotatifs-claas",
        f"{SPEC}/andaineurs-rotatifs-krone",
        f"{SPEC}/andaineurs-rotatifs-kuhn",
        f"{SPEC}/faneuses-rotatives-claas",
        f"{SPEC}/faneuses-rotatives-krone",
        f"{SPEC}/faneuses-rotatives-kuhn",
        f"{SPEC}/faucheuses-arrieres-disques-avec-conditionneurs-claas",
        f"{SPEC}/faucheuses-arrieres-disques-avec-conditionneurs-krone",
        f"{SPEC}/faucheuses-arrieres-disques-avec-conditionneurs-kuhn",
        f"{SPEC}/faucheuses-frontales-disques-avec-conditionneurs-claas",
        f"{SPEC}/faucheuses-frontales-disques-avec-conditionneurs-krone",
        f"{SPEC}/faucheuses-frontales-disques-avec-conditionneurs-kuhn",
        f"{SPEC}/faucheuses-arrieres-tambour-sans-conditionneur-claas",
        f"{SPEC}/faucheuses-arrieres-tambour-sans-conditionneur-fella",
        f"{SPEC}/faucheuses-conditionneuses-a-disques-rotatifs-fendt",
        f"{SPEC}/faucheuses-conditionneuses-a-disques-rotatifs-krone",
        f"{SPEC}/faucheuses-conditionneuses-a-disques-rotatifs-kuhn",
    ],
    # Presses
    "Presses": [
        f"{SPEC}/presses-a-balles-rondes-claas",
        f"{SPEC}/presses-a-balles-rondes-john-deere",
        f"{SPEC}/presses-a-balles-rondes-new-holland",
        f"{SPEC}/presses-de-grandes-balles-a-haute-pression-john-deere",
        f"{SPEC}/presses-de-grandes-balles-a-haute-pression-new-holland",
        f"{SPEC}/emballeuses-dal-bo",
        f"{SPEC}/emballeuses-kverneland",
    ],
    # Chargeurs
    "Chargeurs": [
        f"{SPEC}/chargeurs-frontaux",
    ],
    # Broyeurs
    "Broyeurs & débroussailleuses": [
        f"{SPEC}/broyeurs",
    ],
    # Épandage
    "Épandage": [
        f"{SPEC}/technologie-du-lisier-et-du-fumier",
    ],
    # Remorques
    "Remorques agricoles": [
        f"{SPEC}/remorque-agricole-joskin",
        f"{SPEC}/remorque-agricole-rolland",
        f"{SPEC}/remorques-autochargeuses-d-ensilage-claas",
        f"{SPEC}/remorques-autochargeuses-d-ensilage-pottinger",
        f"{SPEC}/remorques-autochargeuses-d-ensilage-strautmann",
    ],
    # Irrigation
    "Matériel d'irrigation": [
        f"{SPEC}/technologie-d-irrigation",
    ],
    # Accessoires récolte
    "Matériels de récolte": [
        f"{SPEC}/accessoires-pour-moissonneuses-batteuses-claas",
        f"{SPEC}/accessoires-pour-moissonneuses-batteuses-geringhoff",
    ],
}

EXCLUSIONS = ["tondeuse", "jardin", "gazon", "evaluation", "spare-parts"]

MARQUES = [
    "john-deere", "fendt", "claas", "massey-ferguson", "new-holland",
    "case-ih", "kubota", "deutz-fahr", "valtra", "krone", "kuhn",
    "amazone", "horsch", "lemken", "kverneland", "pottinger", "joskin",
    "rolland", "berthoud", "fella", "goldoni", "rabe", "yto", "dal-bo",
    "kongskilde", "unia", "vogel-noot", "strautmann", "trioliet",
    "same", "landini", "mccormick", "steyr", "schaffer", "thaler",
    "weidemann", "geringhoff", "pietro-moro", "bremer", "bcs", "carraro",
]

def _extraire_marque(slug: str) -> str:
    for m in MARQUES:
        if slug.lower().endswith("-" + m):
            return m.replace("-", " ").title()
    return ""

def _get_soup(browser, url: str) -> BeautifulSoup | None:
    """Nouvelle session à chaque appel pour éviter Cloudflare."""
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale="fr-FR",
        viewport={"width": 1280, "height": 800},
    )
    lpage = ctx.new_page()
    try:
        lpage.goto(url, timeout=60000, wait_until="networkidle")
        lpage.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        html = lpage.content()
        if "Cloudflare" in html and len(html) < 10000:
            log.warning(f"  ⚠️  Cloudflare sur {url.split('/')[-1]}")
            return None
        return BeautifulSoup(html, "html.parser")
    except Exception as e:
        log.warning(f"  Erreur {url} → {e}")
        return None
    finally:
        ctx.close()

def _get_model_links(soup) -> set:
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            href = BASE + href
        if "/modele/machine-agricole/" not in href:
            continue
        if any(excl in href.lower() for excl in EXCLUSIONS):
            continue
        links.add(href)
    return links

def _extraire_specs(soup) -> dict:
    specs = {}
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                key = clean(cells[0].get_text())
                val = clean(cells[1].get_text())
                if key and val and len(key) < 80:
                    specs[key] = val
    for dl in soup.find_all("dl"):
        for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
            key = clean(dt.get_text())
            val = clean(dd.get_text())
            if key and val:
                specs[key] = val
    return specs

def scrape(page: Page, already_done: set = None) -> list[Machine]:
    machines = []
    already_done = already_done or set()
    lectura_done = {u for u in already_done if "lectura-specs" in u}
    log.info("📐 Lectura Specs - démarrage")

    browser = page.context.browser

    # Collecter tous les liens modèles
    model_links = {}  # url → categorie
    total_urls = sum(len(v) for v in URLS.values())
    done_urls = 0

    for categorie, cat_urls in URLS.items():
        for cat_url in cat_urls:
            done_urls += 1
            log.info(f"  [{done_urls}/{total_urls}] {cat_url.split('/')[-1]}")
            soup = _get_soup(browser, cat_url)
            if not soup:
                continue
            found = _get_model_links(soup)
            for link in found:
                if link not in model_links:
                    model_links[link] = categorie
            log.info(f"    → {len(found)} modèles")

    new_links = {url: cat for url, cat in model_links.items() if url not in lectura_done}
    log.info(f"  {len(model_links)} fiches total, {len(new_links)} nouvelles à visiter")

    # Visiter chaque fiche
    for i, (url, categorie) in enumerate(new_links.items(), 1):
        soup_m = _get_soup(browser, url)
        if not soup_m:
            continue

        m = Machine()
        m.sourceUrl = url
        m.category = categorie
        parts = unquote(url).rstrip("/").split("/")
        if len(parts) >= 2:
            m.brand = _extraire_marque(parts[-2])
            nom = re.sub(r"-\d+$", "", parts[-1])
            m.name = nom.replace("-", " ").upper()

        h1 = soup_m.find("h1")
        if h1:
            titre = clean(h1.get_text())
            if m.brand and titre.lower().startswith(m.brand.lower()):
                m.name = titre[len(m.brand):].strip()
            elif titre:
                m.name = titre

        if not m.name or len(m.name) < 2:
            continue

        m.imageUrl = extract_image(soup_m)
        specs = _extraire_specs(soup_m)
        if specs:
            for k, v in specs.items():
                if any(x in k.lower() for x in ["puissance", "power"]):
                    cv = extract_cv(v)
                    if cv:
                        specs["puissance_cv"] = cv
        m.specs = json.dumps(specs, ensure_ascii=False) if specs else ""

        machines.append(m)
        log.info(f"  [{i}/{len(new_links)}] ✓ {m.brand} {m.name}")

    log.info(f"Lectura total : {len(machines)} machines")
    return machines