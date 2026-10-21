from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

URLS = [
    "https://www.deutz-fahr.com/en-nd/tractors/5-series",
    "https://www.deutz-fahr.com/en-nd/tractors/3-series",
    "https://www.deutz-fahr.com/en-nd/tractors/5d-series",
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(user_agent=UA)
    for url in URLS:
        print("\n" + "=" * 70)
        print(url)
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        print("titre:", page.title())

        all_links = page.eval_on_selector_all(
            "a", "els => els.map(e => ({href: e.getAttribute('href'), text: (e.textContent||'').trim().slice(0,50)}))"
        )
        pdf_like = [l for l in all_links if l.get('href') and ('.pdf' in l['href'].lower() or 'brochure' in l['href'].lower() or 'download' in l['href'].lower())]
        print(f"{len(pdf_like)} liens pdf/brochure/download-like:")
        for l in pdf_like[:10]:
            print(" ", l)

        text_like = [l for l in all_links if 'brochure' in (l.get('text') or '').lower() or 'download' in (l.get('text') or '').lower()]
        print(f"\n{len(text_like)} liens avec texte brochure/download:")
        for l in text_like[:10]:
            print(" ", l)
    browser.close()
