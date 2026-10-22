import requests
from io import BytesIO
import pdfplumber
import re

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

PDFS = {
    "serie-5": "https://landini-tractors.com/content/dam/landini/it/product/rs2b-serie-5/LA_RS57-RS2B_Serie5_Brochure_52p_6697626A2_Web_IT.pdf.inline.pdf",
    "rex4-cab": "https://landini-tractors.com/content/dam/landini/LA_RP5D-RP5E_REX4_Brochure_48p_6717653A2_web_IT.pdf.inline.pdf",
    "serie-6rs": "https://landini-tractors.com/content/dam/landini/it/product/rp-6-d-serie-6-rs/LA_RP6D_SERIE6RS_Brochure_40p_6725833A1_Web_IT.pdf.inline.pdf",
}


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def variant_columns(table, words):
    """Associe chaque colonne 'valeur' (au-dela de label+unite) a un nom de
    variante, en alignant le x-milieu des mots d'en-tete juste au-dessus de
    la table avec le x-range des colonnes d'une ligne de reference."""
    # ligne de reference = celle avec le plus de cellules non-None (definit les colonnes)
    ref_row = max(table.rows, key=lambda r: sum(1 for c in r.cells if c))
    col_ranges = {i: c for i, c in enumerate(ref_row.cells) if c}
    if len(col_ranges) < 3:
        return {}, []

    value_col_idxs = sorted(col_ranges.keys())[2:]  # on saute label(0) + unite(1)
    if not value_col_idxs:
        value_col_idxs = sorted(col_ranges.keys())[1:]  # pas de colonne unite

    table_top = table.bbox[1]
    header_words = [w for w in words if table_top - 30 <= w["bottom"] <= table_top + 2]

    mapping = {}
    for idx in value_col_idxs:
        x0, _, x1, _ = col_ranges[idx]
        mid_candidates = [w for w in header_words if x0 <= (w["x0"] + w["x1"]) / 2 <= x1]
        if mid_candidates:
            mapping[idx] = clean(" ".join(w["text"] for w in mid_candidates))
    return mapping, value_col_idxs


for label, url in PDFS.items():
    print("\n" + "=" * 70)
    print(label)
    r = requests.get(url, timeout=30, headers={"User-Agent": UA})
    with pdfplumber.open(BytesIO(r.content)) as pdf:
        all_specs = {}  # variant -> {attr: val}
        for pi, page in enumerate(pdf.pages):
            tables = page.find_tables()
            if not tables:
                continue
            words = page.extract_words()
            for table in tables:
                mapping, value_col_idxs = variant_columns(table, words)
                if not mapping:
                    continue
                for variant in mapping.values():
                    all_specs.setdefault(variant, {})
                data = table.extract()
                for row_i, row in enumerate(data):
                    row_obj = table.rows[row_i]
                    label_cell = clean(row[0]) if row[0] else ""
                    if not label_cell or label_cell.isupper() and len(label_cell) > 3 and all(c is None for c in row_obj.cells[1:]):
                        continue
                    unit_cell = clean(row[1]) if len(row) > 1 and row[1] else ""
                    # ligne "propre" : chaque colonne valeur a sa PROPRE cellule (pas de merge)
                    clean_row = all(row_obj.cells[i] is not None for i in value_col_idxs)
                    if not clean_row:
                        continue
                    for idx in value_col_idxs:
                        variant = mapping.get(idx)
                        val = clean(row[idx]) if idx < len(row) and row[idx] else ""
                        if variant and val and label_cell:
                            attr = f"{label_cell} ({unit_cell})" if unit_cell else label_cell
                            all_specs[variant][attr] = val
        print(f"{len(all_specs)} variantes trouvees:")
        for v, specs in all_specs.items():
            print(f"  '{v}': {len(specs)} attributs -> {dict(list(specs.items())[:4])}")
