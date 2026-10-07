"""
Script de sondage temporaire — à supprimer après usage.
L'utilisateur signale aussi [Kverneland] 'Capacity' (anglais, pas couvert
par la liste de mots précédente qui n'avait que la version française
"capacité"). On élargit la recherche à TOUTES les marques avec des mots
génériques en anglais ET français, et on liste le détail complet de
n'importe quel sourceUrl partagé par une entrée suspecte (pour voir les
autres entrées garbage potentiellement associées, comme pour Kuhn).
"""

import logging
import os

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")

SUSPECT_WORDS = {
    # français
    "taille", "couleur", "poids", "largeur", "hauteur", "longueur",
    "capacité", "capacite", "modèle", "modele", "type", "puissance",
    "vitesse", "diamètre", "diametre", "pression", "volume", "débit",
    "debit", "profondeur", "epaisseur", "épaisseur", "unité", "unite",
    "norme", "standard", "série", "serie", "gamme", "référence",
    "reference", "code", "désignation", "designation", "valeur",
    "min", "max", "min.", "max.", "mini", "maxi", "nombre", "quantité",
    "quantite", "dimension", "dimensions",
    # anglais
    "capacity", "width", "height", "length", "weight", "color", "colour",
    "model", "type", "power", "speed", "diameter", "pressure", "volume",
    "flow", "depth", "thickness", "unit", "standard", "series", "range",
    "reference", "value", "number", "quantity", "dimension", "dimensions",
    "size",
    # unités
    "mm", "cm", "kg", "l", "kw", "ch", "bar", "tr/min", "m", "m²", "m2",
    "m3", "m³", "hp", "rpm", "lbs", "ft", "in",
}


def is_suspect(value: str) -> bool:
    v = value.strip().lower().rstrip(".")
    if not v:
        return False
    return v in SUSPECT_WORDS


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

    # Détail complet des sourceUrl partagées par une entrée suspecte.
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
