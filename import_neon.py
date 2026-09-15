"""
AgriScan — Import machines vers Neon (PostgreSQL)
Lit l'Excel et insère dans la table Machine via psycopg2.

Installation :
    pip install psycopg2-binary openpyxl python-dotenv

Usage :
    python import_neon.py
"""

import psycopg2
import openpyxl
import json
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("agriscan")

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
DATABASE_URL = os.getenv("DATABASE_URL")
EXCEL_FILE = "machines_extracted.xlsx"

if not DATABASE_URL:
    raise ValueError("DATABASE_URL introuvable dans le .env")

# ─────────────────────────────────────────────────────────────────────────────
# Lecture Excel
# ─────────────────────────────────────────────────────────────────────────────

def lire_excel(filepath: str) -> list[dict]:
    wb = openpyxl.load_workbook(filepath)
    # Trouver le bon onglet
    print(f"Onglets disponibles : {wb.sheetnames}")
    nom_onglet = wb.sheetnames[0]  # Prendre le premier onglet
    for name in wb.sheetnames:
        if "toutes" in name.lower() or "all" in name.lower():
            nom_onglet = name
            break
    print(f"Onglet utilisé : {nom_onglet}")
    ws = wb[nom_onglet]

    headers = [cell.value for cell in ws[1]]
    print(f"En-têtes trouvés : {headers}")
    print(f"Nombre de lignes : {ws.max_row}")
    machines = []

    # Debug premières lignes
    for i, row in enumerate(ws.iter_rows(min_row=2, max_row=4, values_only=True), 2):
        print(f"Ligne {i} : {row}")

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        d = dict(zip(headers, row))

        # Nettoyer les valeurs None
        for k in d:
            if d[k] is None:
                d[k] = ""

        # specs doit être un dict valide ou None
        specs = d.get("specs", "")
        if specs:
            try:
                d["specs"] = json.loads(specs)
            except:
                d["specs"] = {}
        else:
            d["specs"] = {}

        # Ignorer les lignes sans brand ou name
        if not d.get("brand") or not d.get("name"):
            continue

        machines.append(d)

    log.info(f"📋 {len(machines)} machines lues depuis l'Excel")
    return machines

# ─────────────────────────────────────────────────────────────────────────────
# Import Neon
# ─────────────────────────────────────────────────────────────────────────────

INSERT_SQL = """
    INSERT INTO "Machine" (
        id, brand, range, name, variant,
        category, subcategory, description,
        specs, "imageUrl", "videoUrl", "sourceUrl",
        "createdAt"
    ) VALUES (
        gen_random_uuid()::text,
        %(brand)s, %(range)s, %(name)s, %(variant)s,
        %(category)s, %(subcategory)s, %(description)s,
        %(specs)s::jsonb, %(imageUrl)s, %(videoUrl)s, %(sourceUrl)s,
        NOW()
    )
    ON CONFLICT (brand, name, variant) DO UPDATE SET
        range       = EXCLUDED.range,
        category    = EXCLUDED.category,
        subcategory = EXCLUDED.subcategory,
        description = EXCLUDED.description,
        specs       = EXCLUDED.specs,
        "imageUrl"  = EXCLUDED."imageUrl",
        "sourceUrl" = EXCLUDED."sourceUrl"
"""

def importer(machines: list[dict]):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    inseres = 0
    mis_a_jour = 0
    erreurs = 0

    for i, m in enumerate(machines, 1):
        try:
            # Préparer les données
            data = {
                "brand":       str(m.get("brand", ""))[:255],
                "range":       str(m.get("range", ""))[:255] or None,
                "name":        str(m.get("name", ""))[:255],
                "variant":     str(m.get("variant", "")) or "",
                "category":    str(m.get("category", ""))[:255],
                "subcategory": str(m.get("subcategory", ""))[:255] or None,
                "description": str(m.get("description", "")) or None,
                "specs":       json.dumps(m.get("specs") or {}),
                "imageUrl":    str(m.get("imageUrl", "")) or None,
                "videoUrl":    str(m.get("videoUrl", "")) or None,
                "sourceUrl":   str(m.get("sourceUrl", "")) or None,
            }

            cursor.execute(INSERT_SQL, data)

            if cursor.rowcount == 1:
                inseres += 1
            else:
                mis_a_jour += 1

            # Commit par batch de 100
            if i % 100 == 0:
                conn.commit()
                log.info(f"  {i}/{len(machines)} — {inseres} insérées, {mis_a_jour} mises à jour, {erreurs} erreurs")

        except Exception as e:
            conn.rollback()
            erreurs += 1
            log.warning(f"  ❌ Erreur {m.get('brand')} {m.get('name')} : {e}")

    conn.commit()
    cursor.close()
    conn.close()

    log.info(f"\n✅ Import terminé !")
    log.info(f"   Insérées    : {inseres}")
    log.info(f"   Mises à jour: {mis_a_jour}")
    log.info(f"   Erreurs     : {erreurs}")


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not os.path.exists(EXCEL_FILE):
        log.error(f"❌ Fichier Excel introuvable : {EXCEL_FILE}")
        exit(1)

    machines = lire_excel(EXCEL_FILE)

    print(f"\n{len(machines)} machines à importer dans Neon")
    print("ON CONFLICT → mise à jour automatique si la machine existe déjà")
    confirm = input("\nConfirmer l'import ? (oui/non) : ").strip().lower()

    if confirm == "oui":
        importer(machines)
    else:
        print("Import annulé.")