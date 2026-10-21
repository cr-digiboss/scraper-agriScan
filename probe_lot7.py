from playwright.sync_api import sync_playwright

URL = "https://www.vredo.com/en/products/agri-solutions/agricultural-overseeders/agri-air/"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    # Cherche l'element contenant "DOWNLOAD PRODUCT SPECIFICATIONS"
    el = page.get_by_text("DOWNLOAD PRODUCT SPECIFICATIONS", exact=False).first
    try:
        tag = el.evaluate("e => e.tagName")
        outer = el.evaluate("e => e.outerHTML")
        print("tag:", tag)
        print("outerHTML:", outer[:1000])
        href = el.get_attribute("href")
        print("href direct:", href)
    except Exception as e:
        print("ERREUR element:", e)

    # Cherche aussi tous les liens/boutons contenant 'download' ou 'specification'
    hrefs = page.eval_on_selector_all(
        "a, button",
        "els => els.filter(e => (e.textContent||'').toLowerCase().includes('download') || (e.textContent||'').toLowerCase().includes('specification')).map(e => ({tag: e.tagName, href: e.getAttribute('href'), onclick: e.getAttribute('onclick'), text: (e.textContent||'').trim().slice(0,60)}))"
    )
    print("\nElements download/specification trouves:")
    for h in hrefs:
        print(" ", h)

    # Cherche les liens pdf meme masques / data-attributes
    all_links = page.eval_on_selector_all(
        "a", "els => els.map(e => ({href: e.getAttribute('href'), data: e.getAttribute('data-href') || e.getAttribute('data-url')}))"
    )
    pdf_like = [l for l in all_links if l.get('href') and 'pdf' in (l['href'] or '').lower()]
    pdf_like += [l for l in all_links if l.get('data') and 'pdf' in (l['data'] or '').lower()]
    print("\nLiens contenant 'pdf' (href ou data-attr):", pdf_like)

    browser.close()
