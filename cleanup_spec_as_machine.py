"""
Script ponctuel — à supprimer après usage.
Supprime 3 lignes où name/variant est en fait une valeur de spec/libellé
d'attribut plutôt qu'un vrai nom de machine : [Grimme] 'Standard' (nom de
modèle non extrait correctement) et [Kuhn] '5000 litres'/'Capacité'
(2 entrées garbage sur la page pulverisateurs-automoteurs, déjà repérées
lors d'une investigation précédente).
"""

import logging
import os
import uuid

import db
from qdrant_client import QdrantClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("cleanup")

_NAMESPACE = uuid.UUID("6f6e6f9e-6c7a-4c8e-9c9a-3a6b6f6f6c61")

STALE = [
    ("Grimme", "Standard", ""),
    ("Kuhn", "5000 litres", ""),
    ("Kuhn", "Capacité", ""),
]


def main():
    conn = db.get_connection()
    cur = conn.cursor()

    total = 0
    for brand, name, variant in STALE:
        cur.execute(
            """DELETE FROM "Machine" WHERE brand = %s AND name = %s AND variant = %s""",
            (brand, name, variant),
        )
        log.info(f"Neon : {cur.rowcount} ligne(s) supprimée(s) pour [{brand}] {name!r}/{variant!r}")
        total += cur.rowcount
    log.info(f"Neon : {total} lignes supprimées au total")
    conn.commit()
    cur.close()
    conn.close()

    client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
    collection = os.environ["QDRANT_COLLECTION"]
    point_ids = [str(uuid.uuid5(_NAMESPACE, f"{brand}|{name}|{variant}")) for brand, name, variant in STALE]
    log.info(f"Qdrant : suppression de {point_ids}")
    client.delete(collection_name=collection, points_selector=point_ids)
    log.info("Qdrant : suppression effectuée")


if __name__ == "__main__":
    main()
