"""
Script de sondage temporaire — à supprimer après usage.
Monosem round PDF-1 : les specs techniques Monosem ne sont disponibles
que dans des PDF téléchargeables (pas de tableau HTML). On télécharge
quelques PDF connus et on teste l'extraction de texte/tableaux avec
pdfplumber, pour savoir si ce sont de vrais PDF texte (exploitables) ou
des scans/images (nécessiteraient de l'OCR, bien plus lourd).
"""

import logging

import requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

PDFS = {
    "Tableau general chassis NG-PLUS": "https://www.monosem.com/en/wp-content/uploads/2026/07/Tableau-general-chassis_NG-PLUS_EN.pdf",
    "Tableau distribution NG-PLUS": "https://www.monosem.com/en/wp-content/uploads/2026/07/Tableau_distribution_NG_PLUS_EN.pdf",
    "Brochure NG-PLUS": "https://www.monosem.com/en/wp-content/uploads/2026/07/Brochure-NG-PLUS_EN_compressed.pdf",
}


def main():
    import pdfplumber

    for label, url in PDFS.items():
        log.info(f"\n{'='*70}\n{label} → {url}")
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            log.info(f"  status: {resp.status_code}, taille: {len(resp.content)} octets")
        except Exception as e:
            log.info(f"  ERREUR download: {e}")
            continue

        path = "/tmp/doc.pdf"
        with open(path, "wb") as f:
            f.write(resp.content)

        try:
            with pdfplumber.open(path) as pdf:
                log.info(f"  {len(pdf.pages)} pages")
                for i, page in enumerate(pdf.pages[:3]):
                    text = page.extract_text() or ""
                    log.info(f"  --- page {i} : {len(text)} caractères de texte extrait ---")
                    log.info(text[:800])
                    tables = page.extract_tables()
                    log.info(f"  --- page {i} : {len(tables)} tableau(x) détecté(s) ---")
                    for t in tables[:2]:
                        log.info(f"    {t[:5]}")
        except Exception as e:
            log.info(f"  ERREUR parsing PDF: {e}")


if __name__ == "__main__":
    main()
