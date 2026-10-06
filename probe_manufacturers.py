"""
Script de sondage temporaire — à supprimer après usage.
Round 5 : on a maintenant de vraies pages produit (via le menu ouvert) :
- Deutz-Fahr : /fr-fr/tracteurs/serie-6, serie-7-ttv, serie-8, serie-9-stage-5
- Same : /fr-fr/tracteurs/dorado, frutteto, krypton, virtus
On inspecte ces fiches produit : présence de <table>, de liens PDF, et de
boutons "brochure"/"fiche technique"/"télécharger".
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

URLS = [
    "https://www.deutz-fahr.com/fr-fr/tracteurs/serie-6",
    "https://www.deutz-fahr.com/fr-fr/tracteurs/serie-9-stage-5",
    "https://www.same-tractors.com/fr-fr/tracteurs/dorado",
    "https://www.same-tractors.com/fr-fr/tracteurs/virtus",
]


def accept_cookies(page):
    for sel in ["#onetrust-accept-btn-handler", "button:has-text('Accept')", "button:has-text('Accepter')"]:
        try:
            btn = page.query_selector(sel)
            if btn:
                btn.click(force=True, timeout=3000)
                page.wait_for_timeout(1500)
                return
        except Exception:
            pass


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)

        for url in URLS:
            log.info(f"\n{'='*70}\n{url}")
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)
            except Exception as e:
                log.warning(f"  Inaccessible : {e}")
                continue
            accept_cookies(page)
            page.wait_for_timeout(2000)
            for _ in range(8):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(300)

            tables = page.query_selector_all("table")
            log.info(f"  {len(tables)} tables sur la page")

            hrefs = page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => ({href: e.href, text: e.innerText.trim()}))"
            )
            pdf_links = [h for h in hrefs if h["href"].lower().split("?")[0].endswith(".pdf")]
            log.info(f"  PDF trouvés : {len(pdf_links)}")
            for p_ in pdf_links:
                log.info(f"    {p_}")

            brochure_candidates = [
                h for h in hrefs
                if any(k in h["text"].lower() for k in ["brochure", "fiche technique", "télécharger", "download", "catalogue", "pdf"])
            ]
            log.info(f"  Boutons/liens 'brochure'-like : {len(brochure_candidates)}")
            for b in brochure_candidates:
                log.info(f"    {b}")

            # Boutons qui ne sont pas des <a> (ex: déclenchent un téléchargement en JS).
            btn_candidates = page.eval_on_selector_all(
                "button, [role='button']",
                "els => els.map(e => e.innerText.trim()).filter(t => t.length > 0 && t.length < 60)"
            )
            interesting_btns = [b for b in btn_candidates if any(k in b.lower() for k in ["brochure", "fiche", "télécharg", "download", "catalogue", "pdf"])]
            log.info(f"  Boutons JS 'brochure'-like : {interesting_btns}")

        browser.close()


if __name__ == "__main__":
    main()
