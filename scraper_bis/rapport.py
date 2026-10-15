"""Fichiers de sortie : brut.json, extrait.json, rapport.md, libelles_non_reconnus.csv."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from .extraction import champs_cles
from .modele import FicheBrute, FicheExtraite

LIBELLES = {
    "typeAttelage": "Type d'attelage", "largeurTravailMinM": "Largeur de travail", "puissanceRequiseMinCh": "Puissance requise",
    "largeurTransportM": "Largeur au transport", "poidsVideKg": "Poids", "puissanceMoteurCh": "Puissance moteur",
    "normeAntipollution": "Norme antipollution",
}


def _pct(n: int, total: int) -> str:
    return f"{round(100 * n / total)} %" if total else "-"


def ecrire_sorties(
    dossier: Path,
    brutes: list[FicheBrute],
    extraites: list[FicheExtraite],
    journal: dict[str, dict],
    ecriture: dict | None,
    origine: str,
    doublons: list[str] | None = None,
) -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "brut.json").write_text(
        json.dumps([asdict(b) for b in brutes], ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (dossier / "extrait.json").write_text(
        json.dumps([e.en_dict() for e in extraites], ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )

    # Libellés non reconnus : de quoi enrichir les règles
    non_reconnus: Counter = Counter()
    exemples: dict[str, str] = {}
    for e in extraites:
        for lib in e.non_reconnus:
            non_reconnus[lib] += 1
            exemples.setdefault(lib, str(e.brute.specs.get(lib, ""))[:80])
    with (dossier / "libelles_non_reconnus.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["libelle", "occurrences", "exemple"])
        for lib, n in non_reconnus.most_common():
            w.writerow([lib, n, exemples[lib]])

    # Couverture des champs clés par marque
    par_marque: dict[str, list[FicheExtraite]] = defaultdict(list)
    for e in extraites:
        par_marque[e.brute.marque].append(e)

    lignes = [
        "# Rapport du scraper bis",
        "",
        f"Origine des données : {origine}. {len(brutes)} fiches brutes, {len(extraites)} machines après séparation des variantes.",
        "",
    ]
    if journal:
        lignes += ["## Collecte", "", "| Marque | robots.txt | Fiches | Durée | Erreur |", "| --- | --- | --- | --- | --- |"]
        for marque, j in journal.items():
            lignes.append(f"| {marque} | {j['robots']} | {j['fiches']} | {j['duree_s']} s | {j['erreur'] or ''} |")
        lignes.append("")

    lignes += [
        "## Couverture des champs clés",
        "",
        "Part des machines pour lesquelles le champ a été extrait. Les champs clés dépendent du type de machine "
        "(outil, automoteur, tracteur), comme dans l'écran de relecture.",
        "",
        "| Marque | Machines | Méthode | Complètes | " + " | ".join(LIBELLES.values()) + " |",
        "| --- | --- | --- | --- | " + " | ".join("---" for _ in LIBELLES) + " |",
    ]
    total_completes = 0
    for marque, liste in sorted(par_marque.items(), key=lambda x: -len(x[1])):
        n = len(liste)
        completes = sum(1 for e in liste if all(c in e.champs for c in champs_cles(e)))
        total_completes += completes
        methodes = ", ".join(sorted({"PDF" if e.brute.methode == "EXTRACTION_PDF" else "Web" for e in liste}))
        cellules = []
        for champ in LIBELLES:
            concernees = [e for e in liste if champ in champs_cles(e)]
            cellules.append(_pct(sum(1 for e in concernees if champ in e.champs), len(concernees)) if concernees else "")
        lignes.append(f"| {marque} | {n} | {methodes} | {_pct(completes, n)} | " + " | ".join(cellules) + " |")
    lignes += ["", f"**Total : {total_completes} machines sur {len(extraites)} ont tous leurs champs clés "
               f"({_pct(total_completes, len(extraites))}).**", ""]

    if doublons:
        lignes += ["## Doublons", "", "Même marque, nom et variante dans la même collecte : une seule fiche est gardée.", ""]
        lignes += [f"- {d}" for d in doublons[:30]]
        lignes.append("")

    ecartes = Counter(x.split(" : ")[0] for e in extraites for x in e.ecartes)
    if ecartes:
        lignes += ["## Valeurs écartées", "", "Lues mais non retenues (plusieurs valeurs pour une seule machine, valeur invraisemblable).", "",
                   "| Libellé | Occurrences |", "| --- | --- |"]
        lignes += [f"| {lib} | {n} |" for lib, n in ecartes.most_common(15)]
        lignes.append("")

    lignes += ["## Libellés non reconnus (les 25 plus fréquents)", "",
               "Liste complète dans `libelles_non_reconnus.csv`. Ajouter les utiles aux règles de `extraction.py`.", "",
               "| Libellé | Occurrences | Exemple |", "| --- | --- | --- |"]
    lignes += [f"| {lib} | {n} | {exemples[lib]} |" for lib, n in non_reconnus.most_common(25)]
    lignes.append("")

    if ecriture is not None:
        c = ecriture["compteurs"]
        lignes += [
            "## Écriture en base de dev", "",
            f"Base : `{ecriture['hote']}`", "",
            "| Résultat | Nombre |", "| --- | --- |",
            f"| Machines créées | {c.get('creee', 0)} |",
            f"| Machines mises à jour | {c.get('mise_a_jour', 0)} |",
            f"| Inchangées (même contenu) | {c.get('inchangee', 0)} |",
            f"| Ignorées (catégorie non classée) | {c.get('ignoree_categorie', 0)} |",
            f"| Erreurs | {c.get('erreur', 0)} |",
            f"| Colonnes remplies | {c.get('colonnes_ecrites', 0)} |",
            f"| Valeurs seulement proposées (champ déjà validé) | {c.get('valeurs_proposees', 0)} |",
            "",
        ]
        if ecriture["non_classees"]:
            lignes.append(
                "Catégories sans famille connue (ajouter `AUTRE` à l'enum `Famille`, ou un mot-clé dans "
                "`normalisation.py`) : " + ", ".join(f"{k} ({v})" for k, v in ecriture["non_classees"].items())
            )
            lignes.append("")

    chemin = dossier / "rapport.md"
    chemin.write_text("\n".join(lignes), encoding="utf-8")
    return chemin
