from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

HOME = "https://niubo.info/"


def dump(page, label, url):
    print(f"\n{'='*70}\n{label} — {url}\n{'='*70}")
    try:
        resp = page.goto(url, timeout=25000, wait_until="domcontentloaded")
        print("status:", resp.status if resp else None)
        page.wait_for_timeout(2500)
        print("titre:", page.title())
        tables = page.query_selector_all("table")
        print(f"{len(tables)} tables")
        for i, t in enumerate(tables[:6]):
            rows = t.query_selector_all("tr")
            print(f"  table {i}: {len(rows)} lignes")
            for r in rows[:6]:
                cells = [c.inner_text().strip() for c in r.query_selector_all("td, th")]
                print(f"    {cells}")
    except Exception as e:
        print("ERREUR:", e)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    dump(page, "Niubo home", HOME)
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    root = urlparse(HOME).netloc
    links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if root in h})
    print(f"\n{len(links)} liens internes trouves:")
    for l in links[:60]:
        print(" ", l)

    # essaie de visiter quelques liens plausibles de fiche produit
    candidates = [l for l in links if any(k in l.lower() for k in ["producto", "product", "maquina", "gama", "catalogo"])]
    print(f"\n{len(candidates)} candidats fiche produit:")
    for l in candidates[:15]:
        print(" ", l)

    for url in candidates[:4]:
        dump(page, "Niubo candidat", url)

    browser.close()
