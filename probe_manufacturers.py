"""
Script de sondage temporaire — à supprimer après usage.
Round 8 : round 7 n'a capté aucun appel réseau lié aux specs (seulement
un appel de traductions UI). Hypothèse : les données sont déjà intégrées
dans le HTML initial (état d'hydratation Vue.js, ex. window.__NUXT__ ou
similaire) et le composant ne se monte juste pas correctement en mode
headless. On cherche un gros blob JSON dans le <script> de la page, et on
capture les erreurs JS console/page qui pourraient expliquer un montage
raté du composant.
"""

import logging
import re

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

        console_errors = []
        page_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        page.goto(URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(5000)

        log.info(f"Erreurs console ({len(console_errors)}) :")
        for e in console_errors[:20]:
            log.info(f"  {e[:300]}")

        log.info(f"\nErreurs page ({len(page_errors)}) :")
        for e in page_errors[:20]:
            log.info(f"  {e[:300]}")

        html = page.content()
        log.info(f"\nTaille HTML totale : {len(html)}")

        # Cherche des variables globales d'état connues (Nuxt/Vue courantes)
        for pattern in ["__NUXT__", "__INITIAL_STATE__", "window.__", "specifiche", "wrapper-table"]:
            count = html.count(pattern)
            log.info(f"  occurrences de {pattern!r} dans le HTML brut : {count}")

        # Essaie de localiser et d'extraire un éventuel bloc JSON proche de
        # "specifiche" pour voir s'il contient déjà les données.
        idx = html.find("specifiche")
        if idx != -1:
            log.info(f"\ncontexte autour de la 1ere occurrence de 'specifiche' (idx={idx}) :")
            log.info(html[max(0, idx - 200):idx + 800])

        # Vérifie aussi le wrapper après attente réseau idle (plus long que
        # les rounds précédents).
        wrapper = page.query_selector(".specifiche-tecniche_wrapper-table__table")
        if wrapper:
            inner = wrapper.evaluate("e => e.outerHTML")
            log.info(f"\nwrapper (networkidle) longueur HTML : {len(inner)}")
            log.info(inner[:2000])

        browser.close()


if __name__ == "__main__":
    main()
