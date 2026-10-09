from db import get_connection

conn = get_connection()
cur = conn.cursor()
cur.execute(
    'SELECT id, name, "sourceUrl", "createdAt", specs FROM "Machine" '
    'WHERE brand = %s AND name IN (%s, %s) ORDER BY "createdAt"',
    ("Kuhn", "Capacité", "5000 litres"),
)
rows = cur.fetchall()
print(f"{len(rows)} lignes trouvees")
for r in rows:
    print(r)

# plus large: toute ligne Kuhn creee recemment (pour voir si c'est un lot recent)
cur.execute(
    'SELECT name, "sourceUrl", "createdAt" FROM "Machine" WHERE brand = %s '
    'ORDER BY "createdAt" DESC LIMIT 15',
    ("Kuhn",),
)
print("\n--- 15 dernieres lignes Kuhn ---")
for r in cur.fetchall():
    print(r)

conn.close()
