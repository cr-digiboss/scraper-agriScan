"""
Script de sondage temporaire — à supprimer après usage.
Lot 3, round 3 : creuse le contenu complet du bloc "specs" trouvé chez
McCormick (teaser ou fiche complète ?) et corrige l'URL Kubota (sous-domaine
pays France). Ne touche pas à la base de données.
"""

import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

MCCORMICK_URL = "https://mccormick-tractors.com/fr/fr/produits/x8-vt-drive.html"
KUBOTA_URL = "https://ke.kubota-eu.com/agriculture/fr/?country=fr"


def probe_mccormick(page):
    log.info(f"\n{'=' * 80}\nMcCormick (détail specs) — {MCCORMICK_URL}\n{'=' * 80}")
    try:
        page.goto(MCCORMICK_URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        for _ in range(6):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(600)

        spec_divs = page.query_selector_all(
            "[class*='spec' i], [class*='technical' i], [class*='caracteristique' i]"
        )
        log.info(f"Éléments classe spec/technical : {len(spec_divs)}")
        for i, d in enumerate(spec_divs):
            cls = d.get_attribute("class")
            txt = d.inner_text().strip().replace("\n", " | ")
            log.info(f"  [{i}] class={cls}")
            log.info(f"      texte complet ({len(txt)} car.) : {txt[:1500]}")

        # Cherche aussi un lien "voir plus" / "toutes les caractéristiques"
        links = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
        )
        candidats = [l for l in links if any(
            k in l["text"].lower() for k in ["caractéristique", "spec", "technique", "fiche"]
        )]
        log.info(f"Liens 'voir plus specs' candidats : {len(candidats)}")
        for l in candidats[:10]:
            log.info(f"  [{l['text'][:60]}] {l['href']}")

    except Exception as e:
        log.error(f"Erreur McCormick : {e}")


def probe_kubota(page):
    log.info(f"\n{'=' * 80}\nKubota France (agriculture) — {KUBOTA_URL}\n{'=' * 80}")
    try:
        resp = page.goto(KUBOTA_URL, timeout=30000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(5000)
        for _ in range(4):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(500)
        log.info(f"Titre : {page.title()}")
        log.info(f"URL finale : {page.url}")

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> : {len(tables)}")

        links = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
        )
        internal = [l for l in links if "kubota" in l["href"].lower() and l["text"]]
        seen = set()
        uniq = []
        for l in internal:
            if l["href"] not in seen:
                seen.add(l["href"])
                uniq.append(l)
        log.info(f"Liens internes uniques trouvés : {len(uniq)} (échantillon des 60 premiers)")
        for l in uniq[:60]:
            log.info(f"  [{l['text'][:55]:55}] {l['href']}")

    except Exception as e:
        log.error(f"Erreur Kubota : {e}")


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
        probe_mccormick(page)
        probe_kubota(page)
        browser.close()


if __name__ == "__main__":
    main()
