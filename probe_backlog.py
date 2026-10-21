import requests
from io import BytesIO
import pdfplumber

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

PDFS = {
    "serie-5": "https://landini-tractors.com/content/dam/landini/it/product/rs2b-serie-5/LA_RS57-RS2B_Serie5_Brochure_52p_6697626A2_Web_IT.pdf.inline.pdf",
    "rex4-cab": "https://landini-tractors.com/content/dam/landini/LA_RP5D-RP5E_REX4_Brochure_48p_6717653A2_web_IT.pdf.inline.pdf",
    "serie-6rs": "https://landini-tractors.com/content/dam/landini/it/product/rp-6-d-serie-6-rs/LA_RP6D_SERIE6RS_Brochure_40p_6725833A1_Web_IT.pdf.inline.pdf",
}

for label, url in PDFS.items():
    print("\n" + "=" * 70)
    print(label, url)
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": UA})
        print("status:", r.status_code, "bytes:", len(r.content))
        if r.status_code != 200:
            continue
        with pdfplumber.open(BytesIO(r.content)) as pdf:
            print(f"{len(pdf.pages)} pages")
            # Cherche les pages avec le plus grand nombre de tables (page "caractéristiques techniques")
            best = None
            for pi, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if tables:
                    total_rows = sum(len(t) for t in tables)
                    if best is None or total_rows > best[2]:
                        best = (pi, tables, total_rows)
            if best:
                pi, tables, _ = best
                print(f"meilleure page: {pi} ({len(tables)} tables)")
                for ti, t in enumerate(tables):
                    print(f"  table {ti}: {len(t)} rows x {len(t[0]) if t else 0} cols")
                    for row in t[:6]:
                        print("    ", row)
                text = pdf.pages[pi].extract_text() or ""
                print("  TEXTE page (500 premiers car):", text[:500])
            else:
                print("aucune table trouvee dans le PDF")
    except Exception as e:
        print("ERREUR:", e)
