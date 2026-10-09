import time
from playwright.sync_api import sync_playwright
from db import get_connection
import scraper

BAD_TS = "2026-10-07 13:08:04.509000"

conn = get_connection()
cur = conn.cursor()
cur.execute(
    'SELECT DISTINCT "sourceUrl" FROM "Machine" WHERE brand = %s AND "createdAt" = %s ORDER BY 1',
    ("Kverneland", BAD_TS),
)
urls = [r[0] for r in cur.fetchall()]
print(f"{len(urls)} URLs à revérifier")

to_delete_ids = []
total_checked = 0

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    for i, url in enumerate(urls, 1):
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            model_specs = scraper._kverneland_parse_tables(page.query_selector_all("table"))
            page_title = scraper._clean_kverneland_title(page.title())
            valid_names = {name or page_title for name, _ in model_specs}
        except Exception as e:
            print(f"[{i}/{len(urls)}] ERREUR {url} -> {e} (on ne touche à rien pour cette URL)")
            continue

        cur.execute(
            'SELECT id, name FROM "Machine" WHERE brand = %s AND "sourceUrl" = %s',
            ("Kverneland", url),
        )
        rows = cur.fetchall()
        total_checked += len(rows)
        bad_rows = [(rid, name) for rid, name in rows if name not in valid_names]
        if bad_rows:
            print(f"[{i}/{len(urls)}] {url}")
            print(f"    valides attendus: {sorted(valid_names)}")
            print(f"    {len(bad_rows)} lignes à supprimer: {[n for _, n in bad_rows]}")
        to_delete_ids.extend(rid for rid, _ in bad_rows)
    browser.close()

print(f"\n{total_checked} lignes vérifiées au total sur {len(urls)} URLs")
print(f"{len(to_delete_ids)} lignes à supprimer")

if to_delete_ids:
    cur.execute(
        'SELECT brand, name, variant FROM "Machine" WHERE id = ANY(%s)',
        (to_delete_ids,),
    )
    to_delete_bnv = cur.fetchall()

    cur.execute('DELETE FROM "Machine" WHERE id = ANY(%s)', (to_delete_ids,))
    conn.commit()
    print(f"Neon : {cur.rowcount} lignes supprimées")

    import os, uuid
    from qdrant_client import QdrantClient
    _NAMESPACE = uuid.UUID("6f6e6f9e-6c7a-4c8e-9c9a-3a6b6f6f6c61")
    point_ids = [str(uuid.uuid5(_NAMESPACE, f"{b}|{n}|{v}")) for b, n, v in to_delete_bnv]
    if os.getenv("QDRANT_URL") and os.getenv("QDRANT_API_KEY"):
        client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
        collection = os.environ.get("QDRANT_COLLECTION", "agriscan")
        client.delete(collection_name=collection, points_selector=point_ids)
        print(f"Qdrant : suppression de {len(point_ids)} points effectuée")
else:
    print("Rien à supprimer")

conn.close()
