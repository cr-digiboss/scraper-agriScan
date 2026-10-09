import os, json
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
    'SELECT name, "sourceUrl", "createdAt", category, specs FROM "Machine" '
    'WHERE brand = %s AND name = ANY(%s) ORDER BY "createdAt"',
    ("Kverneland", BAD_NAMES),
)
rows = cur.fetchall()
print(f"{len(rows)} lignes trouvées")
for name, url, created, cat, specs in rows:
    print("----")
    print("name:", name)
    print("url:", url)
    print("createdAt:", created)
    print("category:", cat)
    print("specs:", json.dumps(specs)[:300])

# count total bad-looking kverneland rows overall + total kverneland count
cur.execute('SELECT COUNT(*) FROM "Machine" WHERE brand = %s', ("Kverneland",))
print("TOTAL Kverneland:", cur.fetchone()[0])

cur.execute(
    'SELECT MIN("createdAt"), MAX("createdAt") FROM "Machine" WHERE brand = %s',
    ("Kverneland",),
)
print("createdAt range:", cur.fetchone())

conn.close()
