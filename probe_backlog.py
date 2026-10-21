from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

failed_requests = []

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA, viewport={"width": 1366, "height": 900})
    page.on("requestfailed", lambda req: failed_requests.append((req.url, req.failure)))
    page.on("response", lambda resp: print("RESP", resp.status, resp.url) if resp.status >= 400 else None)

    page.goto("https://www.landini.it/en/", timeout=25000, wait_until="load")
    page.wait_for_timeout(3000)
    for _ in range(5):
        page.mouse.wheel(0, 800)
        page.wait_for_timeout(1500)

    html = page.content()
    print("longueur HTML apres scroll:", len(html))
    idx = html.find('<section class="container">')
    print("extrait section:", html[idx:idx + 1000])

    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    print(f"\n{len(hrefs)} liens <a> apres scroll")
    for h in hrefs[:40]:
        print(" ", h)

    print("\nrequetes echouees:", len(failed_requests))
    for u, f in failed_requests[:20]:
        print(" ", u, f)

    browser.close()
