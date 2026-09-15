"""
AgriScan — Connexion à la base Neon (PostgreSQL)

La connexion utilise uniquement la variable d'environnement DATABASE_URL
(définie dans .env en local, ou en secret GitHub Actions en production).
"""

import os
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
