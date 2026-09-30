"""
Script de sondage temporaire — à supprimer après usage.
Lot 4 (suite) : essai d'extraction de données techniques depuis des PDF
pour Holmer et Joskin (aucune donnée structurée trouvée en HTML).
"""

import io
import logging

import pdfplumber
import requests
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def inspect_pdf(url, label):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        log.info(f"\n--- {label} : {url} ({len(r.content)} octets)")
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            log.info(f"    {len(pdf.pages)} page(s)")
            for i, page in enumerate(pdf.pages[:6]):
                text = page.extract_text() or ""
                tables = page.extract_tables()
                log.info(f"    page {i+1}: {len(text)} car. texte, {len(tables)} table(s)")
                if tables:
                    for t in tables[:2]:
                        for row in t[:6]:
                            log.info(f"      row: {row}")
                elif text:
                    log.info(f"      texte (500 car.) : {text[:500]!r}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def find_pdf_links(page, url, label):
    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        for text in ["Tout accepter", "Accepter tout", "Accept all", "J'accepte", "Accepter",
                     "ACCEPTER LES COOKIES ESSENTIELS UNIQUEMENT"]:
            try:
                btn = page.get_by_text(text, exact=False).first
                if btn.is_visible(timeout=1200):
                    btn.click(timeout=1200)
                    page.wait_for_timeout(800)
                    break
            except Exception:
                continue
        page.wait_for_timeout(1000)
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        pdfs = sorted(set(h for h in hrefs if h.lower().endswith(".pdf")))
        log.info(f"\n=== {label} : {url} — {len(pdfs)} PDF(s) trouvé(s)")
        for h in pdfs[:20]:
            log.info(f"    {h}")
        return pdfs
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")
        return []


def main():
    # Holmer : PDF déjà identifié lors du sondage précédent
    inspect_pdf(
        "https://www.holmer-maschinenbau.com/fileadmin/PDF/Produkt-PDFe/WEB_2025-05-12_Terra_Dos_5_Prospekt_FR.pdf",
        "Holmer Terra Dos 5 (brochure FR)",
    )

    with sync_playwright() as p:
        browser = p.chromium.launch()

        page = browser.new_page(user_agent=UA)
        pdfs = find_pdf_links(page, "https://www.joskin.com/fr/epandeurs-de-lisier/alpina2", "Joskin Alpina2")
        page.close()

        browser.close()

    for pdf_url in pdfs[:2]:
        inspect_pdf(pdf_url, f"Joskin PDF ({pdf_url.split('/')[-1]})")


if __name__ == "__main__":
    main()
