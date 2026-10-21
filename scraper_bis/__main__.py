"""Scraper AgriScan : collecter → extraire → écrire en base → indexer dans Qdrant → rapport.

Remplace l'ancien scraper.py + db.py + qdrant_sync.py (les fonctions de collecte de
scraper.py sont réutilisées telles quelles).

Exemples :
  python -m scraper_bis                                     # Kuhn, Lemken, Monosem, sans écrire
  python -m scraper_bis --marques kuhn --max-categories 2   # test rapide
  python -m scraper_bis --marques toutes --ecrire           # nouveautés → base de DEV
  python -m scraper_bis --marques toutes --ecrire --prod --qdrant            # nuit : nouveautés → PRODUCTION
  python -m scraper_bis --marques toutes --ecrire --prod --qdrant --complet  # tout relire → PRODUCTION
  python -m scraper_bis --depuis-json sortie/2026-10-15_1130/brut.json --ecrire

Collecte avec --ecrire : par défaut seules les machines absentes de la base sont lues
(comme l'ancien scraper de nuit) ; --complet relit tout le catalogue pour suivre les
changements de fiches (specs, machines arrêtées).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from .extraction import dedoublonner, extraire, separer_variantes
from .sources import MARQUES, collecter, depuis_json, depuis_xlsx, resoudre_marques

log = logging.getLogger("scraper_bis")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scraper_bis", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marques", default="kuhn,lemken,monosem",
                    help="marques séparées par des virgules, ou « toutes » (défaut : kuhn,lemken,monosem)")
    origine = ap.add_mutually_exclusive_group()
    origine.add_argument("--depuis-xlsx", metavar="FICHIER", help="extraire depuis un Excel (colonnes brand, name, specs…)")
    origine.add_argument("--depuis-json", metavar="FICHIER", help="extraire depuis le brut.json d'une collecte précédente")
    ap.add_argument("--max-categories", type=int, metavar="N", help="collecte : seulement les N premières catégories par marque")
    ap.add_argument("--complet", action="store_true", help="collecte : relire aussi les machines déjà en base")
    ap.add_argument("--llm", action="store_true", help="compléter les champs clés manquants avec Mistral (MISTRAL_API_KEY)")
    ap.add_argument("--llm-max", type=int, default=50, metavar="N", help="nombre maximal de machines envoyées au LLM (défaut 50)")
    ap.add_argument("--ecrire", action="store_true", help="écrire en base : DEV (DATABASE_URL_DEV), ou production avec --prod")
    ap.add_argument("--prod", action="store_true", help="avec --ecrire : écrire dans la base de PRODUCTION (DATABASE_URL)")
    ap.add_argument("--qdrant", action="store_true", help="indexer dans Qdrant les machines créées ou modifiées")
    ap.add_argument("--sortie", default="sortie", help="dossier des résultats (défaut : sortie/)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    # ── Base cible
    url = None
    if args.prod and not args.ecrire:
        log.error("--prod ne s'utilise qu'avec --ecrire.")
        return 2
    if args.qdrant and not args.prod:
        log.error("--qdrant demande --ecrire --prod : la collection Qdrant est celle de la production.")
        return 2
    if args.ecrire:
        if args.prod:
            url = os.environ.get("DATABASE_URL")
            if not url:
                log.error("--prod demande DATABASE_URL. Rien n'a été écrit.")
                return 2
        else:
            url = os.environ.get("DATABASE_URL_DEV")
            if not url:
                log.error("--ecrire demande DATABASE_URL_DEV (base de dev), ou --prod pour la production. Rien n'a été écrit.")
                return 2
            if url == os.environ.get("DATABASE_URL"):
                log.error("DATABASE_URL_DEV est identique à DATABASE_URL (production) : ajoutez --prod si c'est voulu.")
                return 2

    from .ecriture import Ecriture, hote

    cible = f"{'PRODUCTION' if args.prod else 'dev'} ({hote(url)})" if url else None
    if cible:
        log.info(f"Écriture dans la base de {cible}")

    # ── Traitement d'un lot de fiches brutes : extraction, écriture, indexation
    extraites_toutes = []
    doublons_tous: list[str] = []
    compteurs: Counter = Counter()
    non_classees: Counter = Counter()
    qdrant = Counter()

    def traiter(nom_lot: str, brutes):
        extraites, doublons = dedoublonner([extraire(f) for b in brutes for f in separer_variantes(b)])
        if args.llm:
            from .llm import completer

            log.info(f"{nom_lot} : LLM, {completer(extraites, args.llm_max)} machines complétées")
        extraites_toutes.extend(extraites)
        doublons_tous.extend(doublons)
        if not url:
            return
        ecr = Ecriture(url)
        try:
            for e in extraites:
                ecr.ecrire(e)
        finally:
            ecr.fermer()
        compteurs.update(ecr.compteurs)
        non_classees.update(ecr.categories_non_classees)
        log.info(f"{nom_lot} : " + ", ".join(f"{k} {v}" for k, v in sorted(ecr.compteurs.items())))
        if args.qdrant and ecr.modifiees:
            from .indexation import depuis_fiche, indexer

            ok, err = indexer([depuis_fiche(mid, f) for mid, f in ecr.modifiees])
            qdrant["indexees"] += ok
            qdrant["erreurs"] += err
            log.info(f"{nom_lot} : Qdrant, {ok} indexées, {err} erreurs")

    # ── 1. Fiches brutes
    journal: dict[str, dict] = {}
    if args.depuis_xlsx or args.depuis_json:
        if args.depuis_xlsx:
            filtre = None
            if args.marques != ap.get_default("marques"):
                filtre = {m.strip().lower() for m in args.marques.split(",") if m.strip()}
            brutes = depuis_xlsx(args.depuis_xlsx, filtre)
            origine_txt = f"fichier Excel {Path(args.depuis_xlsx).name}"
        else:
            brutes = depuis_json(args.depuis_json)
            origine_txt = f"collecte précédente {args.depuis_json}"
        traiter("fichier", brutes)
    else:
        marques, inconnues = resoudre_marques(args.marques)
        if inconnues:
            log.error(f"Marques inconnues : {', '.join(inconnues)}. Disponibles : toutes, {', '.join(MARQUES)}")
            return 2
        existantes: set[str] = set()
        if url and not args.complet:
            ecr = Ecriture(url)
            try:
                existantes = ecr.cles_existantes()
            finally:
                ecr.fermer()
            log.info(f"{len(existantes)} machines déjà en base : seules les nouvelles seront lues (--complet pour tout relire)")
        brutes, journal = collecter(marques, args.max_categories, existantes, apres_marque=traiter)
        mode = "complète" if (args.complet or not url) else "nouveautés seulement"
        origine_txt = f"collecte en direct sur les sites constructeurs ({mode}, {len(marques)} marques)"
    log.info(f"{len(brutes)} fiches brutes")
    if doublons_tous:
        log.info(f"{len(doublons_tous)} doublons écartés (voir le rapport)")

    ecriture = None
    if url:
        ecriture = {"hote": cible, "compteurs": dict(compteurs), "non_classees": dict(non_classees)}
        if args.qdrant:
            ecriture["compteurs"].update({f"qdrant_{k}": v for k, v in qdrant.items()})

    # ── 2. Rapport
    from .rapport import ecrire_sorties

    dossier = Path(args.sortie) / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    chemin = ecrire_sorties(dossier, brutes, extraites_toutes, journal, ecriture, origine_txt, doublons_tous)
    log.info(f"Rapport : {chemin}")
    # Échec (rouge dans GitHub) seulement si des écritures ont échoué ; une marque dont
    # le site n'a pas répondu est signalée dans le rapport sans bloquer les autres.
    return 1 if compteurs.get("erreur") else 0


if __name__ == "__main__":
    sys.exit(main())
