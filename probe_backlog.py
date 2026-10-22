import requests
from io import BytesIO
import pdfplumber
import re

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

URL = "https://landini-tractors.com/content/dam/landini/it/product/rs2b-serie-5/LA_RS57-RS2B_Serie5_Brochure_52p_6697626A2_Web_IT.pdf.inline.pdf"

r = requests.get(URL, timeout=30, headers={"User-Agent": UA})

with pdfplumber.open(BytesIO(r.content)) as pdf:
    page = pdf.pages[23]
    tables = page.find_tables()
    t = tables[0]
    print(f"table bbox={t.bbox}, {len(t.rows)} rows")
    for ri, row in enumerate(t.rows[:6]):
        print(f"\nrow {ri}:")
        for ci, cell in enumerate(row.cells):
            print(f"  col {ci}: bbox={cell}")

    words = page.extract_words()
    header_words = [w for w in words if 85 <= w["top"] <= 95]
    print("\nmots d'en-tete (top 85-95):")
    for w in header_words:
        print(f"  '{w['text']}' x0={w['x0']:.1f} x1={w['x1']:.1f}")
