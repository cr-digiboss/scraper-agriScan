"""
Export vers Excel — AgriScan Machines
Génère agriscan_machines.xlsx avec mise en forme et onglets par catégorie.
"""

import openpyxl
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side
)
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from dataclasses import asdict
from scrapers.base import Machine
import datetime
from itertools import count as _count
_TABLE_COUNTER = _count(1)

# Couleurs AgriScan (vert agricole)
COLOR_HEADER_BG  = "2E7D32"   # vert foncé
COLOR_HEADER_FG  = "FFFFFF"   # blanc
COLOR_ROW_ALT    = "F1F8E9"   # vert très clair
COLOR_ROW_WHITE  = "FFFFFF"
COLOR_BORDER     = "A5D6A7"   # vert clair

COLUMNS = [
    ("brand",       "brand",       20),
    ("range",       "range",       20),
    ("name",        "name",        28),
    ("variant",     "variant",     20),
    ("category",    "category",    25),
    ("subcategory", "subcategory", 25),
    ("description", "description", 60),
    ("specs",       "specs",       30),
    ("imageUrl",    "imageUrl",    45),
    ("videoUrl",    "videoUrl",    30),
    ("sourceUrl",   "sourceUrl",   45),
]


def _border():
    side = Side(style="thin", color=COLOR_BORDER)
    return Border(left=side, right=side, top=side, bottom=side)


def _write_sheet(ws, machines: list[Machine], sheet_title: str):
    """Écrit les machines dans un onglet avec mise en forme."""

    # ── En-tête ──────────────────────────────────────────────────────────
    ws.row_dimensions[1].height = 30
    for col_idx, (label, _, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font      = Font(name="Arial", bold=True, color=COLOR_HEADER_FG, size=11)
        cell.fill      = PatternFill("solid", fgColor=COLOR_HEADER_BG)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
        cell.border    = _border()
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # ── Données ──────────────────────────────────────────────────────────
    for row_idx, machine in enumerate(machines, start=2):
        d = {f: getattr(machine, f, "") for _, f, _ in COLUMNS}
        fill_color = COLOR_ROW_ALT if row_idx % 2 == 0 else COLOR_ROW_WHITE
        fill = PatternFill("solid", fgColor=fill_color)

        for col_idx, (_, field_name, _) in enumerate(COLUMNS, start=1):
            value = d.get(field_name, "")
            cell  = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font      = Font(name="Arial", size=10)
            cell.fill      = fill
            cell.border    = _border()
            cell.alignment = Alignment(
                vertical="center",
                wrap_text=(field_name == "description"),
            )
            # URLs cliquables
            if field_name in ("url_source", "image_url") and value and value.startswith("http"):
                cell.hyperlink = value
                cell.font = Font(name="Arial", size=10, color="1565C0", underline="single")

        ws.row_dimensions[row_idx].height = 40 if any(
            d.get(f, "") for _, f, _ in COLUMNS if f == "description"
        ) else 22

    # ── Tableau Excel (filtres automatiques) ─────────────────────────────
    if machines:
        last_col = get_column_letter(len(COLUMNS))
        last_row = len(machines) + 1
        tab = Table(
            displayName=f"Tbl{next(_TABLE_COUNTER)}",
            ref=f"A1:{last_col}{last_row}",
        )
        tab.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
        )
        ws.add_table(tab)

    # Figer la ligne d'en-tête
    ws.freeze_panes = "A2"


