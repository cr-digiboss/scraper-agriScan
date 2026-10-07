"""
Script de sondage temporaire — à supprimer après usage.
Avant de nettoyer, on vérifie si TOUTES les lignes Kverneland créées à
l'horodatage exact '2026-10-07 10:07:48.534000' sont bien des lignes
bidon (issues de la régression), ou si certaines sont de vraies machines
légitimement ajoutées pendant le run #75 (même horodatage car commit en
lot ?). On liste le détail complet, groupé par sourceUrl, avec le nombre
de clés dans specs (une vraie machine a généralement plusieurs clés de
specs ; une ligne bidon issue de la régression n'a souvent qu'1 clé).
"""

import json
import logging
import os

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

BAD_TS = "2026-10-07 10:07:48.534000"


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute(
        """SELECT name, variant, specs, "sourceUrl" FROM "Machine"
           WHERE brand = 'Kverneland' AND "createdAt" = %s
           ORDER BY "sourceUrl", name""",
        (BAD_TS,),
    )
    rows = cur.fetchall()
    log.info(f"{len(rows)} lignes Kverneland créées à {BAD_TS}\n")

    by_url = {}
    for name, variant, specs_json, source_url in rows:
        by_url.setdefault(source_url, []).append((name, variant, specs_json))

    for url, items in by_url.items():
        log.info(f"\n{url} → {len(items)} ligne(s) :")
        for name, variant, specs_json in items:
            try:
                n_keys = len(json.loads(specs_json)) if specs_json else 0
            except Exception:
                n_keys = -1
            log.info(f"  {name!r} / {variant!r} — {n_keys} clés de specs")

    log.info(f"\n=== {len(by_url)} sourceUrl distincts, {len(rows)} lignes au total ===")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
