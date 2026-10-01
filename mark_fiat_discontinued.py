"""
Script ponctuel — à supprimer après usage.
Marque toutes les machines de la marque Fiat comme "discontinued" dans Neon.
"""

import logging

import db

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("mark_fiat")


def main():
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM "Machine" WHERE brand = %s', ("Fiat",))
            count = cur.fetchone()[0]
            log.info(f"Neon : {count} machines Fiat trouvées")
            cur.execute(
                'UPDATE "Machine" SET statut = %s WHERE brand = %s',
                ("discontinued", "Fiat"),
            )
        conn.commit()
        log.info(f"Neon : {count} machines Fiat marquées 'discontinued'")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
