import requests
import pdfplumber
from io import BytesIO

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

url = "https://www.deutz-fahr.com/media/308.8901.3.4-1_Serie_5_Stage_V_EN.pdf"
resp = requests.get(url, timeout=30, headers={"User-Agent": UA})
with pdfplumber.open(BytesIO(resp.content)) as pdf:
    for pi in [25, 26]:
        pg = pdf.pages[pi]
        tbls = pg.extract_tables()
        print(f"\n=== page {pi} : {len(tbls)} table(s) ===")
        for ti, t in enumerate(tbls):
            print(f"\n--- table {ti} ({len(t)} lignes) ---")
            for ri, row in enumerate(t):
                print(f"  row {ri}: {row}")
