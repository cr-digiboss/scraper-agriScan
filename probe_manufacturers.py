"""
Script de sondage temporaire — à supprimer après usage.
Round 6 : des PDF "brochure" téléchargeables ont été trouvés sur des fiches
produit Deutz-Fahr et Same (ex. Serie_6_PS-RCS-TTV_FR.pdf, DORADO_Stage_V_FR.pdf,
VIRTUS_Stage_V_FR.pdf). On les télécharge et on vérifie avec pdfplumber s'ils
contiennent de vrais tableaux de specs exploitables (comme pour Monosem) ou
si c'est juste du texte marketing / des images.
"""

import logging
from io import BytesIO

import pdfplumber
import requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

PDFS = {
    "Deutz-Fahr Série 6": "https://www.deutz-fahr.com/media/308.8924.2.4-0_Serie_6_PS-RCS-TTV_FR.pdf",
    "Same Dorado": "https://www.same-tractors.com/media/308.8908.2.1-1_DORADO_Stage_V_FR_LOW.pdf",
    "Same Virtus": "https://www.same-tractors.com/media/308.8905.2.1-1_VIRTUS_-_Stage_V_FR.pdf",
}


def main():
    for name, url in PDFS.items():
        log.info(f"\n{'='*70}\n{name} — {url}")
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
        except Exception as e:
            log.warning(f"  Téléchargement échoué : {e}")
            continue

        log.info(f"  Taille : {len(resp.content)} octets")

        try:
            with pdfplumber.open(BytesIO(resp.content)) as pdf:
                log.info(f"  {len(pdf.pages)} pages")
                total_tables = 0
                for i, pg in enumerate(pdf.pages):
                    tables = pg.extract_tables()
                    if tables:
                        total_tables += len(tables)
                        log.info(f"    page {i+1} : {len(tables)} table(s)")
                        for t in tables:
                            n_rows = len(t)
                            n_cols = max(len(r) for r in t) if t else 0
                            log.info(f"      {n_rows} lignes x {n_cols} colonnes")
                            # Montrer les 3 premières lignes pour juger du contenu.
                            for row in t[:3]:
                                log.info(f"        {row}")
                log.info(f"  TOTAL : {total_tables} tables trouvées dans ce PDF")
        except Exception as e:
            log.warning(f"  Erreur pdfplumber : {e}")


if __name__ == "__main__":
    main()
