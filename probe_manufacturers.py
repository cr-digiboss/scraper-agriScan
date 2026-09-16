"""
Script de sondage temporaire — à supprimer après usage.
Lot 2, round 3 : dump complet du tableau Pöttinger Aerosem M (lignes 3-14
non vues au round 2) et crawl d'un niveau supplémentaire sur les
sous-gammes Deutz-Fahr trouvées (Série 6.4, Série 6C). Ne touche pas à la
base de données.
"""

import logging
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

POETTINGER_URL = "https://www.poettinger.at/fr_be/produkte/detail/asemm/aerosem-m-semoirs-pneumatiques-portes"

DEUTZ_SUBRANGES = {
    "Deutz-Fahr (Série 6.4)": "https://www.deutz-fahr.com/fr-bx/tracteurs/serie-6-4",
    "Deutz-Fahr (Série 6C)": "https://www.deutz-fahr.com/fr-bx/tracteurs/serie-6c",
}


def probe_poettinger_full_table(page):
    log.info(f"\n{'=' * 80}\nPöttinger (Aerosem M) — dump complet — {POETTINGER_URL}\n{'=' * 80}")
    try:
        page.goto(POETTINGER_URL, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        for _ in range(5):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(600)

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> : {len(tables)}")
        for i, t in enumerate(tables):
            rows = t.query_selector_all("tr")
            log.info(f"  Table {i}: {len(rows)} lignes — dump complet :")
            for j, r in enumerate(rows):
                log.info(f"    ligne {j} : {r.inner_text().replace(chr(10), ' | ')[:300]}")

    except Exception as e:
        log.error(f"Erreur Pöttinger : {e}")


def probe_deutz_subrange(name: str, url: str, page):
    log.info(f"\n{'=' * 80}\n{name} — {url}\n{'=' * 80}")
    try:
        resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
        log.info(f"HTTP status: {resp.status if resp else 'N/A'}")
        page.wait_for_timeout(5000)
        for _ in range(4):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(500)

        tables = page.query_selector_all("table")
        log.info(f"Nombre de <table> sur cette page : {len(tables)}")

        links = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
        )
        final_domain = urlparse(page.url).netloc
        root_domain = ".".join(final_domain.split(".")[-2:])
        base_path = urlparse(page.url).path.rstrip("/")

        deeper = []
        for l in links:
            u = urlparse(l["href"])
            if root_domain not in l["href"] or not l["text"]:
                continue
            if u.path.rstrip("/").startswith(base_path) and u.path.rstrip("/") != base_path:
                deeper.append(l)

        seen = set()
        uniq = []
        for l in deeper:
            if l["href"] not in seen:
                seen.add(l["href"])
                uniq.append(l)

        log.info(f"Liens plus profonds que la page actuelle : {len(uniq)}")
        for l in uniq[:30]:
            log.info(f"  [{l['text'][:55]:55}] {l['href']}")

    except Exception as e:
        log.error(f"Erreur sur {name} : {e}")


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
        probe_poettinger_full_table(page)
        for name, url in DEUTZ_SUBRANGES.items():
            probe_deutz_subrange(name, url, page)
        browser.close()


if __name__ == "__main__":
    main()
