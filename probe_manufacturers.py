"""
Script de sondage temporaire — à supprimer après usage.
Round 2 : deux lignes suspectes trouvées ([Grimme] 'Standard', [Kuhn]
'Capacité'). On liste TOUTES les lignes partageant leur sourceUrl pour
voir la famille complète avant de décider quoi nettoyer.
"""

import logging
import os

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

URLS = [
    "https://products.grimme.com/fr/p/varitron-470-terra-trac-gen3",
    "https://www.kuhn.fr/grande-culture/pulverisateurs/pulverisateurs-automoteurs",
]


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    for url in URLS:
        cur.execute(
            """SELECT brand, name, variant, "createdAt" FROM "Machine"
               WHERE "sourceUrl" = %s ORDER BY name""",
            (url,),
        )
        rows = cur.fetchall()
        log.info(f"\n{url} → {len(rows)} lignes :")
        for brand, name, variant, created_at in rows:
            log.info(f"  [{brand}] {name!r} / {variant!r} — créé={created_at}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
