from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)
    page.goto("https://www.schaeffer.de/en/products/10/compact-loader-4670", timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    el = page.query_selector("#techdata")
    if el:
        html = el.inner_html()
        print("longueur HTML #techdata:", len(html))
        print(html[:2000])
        print("\n--- texte brut ---")
        print(el.inner_text()[:2000])
    else:
        print("id=techdata non trouve")
        # fallback: chercher tout element avec id contenant "tech"
        ids = page.eval_on_selector_all("[id]", "els => els.map(e => e.id)")
        print("tous les ids:", [i for i in ids if i])

    browser.close()
