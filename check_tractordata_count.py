"""
Script ponctuel (lecture seule) — à supprimer après usage.
Compte les machines par marque TractorData pour évaluer l'impact d'un
retrait de cette source, avant de décider s'il faut aussi purger les
données déjà en base.
"""

import logging

import db

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("check")

MARQUES = [
    "John Deere", "Massey Ferguson", "New Holland", "Case IH", "Kubota",
    "Ford", "Fendt", "Claas", "Deutz-Fahr", "Allis-Chalmers",
    "International", "Fiat", "Mahindra",
]


def main():
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM "Machine"')
            total = cur.fetchone()[0]
            log.info(f"Total machines en base : {total}")

            cur.execute(
                'SELECT COUNT(*) FROM "Machine" WHERE brand = ANY(%s)',
                (MARQUES,),
            )
            tractordata_total = cur.fetchone()[0]
            log.info(f"Total TractorData (13 marques) : {tractordata_total}")

            for marque in MARQUES:
                cur.execute('SELECT COUNT(*) FROM "Machine" WHERE brand = %s', (marque,))
                count = cur.fetchone()[0]
                log.info(f"  {marque} : {count}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
