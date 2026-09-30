"""
Script de sondage temporaire — à supprimer après usage.
Lot 4 round 5 :
- Ropa : après clic sur l'onglet specs, identifier le conteneur DOM des
  caractéristiques (classes) pour ne récupérer que ce bloc, pas toute la page
- Joskin : accepter le bon texte de cookies puis chercher l'onglet
  "Caractéristiques techniques" sur une fiche modèle
"""

import logging

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

COOKIE_TEXTS = [
    "Tout accepter", "Accepter tout", "Accept all", "J'accepte", "Accepter",
    "ACCEPTER LES COOKIES ESSENTIELS UNIQUEMENT",
    "Accepter les cookies essentiels uniquement",
]


def accept_cookies(page):
    for text in COOKIE_TEXTS:
        try:
            btn = page.get_by_text(text, exact=False).first
            if btn.is_visible(timeout=1500):
                btn.click(timeout=1500)
                page.wait_for_timeout(1000)
                return True
        except Exception:
            continue
    return False


def ropa_probe(page, url):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        page.wait_for_timeout(1000)
        try:
            tab = page.get_by_text("CARACTÉRISTIQUES TECHNIQUES", exact=False).first
            tab.click(timeout=5000)
            page.wait_for_timeout(2000)
        except Exception as e:
            log.warning(f"    clic échec : {e}")
        # dump classes of elements that contain "LONGUEUR" text (a known spec label)
        info = page.evaluate("""
            () => {
                const all = Array.from(document.querySelectorAll('*'));
                const hits = [];
                for (const el of all) {
                    if (el.children.length === 0 && el.textContent.trim() === 'LONGUEUR') {
                        let p = el;
                        let chain = [];
                        for (let i = 0; i < 6 && p; i++) {
                            chain.push(p.tagName + '.' + (p.className || '').toString().slice(0,60));
                            p = p.parentElement;
                        }
                        hits.push(chain);
                    }
                }
                return hits;
            }
        """)
        log.info(f"\n--- Ropa : chaînes DOM autour de 'LONGUEUR' : {info}")
        # try to find a reasonable container and dump its innerText
        container_info = page.evaluate("""
            () => {
                const all = Array.from(document.querySelectorAll('div, section'));
                for (const el of all) {
                    const t = el.textContent || '';
                    if (t.includes('LONGUEUR') && t.includes('CAPACITÉ DE TRÉMIE') && t.length < 4000) {
                        return {cls: el.className, tag: el.tagName, len: t.length, text: t.slice(0, 1500)};
                    }
                }
                return null;
            }
        """)
        log.info(f"--- Ropa : conteneur candidat = {container_info}")
    except Exception as e:
        log.warning(f"  Ropa : échec ({e})")


def joskin_probe(page, url):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        accept_cookies(page)
        page.wait_for_timeout(1500)
        log.info(f"\n--- Joskin : {url} title={page.title()!r}")
        # look for any tab/link mentioning "caractéristiques"
        candidates = page.eval_on_selector_all(
            "a, button, div, li",
            "els => els.filter(e => e.textContent.toLowerCase().includes('caract')).map(e => e.tagName + ':' + e.textContent.trim().slice(0,60))"
        )
        log.info(f"    éléments mentionnant 'caract' : {candidates[:20]}")
        tables = page.query_selector_all("table")
        log.info(f"    {len(tables)} table(s) avant clic")
        if candidates:
            try:
                tab = page.get_by_text("aractéristiques", exact=False).first
                tab.click(timeout=5000)
                page.wait_for_timeout(2000)
                tables = page.query_selector_all("table")
                log.info(f"    {len(tables)} table(s) après clic")
                for t in tables[:2]:
                    rows = t.query_selector_all("tr")
                    for r in rows[:8]:
                        cells = r.query_selector_all("td, th")
                        log.info(f"      row: {[c.inner_text().strip()[:40] for c in cells]}")
            except Exception as e:
                log.warning(f"    clic échec : {e}")
        text = page.inner_text("body")
        log.info(f"    body text (1500 car.) : {text[:1500]!r}")
    except Exception as e:
        log.warning(f"  Joskin : échec ({e})")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        page = browser.new_page(user_agent=UA)
        ropa_probe(page, "https://www.ropa-maschinenbau.de/fr/produits/arracheuse-de-betteraves/panther-2s/")
        page.close()

        page = browser.new_page(user_agent=UA)
        joskin_probe(page, "https://www.joskin.com/fr/epandeurs-de-lisier/alpina2")
        page.close()

        browser.close()


if __name__ == "__main__":
    main()
