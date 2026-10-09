import json
from db import get_connection

BAD_NAMES = [
    "Mechanical drive of fertiliser spreader",
    "Disc section with standard discs",
    "Tyres 7.00-12AS",
    "53cm Crosskill weight (kg)",
    "Tyres 26x12.00STG",
    "Hydraulically operated track marker",
    "Hydraulically frame ballasting kit",
    "Mounted fertiliser spreader",
    "Maximum no. of rows with mounted fertiliser spreader",
    "Electro-hydraulic drive of fertiliser spreader",
    "No. of coulters 12.5cm distance (standard)",
    "No. of coulters 15cm distance (option)",
    "CX-II coulter double entry (f-drill / Plus)",
    "Fertiliser hopper capacity in litres",
    "Filling auger *",
]

conn = get_connection()
cur = conn.cursor()
cur.execute(
    'SELECT id, name, "sourceUrl", "createdAt" FROM "Machine" '
    'WHERE brand = %s AND name = ANY(%s) ORDER BY "createdAt"',
    ("Kverneland", BAD_NAMES),
)
rows = cur.fetchall()
print(f"{len(rows)} lignes trouvées parmi les 15 noms connus")
for r in rows:
    print(r)

# Recherche plus large : toute ligne Kverneland qui ressemble a un attribut
# (nom long en anglais, probablement toujours spec-as-machine), creee recemment
cur.execute(
    'SELECT id, name, "sourceUrl", "createdAt" FROM "Machine" '
    'WHERE brand = %s ORDER BY "createdAt" DESC LIMIT 30',
    ("Kverneland",),
)
print("\n--- 30 dernieres lignes Kverneland (les plus recentes) ---")
for r in cur.fetchall():
    print(r)

conn.close()
