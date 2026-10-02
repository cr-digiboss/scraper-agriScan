"""
Script ponctuel (lecture seule) — à supprimer après usage.
Liste les noms de machines New Holland déjà en base, pour voir si les
variantes (T7.360 XD, T7.390 XD...) sont capturées séparément ou si seul
le nom de famille (T7 XD) existe.
"""

import logging

import db

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("check")


def main():
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT name, variant FROM "Machine" WHERE brand = %s ORDER BY name',
                ("New Holland",),
            )
            rows = cur.fetchall()
            log.info(f"New Holland : {len(rows)} machines en base")
            for name, variant in rows:
                log.info(f"  - {name!r} | variant={variant!r}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