def export(machines: list[Machine], filepath: str = "agriscan_machines.xlsx"):
    wb = openpyxl.Workbook()

    # ── Onglet "Toutes les machines" ────────────────────────────────────
    ws_all = wb.active
    ws_all.title = "Toutes les machines"
    _write_sheet(ws_all, machines, "Toutes")

    # ── Onglets par catégorie ────────────────────────────────────────────
    categories = sorted(set(m.category for m in machines if m.category))
    for cat in categories:
        subset = [m for m in machines if m.category == cat]
        titre_cat = cat.replace("/", "-").replace("\\", "-").replace("*", "").replace("?", "").replace("[", "").replace("]", "").replace(":", "")[:31]
        ws = wb.create_sheet(title=titre_cat)  # Excel limite à 31 chars
        _write_sheet(ws, subset, cat)



    # ── Onglet résumé ────────────────────────────────────────────────────
    ws_sum = wb.create_sheet(title="Résumé")
    ws_sum["A1"] = "Rapport AgriScan — Collecte machines"
    ws_sum["A1"].font = Font(name="Arial", bold=True, size=14, color=COLOR_HEADER_BG)
    ws_sum["A3"] = f"Date de génération :"
    ws_sum["B3"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    ws_sum["A4"] = "Total machines collectées :"
    ws_sum["B4"] = len(machines)
    ws_sum["B4"].font = Font(bold=True)

    marques = sorted(set(m.brand for m in machines if m.brand))

    ws_sum["A6"] = "Par marque"
    ws_sum["A6"].font = Font(bold=True, color=COLOR_HEADER_BG)
    for i, marque in enumerate(marques, start=7):
        count = sum(1 for m in machines if m.brand == marque)
        ws_sum[f"A{i}"] = marque
        ws_sum[f"B{i}"] = count

    offset = len(marques) + 9
    ws_sum[f"A{offset}"] = "Par catégorie"
    ws_sum[f"A{offset}"].font = Font(bold=True, color=COLOR_HEADER_BG)
    for i, cat in enumerate(categories, start=offset + 1):
        count = sum(1 for m in machines if m.category == cat)
        ws_sum[f"A{i}"] = cat
        ws_sum[f"B{i}"] = count

    ws_sum.column_dimensions["A"].width = 30
    ws_sum.column_dimensions["B"].width = 15

    wb.save(filepath)
    print(f"\n✅ Fichier Excel généré : {filepath}")
    print(f"   {len(machines)} machines | {len(categories)} catégories | {len(marques)} marques")
    return filepath


def export_par_marque(machines: list, dossier: str = "."):
    """Génère un fichier Excel séparé pour chaque marque."""
    import os
    os.makedirs(dossier, exist_ok=True)

    marques = sorted(set(m.brand for m in machines if m.brand))
    fichiers = []
    for marque in marques:
        subset = [m for m in machines if m.brand == marque]
        nom_fichier = marque.replace(" ", "_").replace("/", "-")
        filepath = os.path.join(dossier, f"{nom_fichier}.xlsx")
        export(subset, filepath)
        fichiers.append(filepath)
        print(f"  📄 {filepath} — {len(subset)} machines")

    print(f"\n✅ {len(fichiers)} fichiers générés dans '{dossier}/'")
    return fichiers


if __name__ == "__main__":
    import os, json
    from scrapers.base import Machine
    from dataclasses import fields

    MACHINES_FILE = "machines_cache.json"

    print("\n1. Rescraper + exporter")
    print("2. Exporter depuis le cache existant (sans rescraper)")
    mode = input("Ton choix (1 ou 2) : ").strip()

    if mode == "2" and os.path.exists(MACHINES_FILE):
        with open(MACHINES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        machines = []
        for d in data:
            m = Machine()
            m.brand       = d.get("brand", "")
            m.range       = d.get("range", "")
            m.name        = d.get("name", "")
            m.variant     = d.get("variant", "")
            m.category    = d.get("category", "")
            m.subcategory = d.get("subcategory", "")
            m.description = d.get("description", "")
            m.specs       = d.get("specs", "")
            m.imageUrl    = d.get("imageUrl", "")
            m.videoUrl    = d.get("videoUrl", "")
            m.sourceUrl   = d.get("sourceUrl", "")
            machines.append(m)
        # Normaliser les catégories
        from scrapers.categories import normaliser_categorie
        for m in machines:
            m.category = normaliser_categorie(m.category)
        print(f"✅ {len(machines)} machines chargées depuis le cache")
    else:
        from scraper import run_all
        machines = run_all()

    print("\na. Fichier unique (toutes marques)")
    print("b. Un fichier par marque")
    choix = input("Ton choix (a ou b) : ").strip()

    if choix == "b":
        export_par_marque(machines, dossier="exports")
    else:
        export(machines)