"""
AgriScan — Enrichissement des specs depuis Lectura Specs
Pour chaque machine dans Neon, cherche la fiche sur Lectura et récupère les specs.

Installation :
    pip install playwright psycopg2-binary python-dotenv beautifulsoup4
    playwright install chromium

Usage :
    python enrich_specs.py
"""

from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup
import psycopg2
import psycopg2.extras
import json
import os
import time
import random
import logging
from urllib.parse import quote
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("agriscan")

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
DATABASE_URL = os.getenv("DATABASE_URL")

BASE = "https://www.lectura-specs.fr"
SEARCH_URL = f"{BASE}/fr/recherche?q="

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def wait():
    time.sleep(random.uniform(2.0, 4.0))

def get_soup(page: Page, url: str) -> BeautifulSoup | None:
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        wait()
        return BeautifulSoup(page.content(), "html.parser")
    except Exception as e:
        log.warning(f"Erreur GET {url} → {e}")
        return None

def chercher_machine(page: Page, brand: str, name: str) -> str | None:
    """Cherche une machine sur Lectura et retourne l'URL de sa fiche."""
    query = f"{brand} {name}".strip()
    url = SEARCH_URL + quote(query)
    soup = get_soup(page, url)
    if not soup:
        return None

    # Chercher le premier résultat machine agricole
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            href = BASE + href
        if "/fr/modele/machine-agricole/" in href:
            return href

    return None

def extraire_specs(soup: BeautifulSoup) -> dict:
    """Extrait les specs techniques depuis une fiche Lectura."""
    specs = {}

    # Chercher les tableaux de specs
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if key and value and len(key) < 80:
                    specs[key] = value

    # Chercher aussi les listes de specs (format dl/dt/dd)
    for dl in soup.find_all("dl"):
        keys = dl.find_all("dt")
        vals = dl.find_all("dd")
        for k, v in zip(keys, vals):
            key = k.get_text(strip=True)
            val = v.get_text(strip=True)
            if key and val:
                specs[key] = val

    # Chercher format div avec label/value
    for div in soup.find_all("div", class_=lambda c: c and any(
        x in c for x in ["spec", "technical", "detail", "attribute"]
    )):
        label = div.find(class_=lambda c: c and "label" in c)
        value = div.find(class_=lambda c: c and "value" in c)
        if label and value:
            specs[label.get_text(strip=True)] = value.get_text(strip=True)

    return specs

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    update_cursor = conn.cursor()

    # Charger les machines sans specs ou avec specs vides
    cursor.execute("""
        SELECT id, brand, name, specs
        FROM "Machine"
        WHERE specs IS NULL 
           OR specs::text = '{}'
           OR specs::text = 'null'
        ORDER BY brand, name
        LIMIT 500
    """)
    machines = [dict(m) for m in cursor.fetchall()]
    log.info(f"📋 {len(machines)} machines sans specs à enrichir")

    print(f"\n{len(machines)} machines à enrichir depuis Lectura Specs")
    confirm = input("Confirmer ? (oui/non) : ").strip().lower()
    if confirm != "oui":
        print("Annulé.")
        return

    enrichies = 0
    non_trouvees = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="fr-FR",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        for i, machine in enumerate(machines, 1):
            brand = machine.get("brand", "")
            name  = machine.get("name", "")

            log.info(f"  [{i}/{len(machines)}] {brand} {name}")

            # Chercher la fiche sur Lectura
            fiche_url = chercher_machine(page, brand, name)

            if not fiche_url:
                log.info(f"    ❌ Non trouvé sur Lectura")
                non_trouvees += 1
                continue

            # Extraire les specs
            soup = get_soup(page, fiche_url)
            if not soup:
                non_trouvees += 1
                continue

            specs = extraire_specs(soup)

            if not specs:
                log.info(f"    ⚠️  Fiche trouvée mais specs vides")
                non_trouvees += 1
                continue

            # Ajouter l'URL Lectura dans les specs
            specs["lectura_url"] = fiche_url

            # Fusionner avec les specs existantes
            existing = machine.get("specs") or {}
            if isinstance(existing, str):
                try:
                    existing = json.loads(existing)
                except:
                    existing = {}
            existing.update(specs)

            # Mettre à jour Neon
            try:
                update_cursor.execute(
                    'UPDATE "Machine" SET specs = %s WHERE id = %s',
                    (json.dumps(existing, ensure_ascii=False), machine["id"])
                )
                enrichies += 1
                log.info(f"    ✅ {len(specs)} specs récupérées")
            except Exception as e:
                log.warning(f"    ❌ Erreur UPDATE : {e}")
                conn.rollback()

            # Commit par batch de 20
            if i % 20 == 0:
                conn.commit()
                log.info(f"  📊 {i}/{len(machines)} — ✅ {enrichies} enrichies, ❌ {non_trouvees} non trouvées")

        browser.close()

    conn.commit()
    cursor.close()
    update_cursor.close()
    conn.close()

    log.info(f"\n🎯 Terminé !")
    log.info(f"   ✅ Enrichies     : {enrichies}")
    log.info(f"   ❌ Non trouvées  : {non_trouvees}")


if __name__ == "__main__":
    run()