"""
Script de sondage temporaire — à supprimer après usage.
Lot 4, round 2 : vérifie les tableaux de specs sur des fiches modèles déjà
identifiées (McHale, Geringhoff, Bogballe, Einböck, Naïo, AVR), retente
individuellement Agrisem/Jeulin/Güttler (navigation interrompue au round 1)
et Kemper/Capello/Warzée/Actisol avec des URLs alternatives. Ne touche pas
à la base de données.
"""

import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

PRODUCT_PAGES = {
    "McHale (V8960)": "https://www.mchale.net/products/v8960/",
    "Geringhoff (North Star)": "https://www.geringhoff.com/en_US/Products/Corn-Heads/North-Star-/p/gp_MaisStar",
    "Bogballe (M60W Plus)": "https://www.bogballe.com/fertiliser-spreaders/models/m60w-plus/",
    "Einböck (Vibrostar)": "https://www.einboeck.at/produkte/bodenbearbeitung/feingrubber/vibrostar/",
    "Naïo Technologies (Oz)": "https://www.naio-technologies.com/oz/",
    "AVR (Puma)": "https://www.avrmachinery.com/en/product/avr-puma",
}

RETRY_INDIVIDUAL = {
    "Agrisem": "https://www.agrisem.com/",
    "Jeulin": "https://www.jeulin.fr/",
    "Güttler": "https://www.guettler.de/",
}

RETRY_ALT_URLS = {
    "Kemper (alt)": "https://www.kemper-online.de/",
    "Capello (alt)": "https://www.capello.it/",
    "Warzée (alt)": "https://www.warzee.eu/",
    "Actisol (alt)": "https://actisol.fr/",
}


def probe_product(name: str, url: str, page):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(5000)
        for _ in range(5):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(600)
        log.info(f"Titre : {page.title()}")

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> : {len(tables)}")
        for i, t in enumerate(tables[:5]):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i}: {len(rows)} lignes")
            for r in rows[:3]:
                log.info(f"    ligne : {r.inner_text().replace(chr(10), ' | ')[:200]}")

        spec_divs = page.query_selector_all(
            "[class*='spec' i], [class*='technical' i], [class*='caracteristique' i], "
            "[class*='fiche-technique' i], [class*='donnees-techniques' i], [class*='daten' i]"
        )
        log.info(f"Éléments classe spec/technical : {len(spec_divs)}")
        for d in spec_divs[:3]:
            txt = d.inner_text().strip().replace("\n", " | ")
            if txt:
                log.info(f"    échantillon : {txt[:300]}")

        pdf_links = page.eval_on_selector_all("a[href*='.pdf' i]", "els => els.map(e => e.href)")
        log.info(f"PDF trouvés : {len(pdf_links)}")

    except Exception as e:
        log.error(f"Erreur sur {name} : {e}")


def probe_site(name: str, url: str, page):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=30000, wait_until="load")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(5000)
        log.info(f"Titre : {page.title()}")
        log.info(f"URL finale : {page.url}")

        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
        )
        internal = [l for l in links if l["text"]]
        seen = set()
        uniq = []
        for l in internal:
            if l["href"] not in seen:
                seen.add(l["href"])
                uniq.append(l)
        log.info(f"Liens trouvés : {len(uniq)} (échantillon des 40 premiers)")
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
        for name, url in PRODUCT_PAGES.items():
            probe_product(name, url, page)
        page.close()

        # Une page neuve par site pour éviter toute interférence de navigation
        for name, url in RETRY_INDIVIDUAL.items():
            fresh_page = context.new_page()
            probe_site(name, url, fresh_page)
            fresh_page.close()

        for name, url in RETRY_ALT_URLS.items():
            fresh_page = context.new_page()
            probe_site(name, url, fresh_page)
            fresh_page.close()

        browser.close()


if __name__ == "__main__":
    main()
