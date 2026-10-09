import os, uuid
from playwright.sync_api import sync_playwright
from db import get_connection
import scraper

_NAMESPACE = uuid.UUID("6f6e6f9e-6c7a-4c8e-9c9a-3a6b6f6f6c61")
URL = "https://ien.kverneland.com/bale-choppers/mixer-feeders/siloking-selfline-4.0-system-1000"

conn = get_connection()
cur = conn.cursor()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    model_specs = scraper._kverneland_parse_tables(page.query_selector_all("table"))
    page_title = scraper._clean_kverneland_title(page.title())
    valid_names = {name or page_title for name, _ in model_specs}
    browser.close()

print("Noms valides attendus:", sorted(valid_names))

cur.execute(
    'SELECT id, name, brand, variant FROM "Machine" WHERE brand = %s AND "sourceUrl" = %s',
    ("Kverneland", URL),
)
rows = cur.fetchall()
bad_rows = [(rid, name, brand, variant) for rid, name, brand, variant in rows if name not in valid_names]
print(f"{len(bad_rows)} lignes a supprimer:", [n for _, n, _, _ in bad_rows])

if bad_rows:
    ids = [r[0] for r in bad_rows]
    bnv = [(r[2], r[1], r[3]) for r in bad_rows]
    cur.execute('DELETE FROM "Machine" WHERE id = ANY(%s)', (ids,))
    conn.commit()
    print(f"Neon : {cur.rowcount} lignes supprimees")
    point_ids = [str(uuid.uuid5(_NAMESPACE, f"{b}|{n}|{v}")) for b, n, v in bnv]
    if os.getenv("QDRANT_URL") and os.getenv("QDRANT_API_KEY"):
        from qdrant_client import QdrantClient
        client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
        collection = os.environ.get("QDRANT_COLLECTION", "agriscan")
        client.delete(collection_name=collection, points_selector=point_ids)
        print(f"Qdrant : suppression de {len(point_ids)} points effectuee")

conn.close()
