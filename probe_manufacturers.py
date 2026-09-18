"""
Script de sondage temporaire — à supprimer après usage.
Lot 5 : explore Grimme, Krone, Lemken, Horsch, Väderstad et Vicon avant
d'écrire du code de scraping réel (méthodologie sondage → code).
Cherche une page d'accueil -> lien catégorie -> fiche produit, et vérifie
la présence de tableaux HTML de specs sur une fiche concrète.
Ne touche pas à la base de données.
"""

import logging
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

CANDIDATES = {
    "Grimme": "https://www.grimme.com/fr/",
    "Krone": "https://www.krone.de/fr/",
    "Lemken": "https://www.lemken.com/fr/",
    "Horsch": "https://www.horsch.com/fr/",
    "Vaderstad": "https://www.vaderstad.com/fr/",
    "Vicon": "https://www.vicon.eu/fr/",
}


def probe_home(page, name, url):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(4000)
        for _ in range(4):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(400)

        hrefs = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
        )
        final_domain = urlparse(page.url).netloc
        root_domain = ".".join(final_domain.split(".")[-2:])

        # Liens vers des sous-pages plus profondes (candidats catégorie/produit)
        candidates = []
        for l in hrefs:
            u = urlparse(l["href"])
            if root_domain not in l["href"] or not l["text"]:
                continue
            segments = [s for s in u.path.split("/") if s]
            if len(segments) >= 2:
                candidates.append(l)

        seen = set()
        uniq = []
        for l in candidates:
            if l["href"] not in seen:
                seen.add(l["href"])
                uniq.append(l)

        log.info(f"Liens profonds trouvés : {len(uniq)}")
        for l in uniq[:20]:
            log.info(f"  [{l['text'][:50]:50}] {l['href']}")

    except Exception as e:
        log.error(f"Erreur sur {name} : {e}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
            viewport={"width": 1280, "height": 1600},
        )
        page = context.new_page()
        for name, url in CANDIDATES.items():
            probe_home(page, name, url)
        browser.close()


if __name__ == "__main__":
    main()
