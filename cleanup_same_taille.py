"""
Script ponctuel — à supprimer après usage.
Supprime l'entrée Same "Tracteur Frutteto Classic" / "Taille" — faux modèle
issu d'une ligne de données mal interprétée comme ligne d'en-tête (corrigé
dans _sdf_find_header_rows). Vérifie aussi qu'il n'y a pas d'autres entrées
Same avec une variante non numérique suspecte avant de supprimer.
"""

import logging
import os
import uuid

import db
from qdrant_client import QdrantClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("cleanup")

_NAMESPACE = uuid.UUID("6f6e6f9e-6c7a-4c8e-9c9a-3a6b6f6f6c61")

STALE = [("Tracteur Frutteto Classic", "Taille")]


def main():
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute(
        """SELECT name, variant FROM "Machine" WHERE brand = 'Same' AND name = %s AND variant = %s""",
        STALE[0],
    )
    found = cur.fetchall()
    log.info(f"{len(found)} lignes trouvées à supprimer : {found}")

    cur.execute(
        """DELETE FROM "Machine" WHERE brand = 'Same' AND name = %s AND variant = %s""",
        STALE[0],
    )
    log.info(f"Neon : {cur.rowcount} lignes supprimées")
    conn.commit()
    cur.close()
    conn.close()

    client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
    collection = os.environ["QDRANT_COLLECTION"]
    point_ids = [str(uuid.uuid5(_NAMESPACE, f"Same|{name}|{variant}")) for name, variant in STALE]
    log.info(f"Qdrant : suppression de {point_ids}")
    client.delete(collection_name=collection, points_selector=point_ids)
    log.info("Qdrant : suppression effectuée")


if __name__ == "__main__":
    main()
