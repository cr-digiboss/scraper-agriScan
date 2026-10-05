"""
Script de sondage temporaire — à supprimer après usage.
Case IH round modeles-9 : le bouton TRACTEURS du configurateur n'a pas de
href classique. On cherche une iframe (plateforme tierce fréquente pour
ces outils CNH), puis on clique sur TRACTEURS en observant les nouvelles
pages/popups et tout changement d'iframe.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

URL = "https://www.caseih.com/fr-fr/france/outils-et-ressources/configurateur"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(user_agent=UA)
        page = context.new_page()
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        try:
            accept = page.locator("#onetrust-accept-btn-handler")
            if accept.is_visible(timeout=3000):
                accept.click(timeout=3000)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        iframes = page.query_selector_all("iframe")
        log.info(f"{len(iframes)} iframes trouvées :")
        for f in iframes:
            log.info(f"  src={f.get_attribute('src')}")

        # Clique sur TRACTEURS (copie visible) et observe nouvel onglet /
        # navigation / changement d'iframe.
        new_pages = []
        context.on("page", lambda p2: new_pages.append(p2))

        locs = page.locator("text=TRACTEURS")
        n = locs.count()
        log.info(f"\n{n} éléments texte 'TRACTEURS'")
        clicked = False
        for i in range(n):
            loc = locs.nth(i)
            if loc.is_visible():
                log.info(f"clic sur occurrence {i}")
                try:
                    loc.click(timeout=5000, force=True)
                    clicked = True
                except Exception as e:
                    log.info(f"  échec clic : {e}")
                break
        page.wait_for_timeout(4000)

        log.info(f"\nclic effectué : {clicked}")
        log.info(f"URL page principale : {page.url}")
        log.info(f"nouveaux onglets ouverts : {len(new_pages)}")
        for np in new_pages:
            try:
                np.wait_for_load_state(timeout=5000)
            except Exception:
                pass
            log.info(f"  nouvel onglet URL : {np.url}")

        iframes2 = page.query_selector_all("iframe")
        log.info(f"\n{len(iframes2)} iframes après clic :")
        for f in iframes2:
            log.info(f"  src={f.get_attribute('src')}")

        browser.close()


if __name__ == "__main__":
    main()
