"""
Script de sondage temporaire — à supprimer après usage.
Vérifie qu'il ne reste plus de fiches TractorData avec variant = année
après la migration.
"""

import logging
from collections import Counter

import db

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

YEAR_PATTERN = r"^(19[0-9]{2}|20[0-2][0-9])$"


def main():
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT brand, name, variant FROM \"Machine\" WHERE variant ~ '{YEAR_PATTERN}'"
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    log.info(f"Lignes restantes avec variant = année : {len(rows)}")
    if rows:
        par_marque = Counter(brand for brand, _, _ in rows)
        for brand, n in par_marque.most_common():
            log.info(f"  {brand} → {n}")


if __name__ == "__main__":
    main()
