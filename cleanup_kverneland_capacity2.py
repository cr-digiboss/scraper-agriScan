"""
Script ponctuel — à supprimer après usage.
Supprime [Kverneland] 'Capacity (m³)' — même classe de bug (libellé
d'attribut + unité entre parenthèses pris pour un nom de machine),
signalée par l'utilisateur.
"""

import logging
import os
import uuid

import db
from qdrant_client import QdrantClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("cleanup")

_NAMESPACE = uuid.UUID("6f6e6f9e-6c7a-4c8e-9c9a-3a6b6f6f6c61")

BRAND, NAME, VARIANT = "Kverneland", "Capacity (m³)", ""


def main():
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute(
        """DELETE FROM "Machine" WHERE brand = %s AND name = %s AND variant = %s""",
        (BRAND, NAME, VARIANT),
    )
    log.info(f"Neon : {cur.rowcount} ligne(s) supprimée(s)")
    conn.commit()
    cur.close()
    conn.close()

    client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
    collection = os.environ["QDRANT_COLLECTION"]
    point_id = str(uuid.uuid5(_NAMESPACE, f"{BRAND}|{NAME}|{VARIANT}"))
    log.info(f"Qdrant : suppression de {point_id}")
    client.delete(collection_name=collection, points_selector=[point_id])
    log.info("Qdrant : suppression effectuée")


if __name__ == "__main__":
    main()
