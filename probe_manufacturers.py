"""
Script de sondage temporaire — à supprimer après usage.
Lot 1 round 4 : finaliser la structure des fiches produit.
- Amazone : gérer le bandeau cookies puis inspecter une fiche produit
- Vicon : inspecter une fiche produit (andaineur Andex 644)
- Maschio Gaspardo : lister /fr_fr/all-products puis inspecter une fiche (bora.html)
- Horsch : descendre d'un niveau sous travail-du-sol/dechaumeur-a-disques
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
            for r in rows[:5]:
                cells = r.query_selector_all("td, th")
                log.info(f"      row: {[c.inner_text().strip()[:40] for c in cells]}")
        # divs de type spec-item / caractéristique
        spec_divs = page.query_selector_all("[class*='spec' i], [class*='caract' i], [class*='techdata' i], [class*='feature' i]")
        log.info(f"    {len(spec_divs)} div(s) 'spec/caract/techdata/feature'")
        for d in spec_divs[:15]:
            t = d.inner_text().strip().replace("\n", " | ")[:150]
            if t:
                log.info(f"      spec-div: {t}")
        text = page.inner_text("body")
        log.info(f"    body text (1200 car., apres cookies) : {text[:1200]!r}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def dump_links(page, url, label, keyword_filter=None):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        page.wait_for_timeout(1000)
        log.info(f"\n=== {label} : {url} title={page.title()!r}")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        netloc = urlparse(url).netloc
        same = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs if netloc in urlparse(h).netloc))
        if keyword_filter:
            same = [h for h in same if keyword_filter(h)]
        log.info(f"  {len(same)} liens")
        for h in same[:60]:
            log.info(f"    {h}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        page = browser.new_page(user_agent=UA)
        dump_specs(
            page,
            "https://amazone.fr/fr-fr/produits-et-solutions-digitales/machines-agricoles/semis/semoirs-monograines/amazone-semoir-monograine-precea-6000-2cc-475842",
            "Amazone Precea 6000-2CC",
        )
        page.close()

        page = browser.new_page(user_agent=UA)
        dump_specs(
            page,
            "https://fr.vicon.eu/andaineurs/andaineurs-double-rotor/vicon-andex-644",
            "Vicon Andex 644",
        )
        page.close()

        page = browser.new_page(user_agent=UA)
        dump_links(
            page,
            "https://www.maschiogaspardo.com/fr_fr/all-products",
            "Maschio Gaspardo all-products",
            keyword_filter=lambda h: h.endswith(".html"),
        )
        page.close()

        page = browser.new_page(user_agent=UA)
        dump_specs(page, "https://www.maschiogaspardo.com/fr_fr/bora.html", "Maschio Gaspardo Bora")
        page.close()

        page = browser.new_page(user_agent=UA)
        dump_links(
            page,
            "https://www.horsch.com/fr/produits/travail-du-sol/dechaumeur-a-disques",
            "Horsch dechaumeur-a-disques",
        )
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
