"""
AgriScan — Backfill Qdrant : indexe une bonne fois pour toutes les machines
déjà présentes dans Neon avant l'ajout de la synchronisation automatique
(qdrant_sync.py, appelée depuis scraper.py pour les machines nouvellement
scrapées uniquement).

À lancer une seule fois après avoir configuré QDRANT_URL, QDRANT_API_KEY,
QDRANT_COLLECTION et MISTRAL_API_KEY. Idempotent (id de point dérivé de la
clé naturelle brand/name/variant) : peut être relancé sans risque de
doublons si besoin.

Usage :
    python backfill_qdrant.py
"""

import logging

from dotenv import load_dotenv

import db
import qdrant_sync
from scraper import Machine

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("agriscan")


def main() -> int:
    if not qdrant_sync._configured():
        log.error(
            "QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION et MISTRAL_API_KEY "
            "doivent être définis pour lancer le backfill."
        )
        return 1

    conn = db.get_connection()
    total_ok, total_err, total_seen = 0, 0, 0
    try:
        for batch in db.iter_all_machines(conn):
            machines = [Machine(**row) for row in batch]
            total_seen += len(machines)
            ok, err = qdrant_sync.index_machines(machines)
            total_ok += ok
            total_err += err
            log.info(f"  Lot de {len(machines)} → {ok} indexées, {err} erreurs (total vu : {total_seen})")
    finally:
        conn.close()

    log.info(f"Terminé : {total_ok} machines indexées dans Qdrant sur {total_seen} vues, {total_err} erreurs")
    return 0


if __name__ == "__main__":
    main()
