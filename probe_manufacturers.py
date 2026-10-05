"""
Script de sondage temporaire — à supprimer après usage.
Bug Kuhn : interroge directement Neon pour récupérer les sourceUrl exacts
des 4 entrées en double signalées par l'utilisateur (6157 TP / 6157 TP
PWR / MULTI-LONGER GII EP 6157 TP / MULTI-LONGER GII EP 6157 TP PWR).
"""

import json
import logging

import db

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name, variant, category, "sourceUrl", specs
        FROM "Machine"
        WHERE brand = 'Kuhn' AND name ILIKE %s
        ORDER BY name
        """,
        ("%6157%",),
    )
    rows = cur.fetchall()
    log.info(f"{len(rows)} lignes trouvées pour 'Kuhn' + '6157' :")
    for name, variant, category, source_url, specs in rows:
        log.info(f"\nname={name!r} variant={variant!r} category={category!r}")
        log.info(f"  sourceUrl={source_url}")
        log.info(f"  specs={specs}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
