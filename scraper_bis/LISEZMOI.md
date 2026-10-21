# Scraper AgriScan (scraper bis)

Pipeline unique de collecte du catalogue, pour les 37 marques. Il réutilise les fonctions de
collecte de `scraper.py` et remplace son ancien enregistrement (`db.py`, `qdrant_sync.py`).

1. **Collecter** : vérifie le `robots.txt`, puis lance la fonction de la marque dans `scraper.py`.
   Avec `--ecrire`, seules les machines absentes de la base sont lues, comme l'ancien scraper de
   nuit. `--complet` relit tout le catalogue (specs modifiées, machines arrêtées).
2. **Extraire** : transforme les specs brutes en colonnes techniques (largeur, puissance requise,
   poids, attelage, norme…), avec pour chaque valeur l'extrait source et une confiance.
3. **Écrire** (`--ecrire`) : base de dev (`DATABASE_URL_DEV`) par défaut, production
   (`DATABASE_URL`) seulement avec `--prod`. Chaque marque est écrite dès qu'elle est collectée.
4. **Indexer** (`--qdrant`) : les machines créées ou modifiées sont indexées dans Qdrant pour
   l'assistant, au même format que l'ancien `qdrant_sync.py` (+ `machineId`).
5. **Rapport** : couverture des champs clés par marque, libellés non reconnus, valeurs écartées,
   bilan d'écriture.

Marques : `python -c "from scraper_bis.sources import MARQUES; print(*MARQUES)"`, ou `toutes`.

## Installation

Placer le dossier `scraper_bis/` à la racine du dépôt `scraper-agriScan` (à côté de `scraper.py`), puis :

```bash
pip install -r requirements.txt
pip install openpyxl          # seulement pour --depuis-xlsx
playwright install chromium   # seulement pour la collecte en direct
```

Ajouter dans `.env` :

```
DATABASE_URL_DEV=postgresql://…@…neon.tech/…   # branche Neon de dev
MISTRAL_API_KEY=…                              # --llm et --qdrant
# Production et Qdrant : seulement sur la machine qui fait tourner le scraper de nuit
# DATABASE_URL=…  QDRANT_URL=…  QDRANT_API_KEY=…  QDRANT_COLLECTION=…
```

## Utilisation

```bash
# Tests de l'extraction (sans réseau ni base)
python -m scraper_bis.tests_extraction

# Test rapide : 2 catégories par marque, rapport seulement
python -m scraper_bis --max-categories 2

# Nouveautés de Kuhn + Lemken + Monosem → base de dev
python -m scraper_bis --ecrire

# Tout le catalogue, toutes les marques → base de dev
python -m scraper_bis --marques toutes --ecrire --complet

# Scraper de nuit (GitHub Actions) : nouveautés → production + Qdrant ; le dimanche avec --complet
python -m scraper_bis --marques toutes --ecrire --prod --qdrant

# Réindexer tout le catalogue dans Qdrant (ancien backfill_qdrant.py)
python -m scraper_bis.indexation

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

## Règles d'écriture

- **Nouvelle machine** : créée « à vérifier », avec sa source (`MachineSource`) et la provenance de
  chaque valeur (`AttributProvenance`). Elle apparaît dans `/admin/fiches`.
- **Contenu inchangé** (même hash pour la même URL) : rien n'est écrit.
- **Contenu modifié** : nouvelle source. Une colonne est remplie seulement si la fiche n'est pas
  validée et que ce champ n'a pas été corrigé à la main. Sinon la valeur est seulement proposée
  (« Source : X — Utiliser » dans la relecture) et une fiche validée repasse « à vérifier ».
- **Statut, années, vidéo** suivent le site (une machine retirée passe « discontinued »). L'image
  n'est remplie que si la fiche n'en a pas : une image choisie dans l'admin n'est pas remplacée.
- **Catégorie** : sous-catégorie `parent__enfant` quand le site en donne une (comme le site et la
  migration v2) ; famille déduite des mots-clés, `AUTRE` sinon.
- **Enums** : les valeurs sont lues dans la base (majuscules ou minuscules).
- **Même marque + nom + variante** dans une collecte : la gamme est ajoutée au nom quand elle
  diffère ; sinon la fiche la plus complète est gardée et le doublon signalé.
- **Qdrant** : seulement avec `--qdrant` (la collection est celle de la production : ne pas
  l'utiliser avec la base de dev).

## Ajouter une marque

Écrire sa fonction `scrape_xxx(page, existing_keys)` dans `scraper.py`, puis ajouter une entrée
dans `MARQUES` (`sources.py`) : nom affiché, fonction, constante des pages d'entrée, et
`"methode": "EXTRACTION_PDF"` si les specs viennent de brochures PDF.

## Enrichir l'extraction

Ouvrir `libelles_non_reconnus.csv`, ajouter les libellés utiles aux motifs de `REGLES`
(`extraction.py`), ajouter un cas dans `tests_extraction.py`, puis rejouer avec `--depuis-json`.
