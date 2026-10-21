"""Indexation Qdrant pour l'assistant (AgriBot), à partir du nouveau schéma.

Reprend le format de l'ancien qdrant_sync.py pour rester compatible avec
app/api/chat/route.ts : même modèle d'embedding (mistral-embed), même payload
(marque / typeMachine en minuscules, nomModele, pageContent) et même id de point
(uuid5 de « marque|nom|variante ») : les points existants sont mis à jour, sans
doublon. Ajoute machineId, l'id de la fiche en base.

Sans QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION ou MISTRAL_API_KEY,
l'indexation est ignorée : elle ne fait jamais échouer la collecte.

Réindexer tout le catalogue (ancien backfill_qdrant.py) :
    python -m scraper_bis.indexation            # base DATABASE_URL
    python -m scraper_bis.indexation --dev      # base DATABASE_URL_DEV
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass

log = logging.getLogger("scraper_bis")

MISTRAL_EMBED_URL = "https://api.mistral.ai/v1/embeddings"
EMBED_MODEL = "mistral-embed"
EMBED_DIM = 1024
LOT = 32
_NAMESPACE = uuid.UUID("6f6e6f9e-6c7a-4c8e-9c9a-3a6b6f6f6c61")  # identique à qdrant_sync.py


@dataclass
class Document:
    machine_id: str
    marque: str
    nom: str
    variante: str = ""
    gamme: str = ""
    categorie: str = ""
    sous_categorie: str = ""
    description: str = ""
    specs: dict | None = None

    def point_id(self) -> str:
        return str(uuid.uuid5(_NAMESPACE, f"{self.marque}|{self.nom}|{self.variante}"))

    def texte(self) -> str:
        parts = [f"{self.marque} {self.nom}".strip()]
        if self.gamme:
            parts.append(f"Gamme : {self.gamme}")
        if self.variante:
            parts.append(f"Variante : {self.variante}")
        if self.categorie:
            parts.append(f"Catégorie : {self.categorie}")
        if self.sous_categorie:
            parts.append(f"Sous-catégorie : {self.sous_categorie}")
        if self.description:
            parts.append(self.description)
        specs = ", ".join(f"{k} : {v}" for k, v in (self.specs or {}).items() if v)
        if specs:
            parts.append(f"Caractéristiques : {specs}")
        return "\n".join(parts)


def configure() -> bool:
    return all(os.getenv(v) for v in ("QDRANT_URL", "QDRANT_API_KEY", "QDRANT_COLLECTION", "MISTRAL_API_KEY"))


def depuis_fiche(machine_id: str, f) -> Document:
    """Document à partir d'une FicheExtraite qui vient d'être écrite."""
    b = f.brute
    return Document(machine_id, b.marque, b.nom, b.variante, b.gamme, f.categorie_nom, b.sous_categorie,
                    b.description, b.specs)


def _embeddings(textes: list[str]) -> list[list[float]]:
    import requests

    r = requests.post(
        MISTRAL_EMBED_URL,
        headers={"Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}", "Content-Type": "application/json"},
        json={"model": EMBED_MODEL, "input": textes},
        timeout=60,
    )
    r.raise_for_status()
    return [d["embedding"] for d in r.json()["data"]]


def indexer(docs: list[Document]) -> tuple[int, int]:
    """Indexe des documents dans Qdrant. Retourne (indexés, erreurs)."""
    if not docs:
        return 0, 0
    if not configure():
        log.info("Qdrant non configuré : indexation ignorée")
        return 0, 0

    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PayloadSchemaType, PointStruct, VectorParams

    client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
    collection = os.environ["QDRANT_COLLECTION"]
    try:
        if not client.collection_exists(collection):
            client.create_collection(collection, vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE))
        for champ in ("marque", "typeMachine", "machineId"):
            client.create_payload_index(collection, field_name=champ, field_schema=PayloadSchemaType.KEYWORD)
    except Exception as e:
        log.warning(f"Qdrant : collection inaccessible ({e})")
        return 0, len(docs)

    ok = err = 0
    for i in range(0, len(docs), LOT):
        lot = docs[i:i + LOT]
        textes = [d.texte() for d in lot]
        try:
            vecteurs = _embeddings(textes)
            client.upsert(collection, points=[
                PointStruct(id=d.point_id(), vector=v, payload={
                    "machineId": d.machine_id,
                    "marque": d.marque.lower(),
                    "nomModele": d.nom,
                    "typeMachine": d.categorie.lower(),
                    "pageContent": t,
                })
                for d, v, t in zip(lot, vecteurs, textes)
            ])
            ok += len(lot)
        except Exception as e:
            log.warning(f"Qdrant : échec d'un lot de {len(lot)} machines ({e})")
            err += len(lot)
    return ok, err


SQL_TOUT = '''
    SELECT m.id, c.nom, m.name, m.variant, coalesce(m.range, ''),
           coalesce(p."nomFr", k."nomFr"), CASE WHEN p.id IS NULL THEN '' ELSE k."nomFr" END,
           coalesce(m.description, ''), m.specs
    FROM "Machine" m
    JOIN "Constructeur" c ON c.id = m."constructeurId"
    JOIN "Categorie" k ON k.id = m."categorieId"
    LEFT JOIN "Categorie" p ON p.id = k."parentId"
    ORDER BY m."createdAt"
'''


def tout_reindexer(url: str) -> tuple[int, int]:
    import psycopg2

    conn = psycopg2.connect(url)
    total_ok = total_err = vus = 0
    try:
        with conn.cursor(name="indexation_qdrant") as cur:
            cur.itersize = 200
            cur.execute(SQL_TOUT)
            while rows := cur.fetchmany(200):
                docs = []
                for mid, marque, nom, variante, gamme, cat, sous, desc, specs in rows:
                    if isinstance(specs, str):
                        try:
                            specs = json.loads(specs)
                        except ValueError:
                            specs = {}
                    docs.append(Document(mid, marque, nom, variante, gamme, cat, sous, desc,
                                         specs if isinstance(specs, dict) else {}))
                ok, err = indexer(docs)
                vus += len(docs)
                total_ok += ok
                total_err += err
                log.info(f"{vus} machines parcourues, {total_ok} indexées, {total_err} erreurs")
    finally:
        conn.close()
    return total_ok, total_err


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scraper_bis.indexation", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dev", action="store_true", help="lire la base DATABASE_URL_DEV au lieu de DATABASE_URL")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    if not configure():
        log.error("QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION et MISTRAL_API_KEY sont nécessaires.")
        return 1
    url = os.environ.get("DATABASE_URL_DEV" if args.dev else "DATABASE_URL")
    if not url:
        log.error("URL de base absente.")
        return 1
    ok, err = tout_reindexer(url)
    log.info(f"Terminé : {ok} machines indexées, {err} erreurs")
    return 0 if not err else 1


if __name__ == "__main__":
    sys.exit(main())
