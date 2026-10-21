from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def inspect_home(page, url, label):
    print("\n" + "=" * 70)
    print(label, url)
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        print("titre:", page.title())
        print("url finale:", page.url)
        root = page.url.split("//")[1].split("/")[0].replace("www.", "")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if root in h})
        print(f"{len(links)} liens trouves")
        for l in links[:30]:
            print(" ", l)
    except Exception as e:
        print("ERREUR:", e)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)

    # TECNOMA - vraie fiche produit (pas la categorie)
    inspect_home(page, "https://www.tecnoma.com/en/produits/pulverisateur-agricoles/automoteurs/laser/", "TECNOMA produit")

    # AGRIFAC - retry avec networkidle
    try:
        page.goto("https://www.agrifac.com/en/", timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(3000)
        print("\nAGRIFAC (networkidle) titre:", page.title(), "url:", page.url)
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if "agrifac" in h})
        print(f"{len(links)} liens:")
        for l in links[:30]:
            print(" ", l)
    except Exception as e:
        print("AGRIFAC ERREUR:", e)

    # MAHINDRA - essayer d'autres domaines connus
    for url in [
        "https://www.mahindratractor.com/",
        "https://www.mahindraagrimachinery.com/",
        "https://www.mahindra.com/farm-machinery",
    ]:
        inspect_home(page, url, "MAHINDRA tentative")

    # RABE - essayer la home sans /en/
    for url in ["https://www.rabe.de/", "https://rabe.de/en/"]:
        inspect_home(page, url, "RABE tentative")

    browser.close()
