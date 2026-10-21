from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

BRANDS = {
    "tecnoma": "https://www.tecnoma.com/en/",
    "agrifac": "https://www.agrifac.com/en/",
    "mahindra": "https://www.mahindratractorworld.com/",
    "rabe": "https://www.rabe.de/en/",
    "gregoire-besson": "https://www.gregoire-besson.com/en/",
    "landini": "https://landini-tractors.com/gb/en.html",
    "merlo": "https://www.merlo.com/",
}

with sync_playwright() as p:
    browser = p.chromium.launch()
    for brand, home in BRANDS.items():
        print("\n" + "=" * 70)
        print(f"MARQUE: {brand}")
        print("=" * 70)
        page = browser.new_page(user_agent=UA)
        try:
            page.goto(home, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            print("titre:", page.title())
            print("url finale:", page.url)
            root = page.url.split("//")[1].split("/")[0].replace("www.", "")
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            links = sorted({h.split('?')[0].split('#')[0] for h in hrefs if root in h})
            print(f"{len(links)} liens trouves sur le domaine")
            for l in links[:35]:
                print(" ", l)
        except Exception as e:
            print("ERREUR:", e)
        page.close()
    browser.close()
