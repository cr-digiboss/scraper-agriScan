from playwright.sync_api import sync_playwright

AMAZONE_PRODUCT = "https://amazone.net/en/products-digital-solutions/agricultural-technology/fertilising-technology/mounted-spreader/za-m-mounted-spreader-51846"
LELY_PRODUCT = "https://www.lely.com/solutions/milking/astronaut/"


def inspect(page, url, label):
    print("\n" + "=" * 70)
    print(label, url)
    page.goto(url, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    print("titre:", page.title())
    tables = page.query_selector_all("table")
    print(f"{len(tables)} tables HTML")
    for t in tables[:3]:
        txt = t.inner_text().strip().replace("\n", " | ")
        print("  echantillon:", txt[:400])

    # tous les liens de la page (pour reperer brochures/PDF/specs)
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    interesting = sorted({h for h in hrefs if any(
        k in h.lower() for k in ["pdf", "spec", "brochure", "download", "datasheet", "technical"]
    )})
    print(f"{len(interesting)} liens 'specs/pdf/download'-like:")
    for h in interesting[:15]:
        print("  ", h)

    # Recherche de mots cles dans le texte visible de la page
    body_text = page.inner_text("body")
    print(f"longueur texte body: {len(body_text)}")
    for kw in ["Technical data", "Specifications", "Hopper", "Working width", "Weight", "kg"]:
        print(f"  contient {kw!r} ? {kw.lower() in body_text.lower()}")

    # Boutons/onglets "specs" a cliquer ?
    tab_like = page.query_selector_all(
        "[class*='tab' i], [class*='accordion' i], button, [role='tab']"
    )
    print(f"{len(tab_like)} elements tab/accordion/button")
    labels = []
    for el in tab_like[:40]:
        t = el.inner_text().strip()
        if t:
            labels.append(t)
    print("libelles:", labels[:40])


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    inspect(page, AMAZONE_PRODUCT, "AMAZONE PRODUIT (ZA-M)")
    inspect(page, LELY_PRODUCT, "LELY PRODUIT (Astronaut)")
    browser.close()
