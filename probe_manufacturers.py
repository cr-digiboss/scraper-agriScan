"""
Script de sondage temporaire — à supprimer après usage.
Le run de production (#67, après le fix multi-tables) a rapporté
"aucune nouvelle machine" pour Pöttinger ET pour TOUTES les autres marques
(0 machines enregistrées au total sur l'ensemble du run). Avant de creuser
plus loin côté scraper, on vérifie l'état réel de Neon pour Pöttinger :
combien de lignes, quels noms, est-ce que les variantes "PRO"/"PLUS" de la
série Alpha Motion (qui n'auraient normalement jamais pu être capturées par
l'ancien code tables[0]-only) sont déjà présentes.
"""

import logging
import os

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM "Machine" WHERE brand = %s', ("Pöttinger",))
    total = cur.fetchone()[0]
    log.info(f"Pöttinger : {total} lignes dans Neon")

    cur.execute(
        'SELECT name, variant, "createdAt" FROM "Machine" WHERE brand = %s ORDER BY name',
        ("Pöttinger",),
    )
    rows = cur.fetchall()
    for name, variant, created_at in rows:
        log.info(f"  {name!r} | variant={variant!r} | créé={created_at}")

    log.info("\n--- Recherche spécifique des variantes Alpha Motion PRO ---")
    cur.execute(
        """SELECT name, variant FROM "Machine" WHERE brand = %s AND name ILIKE %s""",
        ("Pöttinger", "%ALPHA MOTION%"),
    )
    alpha = cur.fetchall()
    log.info(f"{len(alpha)} lignes 'Alpha Motion' trouvées :")
    for name, variant in alpha:
        log.info(f"  {name!r} | variant={variant!r}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
