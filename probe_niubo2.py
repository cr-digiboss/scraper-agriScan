from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

CATEGORY = "https://niubo.info/categoria_maquina/agricola/desbrozadoras-categoria/"


def dump_tables(page, label, url):
    print(f"\n{'='*70}\n{label} — {url}\n{'='*70}")
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        print("titre:", page.title())
        tables = page.query_selector_all("table")
        # ignore les tables de cookies (meme structure partout)
        real_tables = []
        for t in tables:
            rows = t.query_selector_all("tr")
            if rows:
                header = [c.inner_text().strip() for c in rows[0].query_selector_all("td, th")]
                if header[:2] == ["Cookie", "Duración"]:
                    continue
            real_tables.append(t)
        print(f"{len(tables)} tables ({len(real_tables)} hors cookies)")
        for i, t in enumerate(real_tables[:6]):
            rows = t.query_selector_all("tr")
            print(f"  table {i}: {len(rows)} lignes")
            for r in rows[:8]:
                cells = [c.inner_text().strip() for c in r.query_selector_all("td, th")]
                print(f"    {cells}")
    except Exception as e:
        print("ERREUR:", e)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    page.goto(CATEGORY, timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    root = urlparse(CATEGORY).netloc
    links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if root in h})
    print(f"{len(links)} liens trouves sur la categorie:")
    for l in links:
        print(" ", l)

    # cherche des liens qui ne sont ni la categorie elle-meme ni une page generique connue
    generic = {"actualidad", "agricola", "aviso-legal", "contacto", "de", "empresa", "en",
               "forestal", "fr", "garantia-online", "maquinas-para-piedras", "nb-cloud-4-0",
               "politica-de-cookies", "politica-de-privacidad", "privado", "red-comercial",
               "categoria_maquina"}
    candidates = []
    for l in links:
        segs = [s for s in urlparse(l).path.split("/") if s]
        if not segs:
            continue
        if segs[-1] not in generic and "categoria_maquina" not in l:
            candidates.append(l)
    print(f"\n{len(candidates)} candidats fiche machine:")
    for l in candidates:
        print(" ", l)

    for url in candidates[:5]:
        dump_tables(page, "Niubo fiche", url)

    browser.close()
