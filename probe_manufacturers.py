"""
Script de sondage temporaire — à supprimer après usage.
Debug New Holland : l'utilisateur signale un bouton "voir plus de modèles"
sur certaines pages catégorie dont les modèles cachés ne sont pas repris.
Inspecte le DOM pour trouver ce bouton et compare le nombre de liens avant/
après clic.
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

NEW_HOLLAND_CATEGORIES = [
    "https://agriculture.newholland.com/fr-be/europe/produits/tracteurs",
    "https://agriculture.newholland.com/fr-be/europe/produits/presses",
    "https://agriculture.newholland.com/fr-be/europe/produits/moissonneuses-batteuses",
    "https://agriculture.newholland.com/fr-be/europe/produits/ensileuses",
]


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


def inspect(page, url, label):
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        base_path = urlparse(url).path
        before = links_for(page, base_path)
        log.info(f"\n--- {label} : {url}")
        log.info(f"    liens avant clic : {len(before)}")

        # chercher tout élément cliquable mentionnant "plus"/"more"/"voir"
        candidates = page.eval_on_selector_all(
            "button, a, div[role='button'], span[role='button']",
            "els => els.filter(e => /plus|more|voir|afficher|load/i.test(e.textContent)).map(e => e.tagName + ':' + e.textContent.trim().slice(0,60))"
        )
        log.info(f"    éléments candidats 'voir plus' : {candidates[:15]}")

        clicked_total = 0
        for _ in range(10):
            try:
                btn = page.get_by_text("plus", exact=False).first
                if not btn.is_visible(timeout=1000):
                    break
                btn.scroll_into_view_if_needed(timeout=2000)
                btn.click(timeout=2000)
                clicked_total += 1
                page.wait_for_timeout(1500)
            except Exception:
                break

        after = links_for(page, base_path)
        log.info(f"    clics effectués : {clicked_total}")
        log.info(f"    liens après clic(s) : {len(after)}")
        log.info(f"    nouveaux liens révélés : {len(after - before)}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for url in NEW_HOLLAND_CATEGORIES:
            page = browser.new_page(user_agent=UA)
            inspect(page, url, url.split("/")[-1])
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
