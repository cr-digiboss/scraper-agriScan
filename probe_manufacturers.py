"""
Script de sondage temporaire — à supprimer après usage.
Debug New Holland round 4 : inspecter la section "MODÈLES" + le tableau de
specs détaillé (après clic "TOUT DÉVELOPPER") sur une fiche famille T7 XD.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

URL = "https://agriculture.newholland.com/fr-be/europe/produits/tracteurs/t7-xd"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        log.info(f"title={page.title()!r}")
        tables_before = page.query_selector_all("table")
        log.info(f"tables avant clic : {len(tables_before)}")
        for i, t in enumerate(tables_before):
            rows = t.query_selector_all("tr")
            log.info(f"  table {i}: {len(rows)} rows")
            for r in rows[:5]:
                cells = r.query_selector_all("td, th")
                log.info(f"    row: {[c.inner_text().strip()[:30] for c in cells]}")

        # chercher le bouton "TOUT DÉVELOPPER"
        try:
            btn = page.get_by_text("TOUT DÉVELOPPER", exact=False).first
            log.info(f"bouton 'TOUT DÉVELOPPER' visible : {btn.is_visible(timeout=2000)}")
            btn.click(timeout=3000)
            page.wait_for_timeout(2000)
        except Exception as e:
            log.warning(f"clic TOUT DÉVELOPPER échoué : {e}")

        tables_after = page.query_selector_all("table")
        log.info(f"\ntables après clic : {len(tables_after)}")
        for i, t in enumerate(tables_after):
            rows = t.query_selector_all("tr")
            log.info(f"  table {i}: {len(rows)} rows")
            for r in rows[:10]:
                cells = r.query_selector_all("td, th")
                log.info(f"    row: {[c.inner_text().strip()[:30] for c in cells]}")

        # dump de la zone MODÈLES spécifiquement (div/section contenant "MODÈLES")
        modeles_html = page.evaluate("""
            () => {
                const all = Array.from(document.querySelectorAll('div, section'));
                for (const el of all) {
                    const t = el.textContent || '';
                    if (t.includes('T7.360 XD') && t.includes('T7.390 XD') && t.length < 3000) {
                        return {tag: el.tagName, cls: el.className, html: el.outerHTML.slice(0, 2000)};
                    }
                }
                return null;
            }
        """)
        log.info(f"\nzone MODÈLES (candidat le plus petit) : {modeles_html}")

        browser.close()


if __name__ == "__main__":
    main()
