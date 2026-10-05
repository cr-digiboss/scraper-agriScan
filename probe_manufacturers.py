"""
Script de sondage temporaire — à supprimer après usage.
Case IH round modeles-10 (dernier essai) : capture des requêtes réseau
déclenchées par le clic sur TRACTEURS, attente plus longue, et inspection
du contenu réel des 2 iframes (via content_frame()) plutôt que juste
leur attribut src.
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

        # Inspection du contenu réel des iframes (frames du navigateur).
        log.info(f"{len(page.frames)} frames (y compris principale) :")
        for fr in page.frames:
            log.info(f"  url={fr.url!r} name={fr.name!r}")

        requests_seen = []
        page.on("request", lambda req: requests_seen.append((req.resource_type, req.url)))

        locs = page.locator("text=TRACTEURS")
        for i in range(locs.count()):
            loc = locs.nth(i)
            if loc.is_visible():
                loc.click(timeout=5000, force=True)
                break

        page.wait_for_timeout(8000)

        log.info(f"\n{len(page.frames)} frames après clic :")
        for fr in page.frames:
            log.info(f"  url={fr.url!r} name={fr.name!r}")

        log.info(f"\n{len(requests_seen)} requêtes réseau après le clic :")
        for rtype, url in requests_seen:
            if rtype in ("xhr", "fetch", "document"):
                log.info(f"  [{rtype}] {url}")

        browser.close()


if __name__ == "__main__":
    main()
