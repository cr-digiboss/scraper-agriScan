"""
Script ponctuel — à supprimer après usage.
Supprime les 2 entrées Kuhn "MULTI-LONGER GII EP 6157 TP" / "...PWR"
périmées (ancien nom affiché par le site avant un changement de
structure de la page produit ; les entrées courantes "6157 TP" /
"6157 TP PWR" correspondent au nom actuellement affiché, confirmé par
sondage de la page live).
"""

import logging
import uuid

import db
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue
import os

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("cleanup")

STALE_NAMES = ["MULTI-LONGER GII EP 6157 TP", "MULTI-LONGER GII EP 6157 TP PWR"]
_NAMESPACE = uuid.UUID("6f6e6f9e-6c7a-4c8e-9c9a-3a6b6f6f6c61")


def main():
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """DELETE FROM "Machine" WHERE brand = 'Kuhn' AND name = ANY(%s)""",
        (STALE_NAMES,),
    )
    log.info(f"Neon : {cur.rowcount} lignes Kuhn périmées supprimées")
    conn.commit()
    cur.close()
    conn.close()

    client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
    collection = os.environ["QDRANT_COLLECTION"]
    point_ids = [str(uuid.uuid5(_NAMESPACE, f"Kuhn|{name}|")) for name in STALE_NAMES]
    log.info(f"Qdrant : suppression des points {point_ids}")
    client.delete(collection_name=collection, points_selector=point_ids)
    log.info("Qdrant : suppression effectuée")


if __name__ == "__main__":
    main()
