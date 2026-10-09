import os, uuid, json
from playwright.sync_api import sync_playwright
from db import get_connection
import scraper

_NAMESPACE = uuid.UUID("6f6e6f9e-6c7a-4c8e-9c9a-3a6b6f6f6c61")

KNOWN_BAD_KVERNELAND = [
    "Tine spacing Min - Max",
    "2300 S Reversible Plough",
    "Working width Min - Max",
    "PTO, swivel hitch drawbar (rpm)",
    "Hopper capacity",
    "Headstock",
    "Weight w/o stairs & guards",
    "2501 S Variomat Reversible Plough",
    "Ring profile",
    "Hopper",
    "Ring diameter mm",
    "Weight excl. wheel and",
    "No. Of tines",
    "6300 S Variomat Reversible Plough",
    "3300 S Reversible Plough",
]
KNOWN_BAD_KUHN = ["Capacité", "5000 litres"]

conn = get_connection()
cur = conn.cursor()

# 1) suppression directe des noms deja identifies (captures d'ecran)
cur.execute(
    'SELECT id, brand, name, variant, "sourceUrl" FROM "Machine" '
    'WHERE (brand = %s AND name = ANY(%s)) OR (brand = %s AND name = ANY(%s))',
    ("Kverneland", KNOWN_BAD_KVERNELAND, "Kuhn", KNOWN_BAD_KUHN),
)
known_bad_rows = cur.fetchall()
print(f"{len(known_bad_rows)} lignes bidon deja identifiees trouvees")
for r in known_bad_rows:
    print(" ", r)

# 2) re-verification complete de toutes les URLs Kverneland concernees par
# ces lignes (comme pour le nettoyage precedent), au cas ou d'autres lignes
# bidon du meme type trainent sur les memes pages
urls = sorted({r[4] for r in known_bad_rows if r[1] == "Kverneland"})
print(f"\n{len(urls)} URLs Kverneland a revalider : {urls}")

to_delete_ids = [r[0] for r in known_bad_rows]
to_delete_bnv = [(r[1], r[2], r[3]) for r in known_bad_rows]

if urls:
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
                print(f"[{i}/{len(urls)}] ERREUR {url} -> {e}")
                continue

            cur.execute(
                'SELECT id, name, brand, variant FROM "Machine" WHERE brand = %s AND "sourceUrl" = %s',
                ("Kverneland", url),
            )
            rows = cur.fetchall()
            bad_rows = [(rid, name, brand, variant) for rid, name, brand, variant in rows if name not in valid_names]
            print(f"[{i}/{len(urls)}] {url}")
            print(f"    valides attendus: {sorted(valid_names)}")
            if bad_rows:
                print(f"    {len(bad_rows)} lignes supplementaires a supprimer: {[n for _,n,_,_ in bad_rows]}")
            for rid, name, brand, variant in bad_rows:
                if rid not in to_delete_ids:
                    to_delete_ids.append(rid)
                    to_delete_bnv.append((brand, name, variant))
        browser.close()

print(f"\n{len(to_delete_ids)} lignes au total a supprimer")

if to_delete_ids:
    cur.execute('DELETE FROM "Machine" WHERE id = ANY(%s)', (to_delete_ids,))
    conn.commit()
    print(f"Neon : {cur.rowcount} lignes supprimees")

    point_ids = [str(uuid.uuid5(_NAMESPACE, f"{b}|{n}|{v}")) for b, n, v in to_delete_bnv]
    if os.getenv("QDRANT_URL") and os.getenv("QDRANT_API_KEY"):
        from qdrant_client import QdrantClient
        client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
        collection = os.environ.get("QDRANT_COLLECTION", "agriscan")
        client.delete(collection_name=collection, points_selector=point_ids)
        print(f"Qdrant : suppression de {len(point_ids)} points effectuee")
else:
    print("Rien a supprimer")

conn.close()
