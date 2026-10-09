from db import get_connection

BAD_TS = "2026-10-07 13:08:04.509000"

conn = get_connection()
cur = conn.cursor()
cur.execute(
    'SELECT COUNT(*) FROM "Machine" WHERE brand = %s AND "createdAt" = %s',
    ("Kverneland", BAD_TS),
)
print("Total lignes a ce timestamp:", cur.fetchone()[0])

cur.execute(
    'SELECT DISTINCT "sourceUrl" FROM "Machine" WHERE brand = %s AND "createdAt" = %s ORDER BY 1',
    ("Kverneland", BAD_TS),
)
urls = [r[0] for r in cur.fetchall()]
print(f"{len(urls)} URLs distinctes concernees:")
for u in urls:
    print(u)

conn.close()
