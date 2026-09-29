"""
Script de sondage temporaire — à supprimer après usage.
Lot 1 round 5 :
- Horsch : structure d'une fiche produit (joker-4-6-hd)
- Amazone : trouver un produit sous épandeurs (catégorie différente de la
  fiche "campagne" Precea qui n'avait pas de tableau specs) et inspecter
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


def accept_cookies(page):
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


def dump_specs(page, url, label):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        page.wait_for_timeout(1500)
        log.info(f"\n--- {label} : {url} title={page.title()!r}")
        tables = page.query_selector_all("table")
        log.info(f"    {len(tables)} table(s)")
        for i, t in enumerate(tables[:3]):
            rows = t.query_selector_all("tr")
            log.info(f"    table {i}: {len(rows)} lignes")
            for r in rows[:6]:
                cells = r.query_selector_all("td, th")
                log.info(f"      row: {[c.inner_text().strip()[:40] for c in cells]}")
        text = page.inner_text("body")
        log.info(f"    body text (1000 car.) : {text[:1000]!r}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        page = browser.new_page(user_agent=UA)
        dump_specs(
            page,
            "https://www.horsch.com/fr/produits/travail-du-sol/dechaumeur-a-disques/joker-4-6-hd",
            "Horsch Joker 4-6 HD",
        )
        page.close()

        page = browser.new_page(user_agent=UA)
        try:
            page.goto(
                "https://amazone.fr/fr-fr/produits-et-solutions-digitales/machines-agricoles/fertilisation/epandeurs-portes",
                timeout=25000, wait_until="domcontentloaded",
            )
            page.wait_for_timeout(2000)
            accept_cookies(page)
            page.wait_for_timeout(1000)
            log.info(f"\n=== Amazone épandeurs-portés : title={page.title()!r}")
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            netloc = urlparse(page.url).netloc
            same = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs if netloc in urlparse(h).netloc))
            pertinents = [h for h in same if "epandeur" in h.lower() or "za-" in h.lower()]
            log.info(f"  {len(pertinents)} liens pertinents:")
            for h in pertinents[:30]:
                log.info(f"    {h}")
            if pertinents:
                dump_specs(page, pertinents[0], "Amazone premier épandeur")
        except Exception as e:
            log.warning(f"Amazone épandeurs : échec ({e})")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
