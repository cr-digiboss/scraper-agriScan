"""
Script de sondage temporaire — à supprimer après usage.
Round 2 : la fiche produit McHale n'a AUCUNE table, AUCUN élément
[class*=spec/technical], AUCUN titre avec mot-clé specs, AUCUN PDF.
Dump exhaustif : toutes les classes uniques présentes sur la page,
tous les boutons/onglets cliquables, et un extrait du texte brut complet
de la page pour localiser où sont réellement les caractéristiques.
"""

import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

URL = "https://www.mchale.net/products/691-round-bale-handler/"


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
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(500)

        # Toutes les classes uniques présentes sur la page
        classes = page.eval_on_selector_all(
            "*[class]",
            "els => [...new Set(els.flatMap(e => [...e.classList]))]",
        )
        log.info(f"Nombre de classes CSS uniques : {len(classes)}")
        keyword_classes = [c for c in classes if any(
            k in c.lower() for k in ["spec", "tech", "detail", "feature", "data", "tab", "accordion"]
        )]
        log.info(f"Classes contenant un mot-clé pertinent : {keyword_classes}")

        # Boutons / onglets cliquables
        buttons = page.eval_on_selector_all(
            "button, [role=tab], [role=button], a.tab, .tab, .accordion-title, .accordion-header",
            "els => els.map(e => e.textContent.trim()).filter(t => t)",
        )
        log.info(f"Boutons/onglets trouvés ({len(buttons)}) : {buttons[:30]}")

        # Structure des sections principales (id + classe des <section>/<div> de premier niveau sous main/body)
        sections = page.eval_on_selector_all(
            "main *, body > div *",
            "els => els.slice(0, 0)",
        )

        # Texte brut complet (tronqué) pour repérer visuellement où sont les caractéristiques
        body_text = page.inner_text("body")
        log.info(f"Longueur texte body : {len(body_text)} caractères")
        log.info("--- Texte body (2000 premiers caractères) ---")
        log.info(body_text[:2000])
        log.info("--- Texte body (2000 derniers caractères) ---")
        log.info(body_text[-2000:])

        # Cherche le mot "kg", "mm", "cm" dans le texte pour localiser une zone de chiffres/unités
        import re
        matches = list(re.finditer(r".{40}(kg|mm|cm|litre|litres|tonnes?).{20}", body_text, re.I))
        log.info(f"Occurrences proches d'unités (kg/mm/cm/litre/tonne) : {len(matches)}")
        for m in matches[:15]:
            log.info(f"  ...{m.group(0)}...")

        browser.close()


if __name__ == "__main__":
    main()
