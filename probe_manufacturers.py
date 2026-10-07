"""
Script de sondage temporaire — à supprimer après usage.
L'utilisateur signale "Capacity (m³)" — un libellé d'attribut + unité entre
parenthèses pris pour un nom de machine, variante du bug déjà corrigé (mot
générique seul). On élargit la détection : un name/variant qui est un mot
générique suivi d'une unité entre parenthèses, ou qui contient une unité
entre parenthèses alors qu'il n'y a pas de chiffre ailleurs dans la valeur
(signe que c'est un libellé de colonne et pas un vrai modèle/variante).
"""

import logging
import os
import re

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

# Mots génériques (étendus) qui ne sont jamais un vrai nom de modèle/variante,
# avec ou sans unité entre parenthèses à la suite.
SUSPECT_WORDS = {
    "taille", "couleur", "poids", "largeur", "hauteur", "longueur",
    "capacité", "capacite", "capacity", "modèle", "modele", "model",
    "type", "puissance", "power", "vitesse", "speed", "diamètre",
    "diametre", "diameter", "pression", "pressure", "volume", "débit",
    "debit", "flow", "profondeur", "depth", "epaisseur", "épaisseur",
    "thickness", "unité", "unite", "unit", "norme", "standard", "série",
    "serie", "series", "range", "gamme", "référence", "reference", "code",
    "désignation", "designation", "value", "valeur", "min", "max", "mini",
    "maxi", "nombre", "number", "quantité", "quantite", "quantity",
    "dimension", "dimensions", "width", "height", "length", "weight",
    "color", "colour", "size",
}


def strip_parenthetical_unit(value: str) -> str:
    """Retire un suffixe entre parenthèses (ex. '(m³)', '(mm)') pour isoler
    le libellé de base."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", value).strip()


def is_suspect(value: str) -> bool:
    v = value.strip().lower().rstrip(".")
    if not v:
        return False
    if v in SUSPECT_WORDS:
        return True
    base = strip_parenthetical_unit(v)
    if base and base != v and base in SUSPECT_WORDS:
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

    log.info(f"{len(suspects)} lignes suspectes :\n")
    for brand, name, variant, source_url in suspects:
        log.info(f"  [{brand}] {name!r} / {variant!r} — {source_url}")

    log.info("\n--- Détail des sourceUrl des entrées suspectes ---")
    seen_urls = set()
    for _, _, _, source_url in suspects:
        if source_url in seen_urls:
            continue
        seen_urls.add(source_url)
        cur.execute(
            """SELECT brand, name, variant FROM "Machine" WHERE "sourceUrl" = %s ORDER BY name""",
            (source_url,),
        )
        family = cur.fetchall()
        log.info(f"\n{source_url} → {len(family)} lignes :")
        for brand, name, variant in family:
            log.info(f"  [{brand}] {name!r} / {variant!r}")

    log.info(f"\n=== TOTAL SUSPECTS : {len(suspects)} ===")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
