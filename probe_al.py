import requests
import pdfplumber
from io import BytesIO

URL = "https://info.amazone.de/displayprospekt.aspx?sprache=1&drucknummer=P0023&path=99*92&display=infoPages&page=24"
REFERER = "https://amazone.net/en/products-digital-solutions/agricultural-technology/fertilising-technology/mounted-spreader/za-m-mounted-spreader-51846"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": REFERER,
}

resp = requests.get(URL, headers=headers, timeout=30, allow_redirects=True)
print("status:", resp.status_code)
print("content-type:", resp.headers.get("Content-Type"))
print("content-length:", len(resp.content))
print("url finale:", resp.url)

if resp.status_code == 200 and "pdf" in resp.headers.get("Content-Type", "").lower():
    with pdfplumber.open(BytesIO(resp.content)) as pdf:
        print(f"{len(pdf.pages)} pages")
        for pi, pg in enumerate(pdf.pages):
            tables = pg.extract_tables()
            text_sample = (pg.extract_text() or "")[:200]
            print(f"page {pi}: {len(tables)} tables, texte: {text_sample!r}")
            for ti, t in enumerate(tables):
                print(f"  table {ti}: {len(t)} lignes")
                for row in t[:8]:
                    print("   ", row)
else:
    print("corps (500 premiers octets):", resp.content[:500])
