"""
AgriScan — Synchronisation Qdrant pour l'assistant IA (AgriBot).

Après chaque upsert Neon, indexe les mêmes machines dans Qdrant pour que la
recherche vectorielle du chatbot (app/api/chat/route.ts côté agriscan) reste
à jour automatiquement. Utilise le même modèle d'embedding (mistral-embed)
que la recherche, pour rester dans le même espace vectoriel, et la même
convention de payload (marque/typeMachine en minuscules, filtrés par le
chatbot avec .toLowerCase()).

Si QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION ou MISTRAL_API_KEY ne sont
pas configurés, l'indexation est silencieusement ignorée : elle ne doit
jamais faire échouer le scraping principal.
"""

import os
import json
import uuid
import logging

import requests
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

log = logging.getLogger("agriscan")

MISTRAL_EMBED_URL = "https://api.mistral.ai/v1/embeddings"
EMBED_MODEL = "mistral-embed"
BATCH_SIZE = 32

# Namespace fixe pour dériver un id Qdrant stable à partir de la clé
# naturelle (brand, name, variant) : permet un upsert idempotent sans
# dépendre de l'id UUID généré côté Neon (jamais renvoyé au scraper).
_NAMESPACE = uuid.UUID("6f6e6f9e-6c7a-4c8e-9c9a-3a6b6f6f6c61")


def _point_id(m) -> str:
    return str(uuid.uuid5(_NAMESPACE, f"{m.brand}|{m.name}|{m.variant}"))


def _build_page_content(m) -> str:
    """Texte à embedder : reprend les champs utiles à la recherche sémantique."""
    parts = [f"{m.brand} {m.name}".strip()]
    if m.range:
        parts.append(f"Gamme : {m.range}")
    if m.variant:
        parts.append(f"Variante : {m.variant}")
    if m.category:
        parts.append(f"Catégorie : {m.category}")
    if m.subcategory:
        parts.append(f"Sous-catégorie : {m.subcategory}")
    if m.description:
        parts.append(m.description)
    if m.specs and m.specs != "{}":
        try:
            specs = json.loads(m.specs)
            specs_txt = ", ".join(f"{k} : {v}" for k, v in specs.items() if v)
            if specs_txt:
                parts.append(f"Caractéristiques : {specs_txt}")
        except (ValueError, TypeError):
            pass
    return "\n".join(parts)


def _embed_batch(texts: list[str]) -> list[list[float]]:
    resp = requests.post(
        MISTRAL_EMBED_URL,
        headers={
            "Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={"model": EMBED_MODEL, "input": texts},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return [item["embedding"] for item in data["data"]]


def _configured() -> bool:
    return all(
        os.getenv(v)
        for v in ("QDRANT_URL", "QDRANT_API_KEY", "QDRANT_COLLECTION", "MISTRAL_API_KEY")
    )


def index_machines(machines: list) -> tuple[int, int]:
    """Indexe une liste de Machine dans Qdrant. Retourne (réussies, erreurs)."""
    if not machines or not _configured():
        return 0, 0

    client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
    collection = os.environ["QDRANT_COLLECTION"]

    ok, errors = 0, 0
    for i in range(0, len(machines), BATCH_SIZE):
        batch = machines[i:i + BATCH_SIZE]
        texts = [_build_page_content(m) for m in batch]
        try:
            vectors = _embed_batch(texts)
        except Exception as e:
            log.warning(f"  Qdrant : échec embeddings ({len(batch)} machines) : {e}")
            errors += len(batch)
            continue

        points = [
            PointStruct(
                id=_point_id(m),
                vector=vector,
                payload={
                    "marque": (m.brand or "").lower(),
                    "nomModele": m.name,
                    "typeMachine": (m.category or "").lower(),
                    "pageContent": text,
                },
            )
            for m, vector, text in zip(batch, vectors, texts)
        ]

        try:
            client.upsert(collection_name=collection, points=points)
            ok += len(points)
        except Exception as e:
            log.warning(f"  Qdrant : échec upsert ({len(points)} machines) : {e}")
            errors += len(points)

    return ok, errors
