"""
Script de sondage temporaire — à supprimer après usage.
L'utilisateur signale que c'est "encore pire" : beaucoup de lignes
Kverneland auraient un nom = valeur de spec plutôt qu'un vrai modèle. Le
bug "une ligne par modèle" (déjà corrigé dans scraper.py) a pu toucher BEAUCOUP
plus de fiches que les 2 repérées initialement — sur toutes ces fiches,
l'ancien code produisait une unique machine par page avec un nom bidon ET
des specs dont les CLÉS ressemblent à de vrais noms de modèles (ex.
{"Capacity (m³)": "...", "Compact 1612-12": "12", ...}), signature
distinctive du bug. On balaie TOUTES les lignes Kverneland pour détecter ce
pattern.
"""

import json
import logging
import os
import re

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

# Une clé de specs qui ressemble à un nom de modèle (contient un chiffre et
# soit un tiret soit plusieurs mots) plutôt qu'à un libellé d'attribut
# classique (qui est généralement court et sans chiffre, ou juste "X (unité)").
MODEL_LIKE_KEY = re.compile(r"^[A-Za-zÀ-ÿ]+[\s-][\w.\-]*\d")


def looks_like_model_key(key: str) -> bool:
    return bool(MODEL_LIKE_KEY.match(key.strip()))


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute(
        """SELECT name, variant, specs, "sourceUrl" FROM "Machine" WHERE brand = 'Kverneland'"""
    )
    rows = cur.fetchall()
    log.info(f"Kverneland : {len(rows)} lignes au total\n")

    suspects = []
    for name, variant, specs_json, source_url in rows:
        try:
            specs = json.loads(specs_json) if specs_json else {}
        except Exception:
            specs = {}
        model_like_keys = [k for k in specs if looks_like_model_key(k)]
        if len(model_like_keys) >= 2:
            suspects.append((name, variant, model_like_keys, source_url))

    log.info(f"{len(suspects)} lignes avec signature du bug 'une ligne par modèle' :\n")
    for name, variant, model_like_keys, source_url in suspects:
        log.info(f"  {name!r} / {variant!r} — clés suspectes: {model_like_keys} — {source_url}")

    log.info(f"\n=== TOTAL : {len(suspects)} lignes affectées sur {len(rows)} ===")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
