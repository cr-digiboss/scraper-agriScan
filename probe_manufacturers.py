"""
Script de sondage temporaire — à supprimer après usage.
Lot 6 round 3 : suivre le sélecteur de pays Rauch vers la France (25-fr.html)
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def dump_links(page, url, label):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        log.info(f"\n=== {label} : {url} title={page.title()!r} final_url={page.url!r}")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        same = sorted(set(h.split("?")[0].split("#")[0] for h in hrefs))
        log.info(f"  {len(same)} liens")
        for h in same[:100]:
            log.info(f"    {h}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        dump_links(page, "https://rauch.de/land-waehlen/25-fr.html", "Rauch FR (via selecteur de pays)")
        page.close()
        browser.close()


if __name__ == "__main__":
    main()
