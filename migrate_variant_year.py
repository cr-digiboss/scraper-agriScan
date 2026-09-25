"""
Script de migration à usage unique — à supprimer après exécution.

Retire l'année du champ `variant` pour les fiches issues de TractorData
(scrape_marque) déjà en base, suite au changement de scraper.py qui ne
met plus la date dans le variant. La contrainte d'unicité Neon porte sur
(brand, name, variant) : les groupes qui avaient plusieurs entrées pour le
même modèle (une par année) sont consolidés en une seule fiche (on garde
la plus récente par anneeDebut, les autres sont supprimées).

Nettoie aussi Qdrant : l'id du point est dérivé de brand|name|variant, donc
change quand le variant change. On supprime les anciens points et on
réindexe les fiches conservées avec leur nouvelle clé.

Usage :
    python migrate_variant_year.py
"""

import json
import logging
import uuid

import psycopg2.errors
from dotenv import load_dotenv

import db
import qdrant_sync
from scraper import Machine

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("migrate")

YEAR_PATTERN = r"^(19[0-9]{2}|20[0-2][0-9])$"

COLS = [
    "id", "brand", "range", "name", "variant", "category", "subcategory",
    "description", "specs", "sourceUrl", "anneeDebut", "anneeFin",
]


def _old_point_id(brand: str, name: str, variant: str) -> str:
    return str(uuid.uuid5(qdrant_sync._NAMESPACE, f"{brand}|{name}|{variant}"))


def main():
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute(
            f'SELECT id, brand, range, name, variant, category, subcategory, '
            f'description, specs, "sourceUrl", "anneeDebut", "anneeFin" '
            f'FROM "Machine" WHERE variant ~ \'{YEAR_PATTERN}\''
        )
        rows = cur.fetchall()

    groupes = {}
    for row in rows:
        d = dict(zip(COLS, row))
        groupes.setdefault((d["brand"], d["name"]), []).append(d)

    log.info(f"{len(rows)} lignes à traiter, {len(groupes)} groupes brand+name")

    old_point_ids = []
    a_reindexer = []
    maj, supprimees, conflits = 0, 0, 0

    for i, ((brand, name), items) in enumerate(groupes.items(), 1):
        if i % 200 == 0:
            log.info(f"  ... {i}/{len(groupes)} groupes traités")

        for d in items:
            old_point_ids.append(_old_point_id(brand, name, d["variant"]))

        # Garde la version la plus récente (anneeDebut le plus grand) quand
        # plusieurs années existent pour le même nom de modèle.
        items.sort(key=lambda d: (d["anneeDebut"] or 0), reverse=True)
        garde, *doublons = items

        with conn.cursor() as cur:
            for d in doublons:
                cur.execute('DELETE FROM "Machine" WHERE id = %s', (d["id"],))
            conn.commit()
        supprimees += len(doublons)

        with conn.cursor() as cur:
            try:
                cur.execute('UPDATE "Machine" SET variant = \'\' WHERE id = %s', (garde["id"],))
                conn.commit()
                maj += 1
                garde["variant"] = ""
                a_reindexer.append(garde)
            except psycopg2.errors.UniqueViolation:
                # Une fiche (brand, name, '') existe déjà : un scraper dédié
                # couvre ce même modèle avec des données à jour. La fiche
                # historique TractorData est redondante, on la supprime au
                # lieu de la laisser bloquée avec une année pour toujours.
                conn.rollback()
                with conn.cursor() as cur2:
                    cur2.execute('DELETE FROM "Machine" WHERE id = %s', (garde["id"],))
                    conn.commit()
                supprimees += 1
                conflits += 1
                log.warning(
                    f"  Doublon avec un scraper dédié, fiche historique supprimée : {brand} — {name}"
                )

    conn.close()
    log.info(
        f"\nTerminé : {maj} fiches mises à jour, {supprimees} doublons supprimés "
        f"(dont {conflits} en conflit avec un scraper dédié)"
    )

    if not qdrant_sync._configured():
        log.info("Qdrant non configuré, pas de nettoyage/réindexation.")
        return

    from qdrant_client import QdrantClient
    import os

    client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
    collection = os.environ["QDRANT_COLLECTION"]

    try:
        client.delete(collection_name=collection, points_selector=old_point_ids)
        log.info(f"Qdrant : {len(old_point_ids)} anciens points supprimés")
    except Exception as e:
        log.warning(f"Qdrant : échec suppression anciens points → {e}")

    machines = [
        Machine(
            brand=d["brand"], range=d["range"] or "", name=d["name"], variant="",
            category=d["category"] or "", subcategory=d["subcategory"] or "",
            description=d["description"] or "",
            specs=json.dumps(d["specs"]) if isinstance(d["specs"], dict) else (d["specs"] or "{}"),
            sourceUrl=d["sourceUrl"] or "",
        )
        for d in a_reindexer
    ]
    ok, errors = qdrant_sync.index_machines(machines)
    log.info(f"Qdrant : {ok} fiches réindexées, {errors} erreurs")


if __name__ == "__main__":
    main()
