"""
Script de sondage temporaire — à supprimer après usage.
L'utilisateur signale que JCB contient des produits qui ne sont pas des
machines agricoles. JCB_CATEGORIES couvre tout le catalogue JCB (construction
+ agriculture). On interroge Neon pour voir combien de lignes existent par
catégorie normalisée, afin de quantifier l'ampleur avant de retirer les
catégories non-agricoles de la config.
"""

import logging
import os

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM "Machine" WHERE brand = %s', ("JCB",))
    total = cur.fetchone()[0]
    log.info(f"JCB : {total} lignes au total dans Neon")

    cur.execute(
        """SELECT category, COUNT(*) FROM "Machine" WHERE brand = %s
           GROUP BY category ORDER BY COUNT(*) DESC""",
        ("JCB",),
    )
    log.info("\nRépartition par catégorie normalisée :")
    for category, count in cur.fetchall():
        log.info(f"  {category!r} : {count}")

    cur.execute(
        """SELECT category, name, variant, "sourceUrl" FROM "Machine"
           WHERE brand = %s ORDER BY category, name""",
        ("JCB",),
    )
    log.info("\nDétail complet :")
    for category, name, variant, source_url in cur.fetchall():
        log.info(f"  [{category}] {name!r} / {variant!r} — {source_url}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
