"""
Script de sondage temporaire — à supprimer après usage.
Lot 6, round 3 :
- Amazone : 0 table trouvée sur une fiche produit -> chercher où sont les specs
  (onglets à cliquer, accordéons, sections par mot-clé).
- Kuhn : round 2 a ouvert des pages de sous-catégorie, pas de vraies fiches
  produit -> ouvrir une vraie fiche (master-103) et chercher les tables.
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

AMAZONE_URL = "https://amazone.fr/fr-fr/produits-et-solutions-digitales/machines-agricoles/travail-du-sol/charrues/charrue-cayros-portee-a-braquage-complet-298404"
KUHN_URL = "https://www.kuhn.fr/grande-culture/materiels-de-travail-du-sol/charrues/charrues-portees-reversibles/master-103"


def probe_amazone(page):
    log.info(f"\n===== Amazone fiche : {AMAZONE_URL} =====")
    page.goto(AMAZONE_URL, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    for _ in range(8):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(300)

    # Chercher boutons / onglets contenant des mots-clés specs
    candidats_boutons = page.query_selector_all(
        "button, a, [role='tab'], [class*='tab' i], [class*='accordion' i]"
    )
    log.info(f"  Boutons/onglets candidats : {len(candidats_boutons)}")
    mots = ["caractérist", "technique", "spec", "données", "detail"]
    matches = []
    for el in candidats_boutons:
        try:
            txt = (el.inner_text() or "").strip().lower()
        except Exception:
            continue
        if txt and any(m in txt for m in mots):
            matches.append(txt)
    log.info(f"  Boutons/onglets matchant mots-clés : {matches[:20]}")

    # Chercher dl/dt/dd
    dls = page.query_selector_all("dl")
    log.info(f"  <dl> trouvés : {len(dls)}")

    # Chercher iframe
    iframes = page.query_selector_all("iframe")
    log.info(f"  <iframe> trouvés : {len(iframes)}")
    for i, ifr in enumerate(iframes[:5]):
        log.info(f"    iframe {i} src={ifr.get_attribute('src')}")

    # Dump du texte brut de la page (les 3000 premiers car. après le titre)
    body_text = page.inner_text("body")
    log.info(f"  Longueur texte body : {len(body_text)}")
    idx = body_text.lower().find("caractérist")
    if idx == -1:
        idx = body_text.lower().find("technique")
    if idx != -1:
        log.info("  Extrait autour du mot-clé trouvé :")
        log.info("  " + body_text[max(0, idx - 100):idx + 900].replace("\n", " | "))
    else:
        log.info("  Aucun mot-clé 'caractérist'/'technique' trouvé dans le texte visible.")


def probe_kuhn(page):
    log.info(f"\n===== Kuhn fiche : {KUHN_URL} =====")
    page.goto(KUHN_URL, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    for _ in range(8):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(300)

    title = page.title()
    log.info(f"  Titre : {title}")
    tables = page.query_selector_all("table")
    log.info(f"  Tables trouvées : {len(tables)}")
    for i, t in enumerate(tables[:3]):
        txt = t.inner_text()
        log.info(f"  --- table {i} ({len(txt)} car.) ---")
        log.info("  " + txt[:500].replace("\n", " | "))

    if not tables:
        specish = page.query_selector_all(
            "[class*='spec' i], [class*='technical' i], [class*='caracteristique' i], [class*='fiche' i]"
        )
        log.info(f"  Éléments spec-like : {len(specish)}")
        for i, el in enumerate(specish[:5]):
            cls = el.get_attribute("class") or ""
            txt = el.inner_text()
            log.info(f"  --- elt {i} class=\"{cls}\" ({len(txt)} car.) ---")
            log.info("  " + txt[:400].replace("\n", " | "))


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
        try:
            probe_amazone(page)
        except Exception as e:
            log.info(f"  ERREUR Amazone : {e!r}")
        page.close()

        page = context.new_page()
        try:
            probe_kuhn(page)
        except Exception as e:
            log.info(f"  ERREUR Kuhn : {e!r}")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
