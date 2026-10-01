"""
Script de sondage temporaire — à supprimer après usage.
Debug Franquet : l'utilisateur signale avoir des "specs" au lieu de
"machines" en base. Inspecter la structure réelle des <table> sur une
fiche produit pour voir si ce sont des tableaux "larges" (un modèle par
colonne, le format attendu par _machines_from_wide_table) ou des tableaux
simples "label : valeur" pour une seule machine.
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

FRANQUET_CATEGORIES = [
    "https://www.franquet.com/travail-du-sol/",
    "https://www.franquet.com/desherbage-mecanique/",
    "https://www.franquet.com/equipements-pour-semis/",
    "https://www.franquet.com/materiels-recolte-betteraviere/",
]


def inspect(page, url, label):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(6):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(250)
        log.info(f"\n--- {label} : {url} title={page.title()!r}")
        tables = page.query_selector_all("table")
        log.info(f"    {len(tables)} table(s)")
        for ti, t in enumerate(tables[:3]):
            rows = t.query_selector_all("tr")
            log.info(f"    table {ti}: {len(rows)} rows")
            for r in rows[:6]:
                cells = r.query_selector_all("td, th")
                log.info(f"      row: {[c.inner_text().strip()[:40] for c in cells]}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        for category_url in FRANQUET_CATEGORIES:
            page = browser.new_page(user_agent=UA)
            try:
                page.goto(category_url, timeout=25000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                base_path = urlparse(category_url).path
                hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
                links = sorted(set(
                    h.split("?")[0].split("#")[0] for h in hrefs
                    if "franquet.com" in urlparse(h).netloc
                    and urlparse(h).path.startswith(base_path)
                    and urlparse(h).path.rstrip("/") != base_path.rstrip("/")
                ))
                log.info(f"=== {category_url} : {len(links)} fiches")
                if links:
                    inspect(page, links[0], f"{category_url} — premier produit")
            except Exception as e:
                log.warning(f"  {category_url} : échec ({e})")
            page.close()

        browser.close()


if __name__ == "__main__":
    main()
