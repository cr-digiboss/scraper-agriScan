"""
Script de sondage temporaire — à supprimer après usage.
Debug New Holland round 2 : chercher des onglets/filtres de série (pas un
bouton "voir plus" classique) qui limiteraient les modèles affichés, et
dumper le texte complet de la page tracteurs pour comprendre la structure.
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


def links_for(page, base_path):
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = set()
    for href in hrefs:
        u = urlparse(href)
        if "newholland.com" not in u.netloc:
            continue
        if u.path.startswith(base_path) and u.path != base_path and u.path.rstrip("/") != base_path.rstrip("/"):
            links.add(href.split("?")[0].split("#")[0])
    return links


def inspect(page, url):
    page.goto(url, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    base_path = urlparse(url).path

    log.info(f"\n=== {url}")
    log.info(f"  liens produits trouvés : {len(links_for(page, base_path))}")

    # chercher des onglets / filtres (role=tab, boutons de filtre série)
    tabs = page.eval_on_selector_all(
        "[role='tab'], [role='tablist'] *, .tab, .filter, [class*='tab'], [class*='filter']",
        "els => els.slice(0,40).map(e => e.tagName + ':' + (e.getAttribute('role')||'') + ':' + e.textContent.trim().slice(0,40))"
    )
    log.info(f"  éléments tab/filter (40 max) : {tabs}")

    # dump texte complet de la zone produits (pour voir s'il y a un compteur
    # "X sur Y modèles" ou des noms de séries non listés dans les liens)
    text = page.inner_text("body")
    log.info(f"  body text ({len(text)} car. ; 2000 affichés) : {text[:2000]!r}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        inspect(page, "https://agriculture.newholland.com/fr-be/europe/produits/tracteurs")
        page.close()

        page = browser.new_page(user_agent=UA)
        inspect(page, "https://agriculture.newholland.com/fr-be/europe/produits/ensileuses")
        page.close()
        browser.close()


if __name__ == "__main__":
    main()
