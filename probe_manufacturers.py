"""
Script de sondage temporaire — à supprimer après usage.
Rapport en lecture seule (aucune écriture) : compte les fiches TractorData
déjà en base avec un variant = année, et détecte les groupes brand+name qui
ont plusieurs entrées (qui entreraient en conflit une fois le variant vidé).
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

    log.info(f"Lignes avec variant = année : {len(rows)}")

    par_marque = Counter(brand for brand, _, _ in rows)
    log.info("\nRépartition par marque :")
    for brand, n in par_marque.most_common():
        log.info(f"  {brand} → {n}")

    groupes = {}
    for brand, name, variant in rows:
        groupes.setdefault((brand, name), []).append(variant)

    doublons = {k: v for k, v in groupes.items() if len(v) > 1}
    log.info(f"\nGroupes brand+name distincts : {len(groupes)}")
    log.info(f"Groupes avec plusieurs années pour le même nom (conflit potentiel) : {len(doublons)}")
    for (brand, name), variants in list(doublons.items())[:20]:
        log.info(f"  {brand} — {name} → années {sorted(variants)}")


if __name__ == "__main__":
    main()
