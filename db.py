"""
AgriScan — Connexion à la base Neon (PostgreSQL)

La connexion utilise uniquement la variable d'environnement DATABASE_URL
(définie dans .env en local, ou en secret GitHub Actions en production).
"""

import os
import json
import logging

import psycopg2

log = logging.getLogger("agriscan")


def get_connection():
    """Ouvre une connexion à Neon à partir de DATABASE_URL."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL n'est pas défini. "
            "Ajoutez-le dans un fichier .env (local) ou dans les secrets GitHub Actions (CI)."
        )
    return psycopg2.connect(db_url)


def get_existing_keys(conn) -> set:
    """Retourne l'ensemble des machines déjà en base, sous forme 'brand|name|variant'."""
    with conn.cursor() as cur:
        cur.execute('SELECT brand, name, variant FROM "Machine"')
        return {f"{brand}|{name}|{variant}" for brand, name, variant in cur.fetchall()}


MACHINE_COLUMNS = [
    "brand", "range", "name", "variant", "category", "subcategory",
    "description", "specs", "sourceUrl",
]

_SELECT_MACHINES_SQL = (
    'SELECT brand, range, name, variant, category, subcategory, '
    'description, specs, "sourceUrl" FROM "Machine" ORDER BY "createdAt"'
)


def iter_all_machines(conn, batch_size: int = 200):
    """Parcourt toutes les machines de Neon par lots (pour le backfill Qdrant).

    Utilise un curseur nommé pour éviter de charger tout le catalogue en
    mémoire d'un coup. Retourne des dicts avec les mêmes noms de champs
    que le dataclass Machine (brand, range, name, ...) pour être réutilisés
    directement par qdrant_sync.
    """
    with conn.cursor(name="agriscan_backfill") as cur:
        cur.itersize = batch_size
        cur.execute(_SELECT_MACHINES_SQL)
        while True:
            rows = cur.fetchmany(batch_size)
            if not rows:
                break
            batch = []
            for row in rows:
                data = dict(zip(MACHINE_COLUMNS, row))
                data["specs"] = json.dumps(data["specs"]) if isinstance(data["specs"], dict) else (data["specs"] or "{}")
                batch.append(data)
            yield batch


UPSERT_SQL = """
    INSERT INTO "Machine" (
        id, brand, range, name, variant,
        category, subcategory, description,
        specs, "imageUrl", "videoUrl", "sourceUrl",
        statut, "anneeDebut", "anneeFin", "createdAt"
    ) VALUES (
        gen_random_uuid()::text,
        %(brand)s, %(range)s, %(name)s, %(variant)s,
        %(category)s, %(subcategory)s, %(description)s,
        %(specs)s::jsonb, %(imageUrl)s, %(videoUrl)s, %(sourceUrl)s,
        %(statut)s, %(anneeDebut)s, %(anneeFin)s, NOW()
    )
    ON CONFLICT (brand, name, variant) DO UPDATE SET
        range        = EXCLUDED.range,
        category     = EXCLUDED.category,
        subcategory  = EXCLUDED.subcategory,
        description  = EXCLUDED.description,
        specs        = EXCLUDED.specs,
        "imageUrl"   = EXCLUDED."imageUrl",
        "sourceUrl"  = EXCLUDED."sourceUrl",
        statut       = EXCLUDED.statut,
        "anneeDebut" = EXCLUDED."anneeDebut",
        "anneeFin"   = EXCLUDED."anneeFin"
"""


def upsert_machines(conn, machines) -> tuple[int, int]:
    """Insère ou met à jour une liste de machines dans Neon. Retourne (réussies, erreurs)."""
    ok, errors = 0, 0
    with conn.cursor() as cur:
        for m in machines:
            try:
                cur.execute(UPSERT_SQL, {
                    "brand": (m.brand or "")[:255],
                    "range": m.range or None,
                    "name": (m.name or "")[:255],
                    "variant": m.variant or "",
                    "category": (m.category or "")[:255],
                    "subcategory": m.subcategory or None,
                    "description": m.description or None,
                    "specs": m.specs or "{}",
                    "imageUrl": m.imageUrl or None,
                    "videoUrl": m.videoUrl or None,
                    "sourceUrl": m.sourceUrl or None,
                    "statut": m.statut or "active",
                    "anneeDebut": int(m.anneeDebut) if m.anneeDebut else None,
                    "anneeFin": int(m.anneeFin) if m.anneeFin else None,
                })
                ok += 1
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass  # connexion déjà perdue (ex. timeout Neon) : rien à annuler
                errors += 1
                log.warning(f"  Erreur upsert {m.brand} {m.name} : {e}")
    conn.commit()
    return ok, errors
