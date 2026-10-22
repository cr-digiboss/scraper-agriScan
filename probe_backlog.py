import requests
from io import BytesIO
import pdfplumber
import re

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

URL = "https://landini-tractors.com/content/dam/landini/it/product/rs2b-serie-5/LA_RS57-RS2B_Serie5_Brochure_52p_6697626A2_Web_IT.pdf.inline.pdf"

r = requests.get(URL, timeout=30, headers={"User-Agent": UA})
print("status:", r.status_code, "bytes:", len(r.content))

with pdfplumber.open(BytesIO(r.content)) as pdf:
    page = pdf.pages[23]
    print("page size:", page.width, page.height)

    # Trouve les "tables" structurelles (avec bbox) pour avoir position x des colonnes.
    found_tables = page.find_tables()
    print(f"{len(found_tables)} tables trouvees (find_tables)")
    for ti, t in enumerate(found_tables):
        print(f"\n--- table {ti} bbox={t.bbox} ---")
        rows = t.rows
        if rows:
            first_row_cells = rows[0].cells
            print("  cellules ligne 0 (bbox par colonne):", first_row_cells)

    # Cherche les mots au-dessus du haut de la 1ere table (candidats = noms de variantes)
    words = page.extract_words()
    if found_tables:
        top_table_y0 = min(t.bbox[1] for t in found_tables)
        header_zone_words = [w for w in words if w["bottom"] <= top_table_y0 + 5 and w["top"] >= top_table_y0 - 40]
        print(f"\n{len(header_zone_words)} mots dans la zone d'en-tete (juste au-dessus des tables):")
        for w in header_zone_words:
            print(f"  '{w['text']}' x0={w['x0']:.1f} x1={w['x1']:.1f} top={w['top']:.1f}")

    # Variant pattern check: mots ressemblant a des codes modeles
    model_like = [w for w in words if re.match(r"^\d-\d{2,3}$", w["text"]) or re.match(r"^REX", w["text"])]
    print(f"\n{len(model_like)} mots ressemblant a des codes modele sur toute la page:")
    for w in model_like:
        print(f"  '{w['text']}' x0={w['x0']:.1f} x1={w['x1']:.1f} top={w['top']:.1f}")
