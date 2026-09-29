"""
Script de sondage temporaire — à supprimer après usage.
Lot 2 round 6 :
- Bogballe : remonter la chaîne d'ancêtres pour trouver un conteneur stable
  englobant toute la section "Caractéristiques" (pas juste un item)
- Berthoud : cliquer sur "Caractéristiques techniques" pour voir si des
  données structurées apparaissent (comme sur Amazone, qui n'avait que des
  PDF)
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Bogballe : chaîne d'ancêtres
        page = browser.new_page(user_agent=UA)
        page.goto("https://www.bogballe.com/fr/epandeurs-dengrais/modeles/m60w-plus/", timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        loc = page.get_by_text("Largeur de travail", exact=False).first
        info = loc.evaluate("""el => {
            const chain = [];
            let p = el;
            for (let i = 0; i < 10 && p; i++) {
                chain.push({tag: p.tagName, cls: p.className, textLen: p.innerText ? p.innerText.length : 0});
                p = p.parentElement;
            }
            return chain;
        }""")
        log.info(f"Chaîne d'ancêtres Bogballe : {info}")
        # trouver le container avec le texte le plus complet mais pas toute la page
        for lvl in info:
            log.info(f"  {lvl}")
        page.close()

        # Berthoud : cliquer sur Caractéristiques techniques
        page = browser.new_page(user_agent=UA)
        page.goto("https://www.berthoud.com/vega/", timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        try:
            loc = page.get_by_text("Caractéristiques techniques", exact=False).first
            loc.click(timeout=3000)
            page.wait_for_timeout(2500)
            log.info(f"Après clic, URL = {page.url}")
            tables = page.query_selector_all("table")
            log.info(f"  {len(tables)} table(s) après clic")
            for t in tables[:2]:
                rows = t.query_selector_all("tr")
                for r in rows[:8]:
                    cells = r.query_selector_all("td, th")
                    log.info(f"    row: {[c.inner_text().strip()[:40] for c in cells]}")
            text = page.inner_text("body")
            idx = text.lower().find("caractéristique")
            log.info(f"  contexte texte (600 car.) : {text[idx:idx+600]!r}")
        except Exception as e:
            log.warning(f"Berthoud clic échec : {e}")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
