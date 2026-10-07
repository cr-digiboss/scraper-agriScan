"""
Script de sondage temporaire — à supprimer après usage.
0 lignes avec la signature précédente : la théorie du bug généralisé "une
ligne par modèle" ne tient pas. On regarde maintenant TOUS les noms
Kverneland bruts (pas de filtre par mot-clé) pour repérer à l'œil ce qui ne
ressemble pas à un vrai nom de modèle, + on note les plus récents (créés
depuis le début du run #75, ~09:20 UTC) pour voir si le run en cours a
introduit de nouvelles lignes suspectes.
"""

import logging
import os

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute(
        """SELECT name, variant, "createdAt" FROM "Machine" WHERE brand = 'Kverneland'
           ORDER BY "createdAt" DESC"""
    )
    rows = cur.fetchall()
    log.info(f"Kverneland : {len(rows)} lignes au total\n")

    log.info("--- 40 lignes les plus récentes (pour voir ce que #75 a déjà inséré) ---")
    for name, variant, created_at in rows[:40]:
        log.info(f"  {name!r} / {variant!r} — créé={created_at}")

    # Noms courts (<=20 car.) à un seul mot : souvent révélateur d'un
    # libellé générique plutôt qu'un vrai nom de modèle structuré.
    log.info("\n--- Noms d'un seul mot (potentiellement suspects) ---")
    one_word = [(n, v, c) for n, v, c in rows if " " not in n.strip() and len(n) <= 20]
    log.info(f"{len(one_word)} lignes à un seul mot :")
    for name, variant, created_at in one_word:
        log.info(f"  {name!r} / {variant!r} — créé={created_at}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
