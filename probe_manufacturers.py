"""
Script de sondage temporaire — à supprimer après usage.
Lot 4 (suite 2) :
- Holmer : scan des 48 pages du PDF pour trouver une éventuelle page de
  caractéristiques techniques (table ou texte avec mots-clés)
- Joskin : inspection du PDF spécifique au modèle (focus_alpina2_-_FR.pdf)
"""

import io
import logging

import pdfplumber
import requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

KEYWORDS = ["caractéristiques techniques", "données techniques", "dimensions", "poids", "puissance"]


def scan_pdf_for_specs(url, label):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        log.info(f"\n--- {label} : {url} ({len(r.content)} octets)")
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            log.info(f"    {len(pdf.pages)} page(s)")
            for i, page in enumerate(pdf.pages):
                text = (page.extract_text() or "").lower()
                tables = page.extract_tables()
                real_tables = [t for t in tables if len(t) > 1 and any(any(c for c in row) for row in t)]
                hit = any(k in text for k in KEYWORDS)
                if real_tables or hit:
                    log.info(f"    page {i+1}: {len(real_tables)} table(s) réelle(s), mot-clé={hit}")
                    if real_tables:
                        for t in real_tables[:2]:
                            for row in t[:10]:
                                log.info(f"      row: {row}")
                    elif hit:
                        raw = page.extract_text() or ""
                        log.info(f"      texte (800 car.) : {raw[:800]!r}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def inspect_pdf_full(url, label):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        log.info(f"\n--- {label} : {url} ({len(r.content)} octets)")
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            log.info(f"    {len(pdf.pages)} page(s)")
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                tables = page.extract_tables()
                real_tables = [t for t in tables if len(t) > 1]
                log.info(f"    page {i+1}: {len(text)} car. texte, {len(real_tables)} table(s)")
                if real_tables:
                    for t in real_tables[:3]:
                        for row in t[:10]:
                            log.info(f"      row: {row}")
                elif text:
                    log.info(f"      texte (600 car.) : {text[:600]!r}")
    except Exception as e:
        log.warning(f"  {label} : échec ({e})")


def main():
    scan_pdf_for_specs(
        "https://www.holmer-maschinenbau.com/fileadmin/PDF/Produkt-PDFe/WEB_2025-05-12_Terra_Dos_5_Prospekt_FR.pdf",
        "Holmer Terra Dos 5 — scan complet",
    )

    inspect_pdf_full(
        "https://quote.joskin.com/system/attachments/files/000/000/561/original/focus_alpina2_-_FR.pdf",
        "Joskin focus_alpina2_FR",
    )


if __name__ == "__main__":
    main()
