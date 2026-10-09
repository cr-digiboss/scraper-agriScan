import re
from db import get_connection

conn = get_connection()
cur = conn.cursor()

# Heuristique large : nom "attribut-like" = pas de chiffre ET plusieurs mots
# ET contient des mots-cles typiques d'une spec (width, weight, capacity,
# min, max, no., number, diameter, type, kit, hopper, frame, etc.)
cur.execute('SELECT brand, name, "sourceUrl", "createdAt" FROM "Machine" ORDER BY "createdAt" DESC')
rows = cur.fetchall()
print(f"{len(rows)} machines au total")

SPEC_WORDS = re.compile(
    r"\b(width|weight|capacity|min|max|diameter|hopper|frame|number|no\.|"
    r"type|kit|drive|wheel|tine|tyres?|pto|hp|rpm|litres?|litr|volume|"
    r"pressure|speed|length|height|power|requirement|spacing|section|"
    r"marker|ballasting|auger|coulter|spreader|discs?|harrow|clearance|"
    r"ø|kg\b|cm\b|mm\b)",
    re.IGNORECASE,
)

suspects = []
for brand, name, url, created in rows:
    if not name:
        continue
    has_digit = any(ch.isdigit() for ch in name)
    word_count = len(name.split())
    if not has_digit and word_count >= 2 and SPEC_WORDS.search(name):
        suspects.append((brand, name, url, created))

print(f"\n{len(suspects)} suspects trouves (sans chiffre + vocabulaire de spec) :")
for s in suspects[:150]:
    print(" ", s)

conn.close()
