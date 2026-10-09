import os
import uuid
from db import get_connection
from qdrant_client import QdrantClient

_NAMESPACE = uuid.UUID("6f6e6f9e-6c7a-4c8e-9c9a-3a6b6f6f6c61")

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
    'SELECT id, brand, name, variant, "sourceUrl" FROM "Machine" '
    'WHERE brand = %s AND name = ANY(%s)',
    ("Kverneland", BAD_NAMES),
)
rows = cur.fetchall()
print(f"{len(rows)} lignes trouvées à supprimer")
for r in rows:
    print(r)

ids = [r[0] for r in rows]
point_ids = [str(uuid.uuid5(_NAMESPACE, f"{b}|{n}|{v}")) for _id, b, n, v, _url in rows]

if ids:
    cur.execute('DELETE FROM "Machine" WHERE id = ANY(%s)', (ids,))
    conn.commit()
    print(f"Neon : {cur.rowcount} lignes supprimées")

    if os.getenv("QDRANT_URL") and os.getenv("QDRANT_API_KEY"):
        client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
        collection = os.environ.get("QDRANT_COLLECTION", "agriscan")
        client.delete(collection_name=collection, points_selector=point_ids)
        print(f"Qdrant : suppression de {len(point_ids)} points effectuée")
    else:
        print("Qdrant non configuré, suppression ignorée")
else:
    print("Rien à supprimer")

conn.close()
