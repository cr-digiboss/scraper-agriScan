"""Scraper bis — test en dev du pipeline collecter → extraire → rapport → base de dev.

Exemples :
  python -m scraper_bis                                   # Kuhn, Lemken, Monosem, collecte en direct
  python -m scraper_bis --marques kuhn --max-categories 2 # test rapide
  python -m scraper_bis --depuis-xlsx machines_extracted.xlsx --marques kuhn,agrisem
  python -m scraper_bis --depuis-json sortie/2026-10-15_1130/brut.json --ecrire
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from .extraction import dedoublonner, extraire, separer_variantes
from .sources import MARQUES, collecter, depuis_json, depuis_xlsx

log = logging.getLogger("scraper_bis")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scraper_bis", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marques", default="kuhn,lemken,monosem",
                    help="marques séparées par des virgules (défaut : kuhn,lemken,monosem)")
    origine = ap.add_mutually_exclusive_group()
    origine.add_argument("--depuis-xlsx", metavar="FICHIER", help="extraire depuis un Excel (colonnes brand, name, specs…)")
    origine.add_argument("--depuis-json", metavar="FICHIER", help="extraire depuis le brut.json d'une collecte précédente")
    ap.add_argument("--max-categories", type=int, metavar="N", help="collecte : seulement les N premières catégories par marque")
    ap.add_argument("--llm", action="store_true", help="compléter les champs clés manquants avec Mistral (MISTRAL_API_KEY)")
    ap.add_argument("--llm-max", type=int, default=50, metavar="N", help="nombre maximal de machines envoyées au LLM (défaut 50)")
    ap.add_argument("--ecrire", action="store_true", help="écrire dans la base de DEV (DATABASE_URL_DEV)")
    ap.add_argument("--sortie", default="sortie", help="dossier des résultats (défaut : sortie/)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    marques = [m.strip().lower() for m in args.marques.split(",") if m.strip()]

    # Sécurité : jamais la base de production
    url_dev = None
    if args.ecrire:
        url_dev = os.environ.get("DATABASE_URL_DEV")
        if not url_dev:
            log.error("--ecrire demande DATABASE_URL_DEV (base ou branche Neon de dev). Rien n'a été écrit.")
            return 2
        if url_dev == os.environ.get("DATABASE_URL"):
            log.error("DATABASE_URL_DEV est identique à DATABASE_URL (production). Écriture refusée.")
            return 2

    # 1. Fiches brutes
    journal: dict[str, dict] = {}
    if args.depuis_xlsx:
        brutes = depuis_xlsx(args.depuis_xlsx, set(marques) if args.marques != ap.get_default("marques") else None)
        origine_txt = f"fichier Excel {Path(args.depuis_xlsx).name}"
    elif args.depuis_json:
        brutes = depuis_json(args.depuis_json)
        origine_txt = f"collecte précédente {args.depuis_json}"
    else:
        inconnues = [m for m in marques if m not in MARQUES]
        if inconnues:
            log.error(f"Marques non branchées : {', '.join(inconnues)}. Disponibles : {', '.join(MARQUES)}")
            return 2
        brutes, journal = collecter(marques, args.max_categories)
        origine_txt = "collecte en direct sur les sites constructeurs"
    log.info(f"{len(brutes)} fiches brutes")

    # 2. Extraction
    extraites, doublons = dedoublonner([extraire(f) for b in brutes for f in separer_variantes(b)])
    if doublons:
        log.info(f"{len(doublons)} doublons écartés (voir le rapport)")
    if args.llm:
        from .llm import completer

        n = completer(extraites, args.llm_max)
        log.info(f"LLM : {n} machines complétées")

    # 3. Écriture en base de dev
    ecriture = None
    if url_dev:
        from .ecriture import EcritureDev, hote

        log.info(f"Écriture dans la base de dev : {hote(url_dev)}")
        ecr = EcritureDev(url_dev)
        try:
            for e in extraites:
                ecr.ecrire(e)
        finally:
            ecr.fermer()
        ecriture = {"hote": hote(url_dev), "compteurs": dict(ecr.compteurs),
                    "non_classees": dict(ecr.categories_non_classees)}

    # 4. Rapport
    from .rapport import ecrire_sorties

    dossier = Path(args.sortie) / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    chemin = ecrire_sorties(dossier, brutes, extraites, journal, ecriture, origine_txt, doublons)
    log.info(f"Rapport : {chemin}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
