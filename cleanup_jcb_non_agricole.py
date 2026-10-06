"""
Script ponctuel — à supprimer après usage.
Supprime les entrées JCB non-agricoles déjà présentes dans Neon (chargeuses-
pelleteuses, chargeuses compactes sur chenilles/pneus, groupes électrogènes,
Hydradig) — catégories retirées de JCB_CATEGORIES car JCB vend surtout de
l'équipement de chantier. Seules les catégories Tracteurs et Télescopiques
(rotatifs/articulés) restent dans le scraper.
"""

import logging
import os
import uuid

import db
from qdrant_client import QdrantClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("cleanup")

_NAMESPACE = uuid.UUID("6f6e6f9e-6c7a-4c8e-9c9a-3a6b6f6f6c61")


def main():
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute(
        """SELECT name, variant FROM "Machine" WHERE brand = 'JCB' AND category != 'Tracteurs'"""
    )
    rows = cur.fetchall()
    log.info(f"{len(rows)} lignes JCB non-agricoles trouvées :")
    for name, variant in rows:
        log.info(f"  {name!r} / {variant!r}")

    cur.execute(
        """DELETE FROM "Machine" WHERE brand = 'JCB' AND category != 'Tracteurs'"""
    )
    log.info(f"Neon : {cur.rowcount} lignes JCB non-agricoles supprimées")
    conn.commit()
    cur.close()
    conn.close()

    client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
    collection = os.environ["QDRANT_COLLECTION"]
    point_ids = [str(uuid.uuid5(_NAMESPACE, f"JCB|{name}|{variant}")) for name, variant in rows]
    log.info(f"Qdrant : suppression de {len(point_ids)} points")
    client.delete(collection_name=collection, points_selector=point_ids)
    log.info("Qdrant : suppression effectuée")


if __name__ == "__main__":
    main()
