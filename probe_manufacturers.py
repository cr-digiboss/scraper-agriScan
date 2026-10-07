"""
Script de sondage temporaire — à supprimer après usage.
'Tracteur Frutteto Classic' / 'Taille' en base n'est manifestement pas un
vrai modèle (ça ressemble à une étiquette de colonne, "Taille" = pneus).
On télécharge le PDF brochure de la fiche Frutteto Classic et on inspecte
la table brute pour comprendre comment "Taille" a été pris pour un code
modèle par _sdf_find_header_rows.
"""

import logging
from io import BytesIO

import pdfplumber
from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

URL = "https://www.same-tractors.com/fr-fr/tracteurs/frutteto-classic"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ))
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        for sel in ["#onetrust-accept-btn-handler", "button:has-text('Accept')", "button:has-text('Accepter')"]:
            try:
                btn = page.query_selector(sel)
                if btn:
                    btn.click(force=True, timeout=3000)
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                pass
        for _ in range(8):
            page.mouse.wheel(0, 1200)
            page.wait_for_timeout(300)

        pdf_url = scraper._sdf_brochure_pdf_url(page)
        log.info(f"PDF trouvé : {pdf_url}")
        browser.close()

    import requests
    resp = requests.get(pdf_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    with pdfplumber.open(BytesIO(resp.content)) as pdf:
        for pi, pg in enumerate(pdf.pages):
            tables = pg.extract_tables()
            if not tables:
                continue
            for ti, t in enumerate(tables):
                log.info(f"\n--- page {pi+1}, table {ti} : {len(t)} lignes ---")
                for row in t[:6]:
                    log.info(f"  {row}")
                group_idx, model_idx = scraper._sdf_find_header_rows(t)
                log.info(f"  group_idx={group_idx} model_idx={model_idx}")


if __name__ == "__main__":
    main()
