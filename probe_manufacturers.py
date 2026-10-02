"""
Script de sondage temporaire — à supprimer après usage.
Debug New Holland round 4 : round 3 a confirmé que cliquer sur
"VOIR PLUS DE MODÈLES" ne fait PAS grossir le <table> de specs (resté à
7 colonnes/22 rows avant/après). Le tableau est donc découplé de la
galerie de cartes "MODÈLES". On inspecte ici la structure de cette
galerie (cartes avant/après clic, liens éventuels) pour savoir où se
trouvent les données des modèles manquants.
"""

import json
import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

URL = "https://agriculture.newholland.com/fr-be/europe/produits/moissonneuses-batteuses/barres-de-coupe-varifeed-pour-moissonneuses-batteuses"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        try:
            accept = page.locator("#onetrust-accept-btn-handler")
            if accept.is_visible(timeout=3000):
                accept.click(timeout=3000)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        def describe_cards():
            return page.evaluate(
                """
                () => {
                    const root = document.querySelector('[class*="model-listing"]');
                    if (!root) return {found: false};
                    const items = Array.from(
                        root.querySelectorAll('[class*="model-listing__item"], [class*="model-listing__card"]')
                    );
                    const sample = items.slice(0, 20).map(it => ({
                        tag: it.tagName,
                        cls: it.className,
                        text: it.innerText.trim().slice(0, 60),
                        href: it.querySelector('a') ? it.querySelector('a').href : (it.tagName === 'A' ? it.href : null),
                    }));
                    return {found: true, count: items.length, sample, rootClass: root.className};
                }
                """
            )

        before = describe_cards()
        log.info(f"AVANT clic -- cartes: {json.dumps(before, ensure_ascii=False, indent=2)}")

        clicks = 0
        for _ in range(10):
            try:
                btn = page.get_by_text("VOIR PLUS DE MODÈLES", exact=False).first
                if not btn.is_visible(timeout=1500):
                    break
                btn.scroll_into_view_if_needed(timeout=2000)
                btn.click(timeout=2000)
                clicks += 1
                page.wait_for_timeout(1500)
            except Exception as e:
                log.info(f"  arrêt clic : {e}")
                break

        log.info(f"\nclics effectués : {clicks}")
        after = describe_cards()
        log.info(f"APRES clic(s) -- cartes: {json.dumps(after, ensure_ascii=False, indent=2)}")

        # Les tables de specs ont-elles un attribut identifiant le modèle (ancre, data-*) ?
        tables_info = page.evaluate(
            """
            () => {
                const tables = Array.from(document.querySelectorAll('table'));
                return tables.map((t, i) => ({
                    index: i,
                    id: t.id || null,
                    cls: t.className || null,
                    parentCls: t.parentElement ? t.parentElement.className : null,
                }));
            }
            """
        )
        log.info(f"\ntables sur la page : {json.dumps(tables_info, ensure_ascii=False, indent=2)}")

        browser.close()


if __name__ == "__main__":
    main()
