"""
Script de sondage temporaire — à supprimer après usage.
Round 5 (dernier) : vérifier qu'il n'existe pas un vrai tableau de specs
par modèle caché sous une autre classe (comme découvert pour Kubota),
avant d'abandonner définitivement Deutz-Fahr.
"""

import logging
import re

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

_POWER_RE = re.compile(r"\d{2,3}\s*(ch|cv|kw)\b", re.IGNORECASE)


def inspect_deutzfahr_full(page, url):
    log.info(f"\n===== Deutz-Fahr full : {url} =====")
    try:
        page.goto(url, timeout=35000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)

        body_text = page.inner_text("body")
        matches = _POWER_RE.findall(body_text)
        log.info(f"  Occurrences motif puissance (ch/cv/kW) : {len(matches)}")
        for m in _POWER_RE.finditer(body_text):
            start = max(0, m.start() - 60)
            log.info("    ..." + body_text[start:m.end() + 20].replace("\n", " | "))

        # divs stylés "table" ou "grid" avec plusieurs lignes
        candidates = page.query_selector_all("[class*='table' i], [class*='grid' i], [role='table']")
        log.info(f"  Éléments class*=table/grid ou role=table : {len(candidates)}")
        for el in candidates[:10]:
            cls = el.get_attribute("class")
            txt = el.inner_text().strip().replace("\n", " ")[:150]
            log.info(f"    <{cls}> {txt}")

        # liens PDF / fiches techniques
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        pdfs = [h for h in hrefs if ".pdf" in h.lower()]
        log.info(f"  Liens PDF : {len(pdfs)}")
        for p in pdfs[:10]:
            log.info(f"    {p}")
    except Exception as e:
        log.info(f"  ERREUR : {e!r}")


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

        inspect_deutzfahr_full(page, "https://www.deutz-fahr.com/fr-fr/tracteurs/serie-9-stage-5")

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
