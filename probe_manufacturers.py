"""
Script de sondage temporaire — à supprimer après usage.
Dump des liens de 3 pages catégorie (Amazone, John Deere, Kuhn) pour
trouver une vraie fiche modèle à sonder ensuite. Ne touche pas à la
base de données.
"""

import logging
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

PAGES = {
    "Amazone (charrues)": "https://amazone.net/fr/produits-et-solutions-digitales/machines-agricoles/travail-du-sol/charrues",
    "John Deere (Série 6M)": "https://www.deere.be/fr/tracteurs/moyenne/s%C3%A9rie-6m/",
    "Kuhn (mélangeuses 3 vis)": "https://www.kuhn.com/fr/elevage/melangeuses-trainees/melangeuses-3-vis-verticales",
}


def probe(name: str, url: str, page):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        for _ in range(4):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(500)

        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
        )
        final_domain = urlparse(page.url).netloc
        root_domain = ".".join(final_domain.split(".")[-2:])
        base_path = urlparse(page.url).path.rstrip("/")

        # On cherche les liens qui vont PLUS PROFOND que la page actuelle
        # (candidats pour être des fiches modèles individuelles)
        deeper = []
        for l in links:
            u = urlparse(l["href"])
            if root_domain not in l["href"] or not l["text"]:
                continue
            if u.path.rstrip("/").startswith(base_path) and u.path.rstrip("/") != base_path:
                deeper.append(l)

        seen = set()
        uniq = []
        for l in deeper:
            if l["href"] not in seen:
                seen.add(l["href"])
                uniq.append(l)

        log.info(f"Liens plus profonds que la page actuelle : {len(uniq)}")
        for l in uniq[:40]:
            log.info(f"  [{l['text'][:55]:55}] {l['href']}")

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
        for name, url in PAGES.items():
            probe(name, url, page)
        browser.close()


if __name__ == "__main__":
    main()
