import requests
import pdfplumber
from io import BytesIO

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

url = "https://landini-tractors.com/content/dam/landini/gb/products/rs2b-serie-5/LA_RS57-RS2B_Serie5_Brochure_52p_6697627A2_Web_EN.pdf.inline.pdf"
resp = requests.get(url, timeout=30, headers={"User-Agent": UA})
print("status:", resp.status_code, "bytes:", len(resp.content))
with pdfplumber.open(BytesIO(resp.content)) as pdf:
    print(f"{len(pdf.pages)} pages")
    for pi, pg in enumerate(pdf.pages):
        tbls = pg.extract_tables()
        if tbls:
            print(f"\npage {pi}: {len(tbls)} table(s), texte: {(pg.extract_text() or '')[:150]!r}")
            for ti, t in enumerate(tbls):
                print(f"  table {ti}: {len(t)} lignes")
                for row in t[:10]:
                    print("   ", row)
