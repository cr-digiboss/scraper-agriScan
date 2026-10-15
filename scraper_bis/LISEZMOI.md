# Scraper bis — test en dev

Pipeline de test, à côté du scraper de production (`scraper.py` n'est pas modifié) :

1. **Collecter** : réutilise les fonctions de `scraper.py` (Kuhn, Lemken, Monosem), sans
   sauter les machines déjà en base, après vérification du `robots.txt`.
2. **Extraire** : transforme les specs brutes en colonnes techniques (largeur, puissance
   requise, poids, attelage, norme…), avec pour chaque valeur l'extrait source et une confiance.
3. **Rapport** : couverture des champs clés par marque, libellés non reconnus, valeurs écartées.
4. **Base de dev** (facultatif, `--ecrire`) : écrit dans `DATABASE_URL_DEV`, jamais dans `DATABASE_URL`.

## Installation

Placer le dossier `scraper_bis/` à la racine du dépôt `scraper-agriScan` (à côté de `scraper.py`), puis :

```bash
pip install -r requirements.txt
pip install openpyxl          # seulement pour --depuis-xlsx
playwright install chromium   # seulement pour la collecte en direct
```

Ajouter dans `.env` (jamais l'URL de production) :

```
DATABASE_URL_DEV=postgresql://…@…neon.tech/…   # branche Neon de dev
MISTRAL_API_KEY=…                              # seulement pour --llm
```

## Utilisation

```bash
# Tests de l'extraction (sans réseau ni base)
python -m scraper_bis.tests_extraction

# Test rapide : 2 catégories par marque, rapport seulement
python -m scraper_bis --max-categories 2

# Collecte complète Kuhn + Lemken + Monosem, puis écriture en base de dev
python -m scraper_bis --ecrire

# Rejouer l'extraction sans refaire la collecte (après avoir enrichi les règles)
python -m scraper_bis --depuis-json sortie/2026-10-15_113000/brut.json --ecrire

# Extraction sur un ancien export Excel (colonnes brand, name, variant, category, specs, source)
python -m scraper_bis --depuis-xlsx donnees-test/machines_extracted.xlsx

# Compléter les champs clés manquants avec Mistral (50 machines au plus)
python -m scraper_bis --depuis-json sortie/…/brut.json --llm --llm-max 50
```

Chaque exécution crée `sortie/AAAA-MM-JJ_HHMMSS/` :

| Fichier | Contenu |
| --- | --- |
| `rapport.md` | Couverture des champs clés par marque, doublons, valeurs écartées, libellés non reconnus, bilan d'écriture |
| `brut.json` | Fiches telles que collectées (rejouables avec `--depuis-json`) |
| `extrait.json` | Valeurs extraites, avec extrait source et confiance |
| `libelles_non_reconnus.csv` | Libellés à ajouter aux règles de `extraction.py`, triés par fréquence |

## Règles d'écriture en base de dev

- **Nouvelle machine** : créée « à vérifier », avec sa source (`MachineSource`) et la provenance de
  chaque valeur (`AttributProvenance`). Elle apparaît dans `/admin/fiches`.
- **Contenu inchangé** (même hash pour la même URL) : rien n'est écrit.
- **Contenu modifié** : nouvelle source. Une colonne est remplie seulement si la fiche n'est pas
  validée et que ce champ n'a pas été corrigé à la main. Sinon la valeur est seulement proposée
  (« Source : X — Utiliser » dans la relecture) et une fiche validée repasse « à vérifier ».
- **Enums** : les valeurs sont lues dans la base (majuscules ou minuscules, `AUTRE` présent ou non).
  Une catégorie sans famille reconnue est ignorée et signalée si `Famille.AUTRE` n'existe pas.
- **Même marque + nom + variante** dans une collecte : la gamme est ajoutée au nom quand elle
  diffère ; sinon la fiche la plus complète est gardée et le doublon signalé.
- Pas d'indexation Qdrant en dev.

## Ajouter une marque

Ajouter une entrée dans `MARQUES` (`sources.py`) : nom affiché, fonction de `scraper.py`,
constante des pages de catégories, méthode (`CRAWL_HTML` ou `EXTRACTION_PDF`).

## Enrichir l'extraction

Ouvrir `libelles_non_reconnus.csv`, ajouter les libellés utiles aux motifs de `REGLES`
(`extraction.py`), ajouter un cas dans `tests_extraction.py`, puis rejouer avec `--depuis-json`.
