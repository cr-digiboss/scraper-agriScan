"""
Script de sondage temporaire — à supprimer après usage.
Round 7 : le conteneur ".specifiche-tecniche_wrapper-table__table" reste
vide même après clic sur un onglet texte. On capture TOUTES les requêtes
réseau (XHR/fetch) déclenchées pendant le chargement de la page Same
Virtus, pour repérer un éventuel appel API qui alimenterait ce tableau,
et on essaie aussi un scroll complet de la page (déclencheur possible :
IntersectionObserver / lazy-hydration Vue.js).
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

URL = "https://www.same-tractors.com/fr-fr/tracteurs/virtus"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        requests_seen = []

        def on_request(req):
            if req.resource_type in ("xhr", "fetch"):
                requests_seen.append(req.url)

        page.on("request", on_request)

        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        log.info(f"Requêtes XHR/fetch observées au chargement initial ({len(requests_seen)}) :")
        for u in requests_seen:
            log.info(f"  {u}")

        # Scroll complet de la page, section par section, pour déclencher un
        # éventuel lazy-load basé sur la position de scroll.
        requests_seen.clear()
        page.evaluate(
            """
            async () => {
                const step = window.innerHeight;
                const max = document.body.scrollHeight;
                for (let y = 0; y < max; y += step) {
                    window.scrollTo(0, y);
                    await new Promise(r => setTimeout(r, 400));
                }
                window.scrollTo(0, max);
            }
            """
        )
        page.wait_for_timeout(3000)

        log.info(f"\nRequêtes XHR/fetch observées après scroll complet ({len(requests_seen)}) :")
        for u in requests_seen:
            log.info(f"  {u}")

        wrapper = page.query_selector(".specifiche-tecniche_wrapper-table__table")
        if wrapper:
            html = wrapper.evaluate("e => e.outerHTML")
            log.info(f"\nwrapper après scroll, longueur HTML : {len(html)}")
            log.info(html[:3000])

        browser.close()


if __name__ == "__main__":
    main()
