"""
Script de sondage temporaire — à supprimer après usage.
L'utilisateur signale qu'il reste des entrées où un nom/variante est en fait
une valeur de spec (unité, libellé d'attribut) plutôt qu'un vrai nom de
machine/modèle — même classe de bug que "Taille" (déjà corrigé pour Same).
On balaie TOUTES les marques pour repérer les name/variant suspects : mots
génériques d'unité ou de libellé d'attribut plutôt que des codes/noms de
modèle.
"""

import logging
import os
import re

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

# Libellés/unités génériques qui ne sont jamais un vrai nom de modèle/variante.
SUSPECT_WORDS = {
    "taille", "couleur", "poids", "largeur", "hauteur", "longueur",
    "capacité", "capacite", "modèle", "modele", "type", "puissance",
    "vitesse", "diamètre", "diametre", "pression", "volume", "débit",
    "debit", "profondeur", "epaisseur", "épaisseur", "mm", "cm", "kg",
    "l", "kw", "ch", "bar", "tr/min", "m", "m²", "m2", "m3", "m³",
    "unité", "unite", "norme", "standard", "série", "serie", "gamme",
    "référence", "reference", "code", "désignation", "designation",
    "valeur", "min", "max", "min.", "max.", "mini", "maxi",
}


def is_suspect(value: str) -> bool:
    v = value.strip().lower().rstrip(".")
    if not v:
        return False  # variante vide = normal (pas de variante pour cette machine)
    if v in SUSPECT_WORDS:
        return True
    return False


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute(
        """SELECT brand, name, variant, "sourceUrl" FROM "Machine" ORDER BY brand, name, variant"""
    )
    rows = cur.fetchall()
    log.info(f"{len(rows)} lignes au total dans Neon\n")

    suspects = []
    for brand, name, variant, source_url in rows:
        if is_suspect(name) or is_suspect(variant):
            suspects.append((brand, name, variant, source_url))

    log.info(f"{len(suspects)} lignes suspectes (name/variant = mot générique d'unité/attribut) :\n")
    for brand, name, variant, source_url in suspects:
        log.info(f"  [{brand}] {name!r} / {variant!r} — {source_url}")

    log.info(f"\n=== TOTAL SUSPECTS : {len(suspects)} ===")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
