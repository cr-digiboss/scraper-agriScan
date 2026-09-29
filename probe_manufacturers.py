"""
Script de sondage temporaire — à supprimer après usage.
Lot 3 round 2 :
- Hardi : fiche produit (mounted/master)
- Tecnoma : fiche produit (premis)
- Agrifac : fiche produit (vanguard-55)
- Lely : dump complet des liens (round 1 n'a rien trouvé avec le filtre mots-clés)
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


def inspect(page, url, label):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        page.wait_for_timeout(1500)
        log.info(f"\n--- {label} : {url} title={page.title()!r}")
        tables = page.query_selector_all("table")
        log.info(f"    {len(tables)} table(s)")
        for i, t in enumerate(tables[:2]):
            rows = t.query_selector_all("tr")
            for r in rows[:6]:
                cells = r.query_selector_all("td, th")
                log.info(f"      row: {[c.inner_text().strip()[:40] for c in cells]}")
        spec_divs = page.query_selector_all("[class*='spec' i], [class*='caract' i], [class*='fact' i]")
        log.info(f"    {len(spec_divs)} div(s) spec/caract/fact")
        text = page.inner_text("body")
        log.info(f"    body text (900 car.) : {text[:900]!r}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def dump_links(page, url, label):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        accept_cookies(page)
        page.wait_for_timeout(1000)
        log.info(f"\n=== {label} : {url} title={page.title()!r}")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        netloc = urlparse(page.url).netloc
        same = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs if netloc in urlparse(h).netloc))
        log.info(f"  {len(same)} liens")
        for h in same[:80]:
            log.info(f"    {h}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://hardi.com/fr/sprayers/mounted/master", "Hardi Master")
        page.close()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://www.tecnoma.com/produits/pulverisateur-agricoles/pulverisateur-porte/premis/", "Tecnoma Premis")
        page.close()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://www.agrifac.com/fr/pulverisateurs/vanguard-55/", "Agrifac Vanguard 55")
        page.close()

        page = browser.new_page(user_agent=UA)
        dump_links(page, "https://www.lely.com/fr/", "Lely home (dump complet)")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
