"""
Script de sondage temporaire — à supprimer après usage.
Lot 3, round 5 : Kubota M4003 — cherche l'onglet/accordéon "Caractéristiques
techniques" (probablement chargé en JS), clique dessus, et inspecte le
contenu qui apparaît. Ne touche pas à la base de données.
"""

import logging
import re
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

KUBOTA_MODEL_URL = "https://ke.kubota-eu.com/agriculture/fr/products/m4003/"


def probe_kubota_model(page):
    log.info(f"\n{'=' * 80}\nKubota M4003 (round 5) — {KUBOTA_MODEL_URL}\n{'=' * 80}")
    try:
        page.goto(KUBOTA_MODEL_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Cherche des onglets/boutons/liens mentionnant les caractéristiques
        candidats = page.query_selector_all(
            "a, button, [role='tab'], .tab, [class*='tab' i], [class*='accordion' i]"
        )
        log.info(f"Éléments cliquables candidats (tab/accordion) : {len(candidats)}")
        clicked_any = False
        for el in candidats:
            try:
                txt = clean_text(el.inner_text())
            except Exception:
                continue
            if not txt:
                continue
            if re.search(r"caract[ée]ristique|sp[ée]cification|technical spec|fiche technique", txt, re.I):
                log.info(f"  → clic sur : {txt[:60]!r}")
                try:
                    el.scroll_into_view_if_needed(timeout=5000)
                    el.click(timeout=5000)
                    page.wait_for_timeout(2000)
                    clicked_any = True
                except Exception as e:
                    log.info(f"    (clic échoué : {e})")
        log.info(f"Au moins un clic réussi : {clicked_any}")

        page.wait_for_timeout(2000)
        for _ in range(8):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(400)

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> après interaction : {len(tables)}")
        for i, t in enumerate(tables[:6]):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i}: {len(rows)} lignes")
            for r in rows[:3]:
                log.info(f"    ligne : {r.inner_text().replace(chr(10), ' | ')[:180]}")

        # Recherche brute de motifs numériques de specs dans le texte complet de la page
        body_text = page.inner_text("body")
        numeric_hits = re.findall(r"[A-Za-zÀ-ÿ .'/()-]{3,40}\s*[:\-]?\s*\d+[\.,]?\d*\s?(?:ch|kW|kg|mm|cm|L|l|tr/min)\b", body_text)
        log.info(f"Motifs 'label + valeur numérique + unité' détectés dans le texte : {len(numeric_hits)}")
        for h in numeric_hits[:20]:
            log.info(f"    {h.strip()}")

        # Compte les iframes (specs parfois chargées dans un widget externe)
        iframes = page.query_selector_all("iframe")
        log.info(f"Nombre d'<iframe> : {len(iframes)}")
        for f in iframes[:5]:
            log.info(f"    src={f.get_attribute('src')}")

    except Exception as e:
        log.error(f"Erreur Kubota M4003 round 5 : {e}")


def clean_text(t):
    return re.sub(r"\s+", " ", t or "").strip()


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
        probe_kubota_model(page)
        browser.close()


if __name__ == "__main__":
    main()
