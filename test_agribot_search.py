"""
Script de test temporaire — à supprimer après usage.
Reproduit exactement la logique de searchMachines côté agriscan
(app/api/chat/route.ts) pour vérifier que la recherche vectorielle
fonctionne réellement après le backfill Qdrant : même modèle
d'embedding (mistral-embed), même seuil de score (0.72), même client
Qdrant. Ne touche à rien, lecture seule.
"""

import os
import logging

import requests
from qdrant_client import QdrantClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("test")

MIN_SCORE = 0.72
QUERIES = [
    "je cherche un tracteur puissant pour une exploitation de 80 hectares",
    "un semoir de précision pour du maïs",
    "une presse à balles rondes",
    "un tracteur Fendt",
    "un pulvérisateur automoteur pour grandes cultures",
]


def embed(text: str) -> list[float]:
    resp = requests.post(
        "https://api.mistral.ai/v1/embeddings",
        headers={
            "Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={"model": "mistral-embed", "input": [text]},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def main():
    client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
    collection = os.environ["QDRANT_COLLECTION"]

    info = client.get_collection(collection)
    log.info(f"Collection « {collection} » : {info.points_count} points, config vecteurs : {info.config.params.vectors}")

    for query in QUERIES:
        log.info(f"\n{'=' * 80}\nRequête : {query}\n{'=' * 80}")
        vector = embed(query)
        response = client.query_points(collection, query=vector, limit=10, with_payload=True)
        results = response.points
        above_threshold = [r for r in results if r.score >= MIN_SCORE]
        log.info(f"{len(results)} résultats bruts, {len(above_threshold)} au-dessus du seuil {MIN_SCORE}")
        for r in results[:5]:
            marque = r.payload.get("marque", "?")
            nom = r.payload.get("nomModele", "?")
            flag = "✓" if r.score >= MIN_SCORE else " "
            log.info(f"  [{flag}] score={r.score:.3f}  {marque} — {nom}")


if __name__ == "__main__":
    main()
