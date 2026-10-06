"""
Script de sondage temporaire — à supprimer après usage.
Diagnostic : scrape_deutz_fahr() renvoie 0 machines même après ajout du
scroll (alors que scrape_same() marche bien). On réutilise directement
_sdf_product_links / _sdf_scrape_brand de scraper.py pour voir exactement
quelles URLs sont collectées et pourquoi aucun PDF n'est détecté dessus.
"""

import logging

from playwright.sync_api import sync_playwright

import scraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ))

        home = scraper.SDF_SITES["Deutz-Fahr"]
        page.goto(home, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        for sel in ["#onetrust-accept-btn-handler", "button:has-text('Accept')", "button:has-text('Accepter')"]:
            try:
                btn = page.query_selector(sel)
                if btn:
                    btn.click(force=True, timeout=3000)
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                pass

        links = scraper._sdf_product_links(page, home)
        log.info(f"{len(links)} liens collectés :")
        for u in sorted(links):
            log.info(f"  {u}")

        # Inspecter les 3 premiers en détail : cookie banner toujours là ?
        # lien PDF présent sous un autre format ?
        for url in sorted(links)[:3]:
            log.info(f"\n{'='*70}\n{url}")
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            for _ in range(8):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(300)

            cookie_still_there = page.query_selector("#onetrust-banner-sdk")
            log.info(f"  Bandeau cookies encore présent : {bool(cookie_still_there)}")

            all_hrefs = page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => ({href: e.href, text: e.innerText.trim()}))"
            )
            pdf_like = [h for h in all_hrefs if ".pdf" in h["href"].lower() or "brochure" in h["text"].lower() or "télécharg" in h["text"].lower()]
            log.info(f"  {len(all_hrefs)} liens au total, {len(pdf_like)} PDF/brochure-like :")
            for h in pdf_like:
                log.info(f"    {h}")

            log.info(f"  Titre de la page : {page.title()!r}")

        browser.close()


if __name__ == "__main__":
    main()
