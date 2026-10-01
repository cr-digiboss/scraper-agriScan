"""
Script de nettoyage ponctuel — à supprimer après usage.
Supprime les anciennes lignes Franquet corrompues (noms = valeurs de specs
comme "Suiveuse"/"FIXE" au lieu de vrais noms de machine) de Neon et Qdrant,
produites par l'ancien parseur générique avant le fix du parseur dédié.
"""

import logging
import os

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

import db

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("cleanup")


def cleanup_neon() -> int:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM "Machine" WHERE brand = %s', ("Franquet",))
            count = cur.fetchone()[0]
            log.info(f"Neon : {count} lignes Franquet trouvées")
            cur.execute('DELETE FROM "Machine" WHERE brand = %s', ("Franquet",))
        conn.commit()
        log.info(f"Neon : {count} lignes Franquet supprimées")
        return count
    finally:
        conn.close()


def cleanup_qdrant() -> int:
    if not all(os.getenv(v) for v in ("QDRANT_URL", "QDRANT_API_KEY", "QDRANT_COLLECTION")):
        log.warning("Qdrant : variables d'environnement manquantes, nettoyage ignoré")
        return 0
    client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
    collection = os.environ["QDRANT_COLLECTION"]
    if not client.collection_exists(collection):
        log.warning(f"Qdrant : collection « {collection} » absente, rien à nettoyer")
        return 0

    flt = Filter(must=[FieldCondition(key="marque", match=MatchValue(value="franquet"))])
    before = client.count(collection_name=collection, count_filter=flt).count
    log.info(f"Qdrant : {before} points Franquet trouvés")
    client.delete(collection_name=collection, points_selector=FilterSelector(filter=flt))
    log.info(f"Qdrant : {before} points Franquet supprimés")
    return before


def main():
    cleanup_neon()
    cleanup_qdrant()


if __name__ == "__main__":
    main()
