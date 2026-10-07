"""
Script ponctuel — à supprimer après usage.
Supprime les ~555 lignes Kverneland bidon créées pendant le run #75 (avant
le correctif du régression "non_empty_header") : chaque ligne d'attribut
d'une fiche à un seul modèle (table avec une colonne vide en trop) avait
été prise pour un modèle distinct. Toutes partagent le même horodatage
exact ('2026-10-07 10:07:48.534000', commit en lot après le scrape complet
de Kverneland). On exclut explicitement les 6 vraies machines mixer-feeders
(Compact/Premium) déjà validées, au cas où elles partageraient ce même lot.
"""

import logging
import os
import uuid

import db
from qdrant_client import QdrantClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("cleanup")

_NAMESPACE = uuid.UUID("6f6e6f9e-6c7a-4c8e-9c9a-3a6b6f6f6c61")

BAD_TS = "2026-10-07 10:07:48.534000"

GOOD_NAMES = {
    "Compact 1612-12", "Compact 1612-13", "Compact 1612-16",
    "Premium 2215-15", "Premium 2215-19", "Premium 2215-22",
}


def main():
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute(
        """SELECT name, variant FROM "Machine"
           WHERE brand = 'Kverneland' AND "createdAt" = %s""",
        (BAD_TS,),
    )
    all_rows = cur.fetchall()
    log.info(f"{len(all_rows)} lignes trouvées à cet horodatage")

    protected = [(n, v) for n, v in all_rows if n in GOOD_NAMES]
    log.info(f"{len(protected)} lignes protégées (vraies machines mixer-feeders) : {protected}")

    to_delete = [(n, v) for n, v in all_rows if n not in GOOD_NAMES]
    log.info(f"{len(to_delete)} lignes à supprimer")

    deleted = 0
    for name, variant in to_delete:
        cur.execute(
            """DELETE FROM "Machine" WHERE brand = 'Kverneland' AND name = %s AND variant = %s
               AND "createdAt" = %s""",
            (name, variant, BAD_TS),
        )
        deleted += cur.rowcount
    log.info(f"Neon : {deleted} lignes supprimées")
    conn.commit()
    cur.close()
    conn.close()

    client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
    collection = os.environ["QDRANT_COLLECTION"]
    point_ids = [str(uuid.uuid5(_NAMESPACE, f"Kverneland|{name}|{variant}")) for name, variant in to_delete]
    log.info(f"Qdrant : suppression de {len(point_ids)} points")
    client.delete(collection_name=collection, points_selector=point_ids)
    log.info("Qdrant : suppression effectuée")


if __name__ == "__main__":
    main()
