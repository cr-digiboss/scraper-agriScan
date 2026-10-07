"""
Script de sondage temporaire — à supprimer après usage.
L'utilisateur signale que pour Same, certains modèles en base ne se
retrouvent même pas sur le site. On liste d'abord tout ce qui est en base
pour Same (noms de gamme + variantes), puis on compare avec les fiches
produit réelles du site pour voir où ça diverge.
"""

import logging
import os

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute(
        """SELECT name, variant, "sourceUrl", "createdAt" FROM "Machine"
           WHERE brand = 'Same' ORDER BY name, variant"""
    )
    rows = cur.fetchall()
    log.info(f"Same : {len(rows)} lignes dans Neon\n")
    for name, variant, source_url, created_at in rows:
        log.info(f"  {name!r} / {variant!r} — {source_url} — créé={created_at}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
