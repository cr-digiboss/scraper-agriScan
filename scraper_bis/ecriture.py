"""Écriture dans la base de DEV (variable DATABASE_URL_DEV, jamais DATABASE_URL).

Règles :
- machine nouvelle → créée en « à vérifier », avec sa source et la provenance de chaque valeur ;
- contenu inchangé (même hash pour la même URL) → rien n'est écrit ;
- contenu modifié → nouvelle source ; une colonne n'est remplie que si la fiche n'est
  pas validée et que ce champ n'a jamais été validé à la main. Sinon la valeur est
  seulement proposée (AttributProvenance) et la fiche repasse « à vérifier ».
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from urllib.parse import urlparse

from .modele import FicheExtraite
from .normalisation import slug

log = logging.getLogger("scraper_bis")

COLONNES = [
    "typeAttelage", "culturesCompatibles", "largeurTravailMinM", "largeurTravailMaxM", "largeurTransportM",
    "hauteurTransportM", "longueurTransportM", "poidsVideKg", "ptacKg", "puissanceRequiseMinCh",
    "puissanceRequiseMaxCh", "categorieAttelage", "regimePdf", "distributeursDERequis", "distributeursSERequis",
    "debitHydrauliqueRequisLmin", "isobus", "fonctionsIsobus", "typesSolAdaptes", "penteMaxPct",
    "vitesseTravailMinKmh", "vitesseTravailMaxKmh", "debitChantierHaH", "homologueRoute", "vitesseMaxRouteKmh",
    "puissanceMoteurCh", "normeAntipollution",
]
CASTS = {"typeAttelage": '::"TypeAttelage"'}


def hote(url: str) -> str:
    return urlparse(url).hostname or "?"


def empreinte(f: FicheExtraite) -> str:
    b = f.brute
    contenu = {"nom": b.nom, "variante": b.variante, "gamme": b.gamme, "description": b.description, "specs": b.specs}
    return hashlib.sha256(json.dumps(contenu, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class EcritureDev:
    def __init__(self, url: str):
        import psycopg2

        self.conn = psycopg2.connect(url)
        self.enums = self._enums()
        self.constructeurs: dict[str, str] = {}
        self.categories: dict[str, str | None] = {}
        self.compteurs: Counter = Counter()
        self.categories_non_classees: Counter = Counter()

    def fermer(self):
        self.conn.close()

    # ── Enums : la base de dev peut avoir des valeurs en majuscules ou minuscules
    def _enums(self) -> dict[str, list[str]]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT t.typname, e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                "ORDER BY e.enumsortorder"
            )
            res: dict[str, list[str]] = {}
            for typ, lab in cur.fetchall():
                res.setdefault(typ, []).append(lab)
        return res

    def enum(self, typ: str, valeur: str) -> str | None:
        for lab in self.enums.get(typ, []):
            if lab.lower() == valeur.lower():
                return lab
        return None

    # ── Référentiels
    def constructeur(self, cur, nom: str) -> str:
        cle = nom.lower()
        if cle not in self.constructeurs:
            cur.execute('SELECT id FROM "Constructeur" WHERE lower(nom) = %s', (cle,))
            row = cur.fetchone()
            if not row:
                cur.execute(
                    'INSERT INTO "Constructeur" (id, nom) VALUES (gen_random_uuid()::text, %s) RETURNING id', (nom,)
                )
                row = cur.fetchone()
            self.constructeurs[cle] = row[0]
        return self.constructeurs[cle]

    def categorie(self, cur, nom: str, famille: str | None) -> str | None:
        code = slug(nom)
        if code not in self.categories:
            cur.execute('SELECT id FROM "Categorie" WHERE code = %s', (code,))
            row = cur.fetchone()
            if not row:
                fam = self.enum("Famille", famille or "AUTRE")
                if not fam:
                    self.categories[code] = None
                    return None
                cur.execute(
                    'INSERT INTO "Categorie" (id, code, famille, "nomFr", "nomNl") '
                    "VALUES (gen_random_uuid()::text, %s, %s::\"Famille\", %s, %s) RETURNING id",
                    (code, fam, nom, nom),
                )
                row = cur.fetchone()
            self.categories[code] = row[0]
        return self.categories[code]

    # ── Machine
    def ecrire(self, f: FicheExtraite) -> str:
        b = f.brute
        try:
            with self.conn.cursor() as cur:
                resultat = self._ecrire(cur, f)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            log.warning(f"Écriture impossible pour {b.cle()} : {e}")
            resultat = "erreur"
        self.compteurs[resultat] += 1
        return resultat

    def _ecrire(self, cur, f: FicheExtraite) -> str:
        b = f.brute
        categorie_id = self.categorie(cur, f.categorie_nom, f.famille)
        if not categorie_id:
            self.categories_non_classees[f.categorie_nom] += 1
            return "ignoree_categorie"
        constructeur_id = self.constructeur(cur, b.marque)
        hash_ = empreinte(f)
        statut = self.enum("StatutMachine", b.statut or "active") or self.enums["StatutMachine"][0]
        a_verifier = self.enum("StatutValidation", "A_VERIFIER")
        valide = self.enum("StatutValidation", "VALIDE")
        methode = self.enum("MethodeCollecte", b.methode) or self.enum("MethodeCollecte", "CRAWL_HTML")

        cur.execute(
            'SELECT id, "statutValidation" FROM "Machine" WHERE "constructeurId" = %s AND name = %s AND variant = %s',
            (constructeur_id, b.nom, b.variante or ""),
        )
        row = cur.fetchone()
        nouvelle = row is None
        if nouvelle:
            cur.execute(
                'INSERT INTO "Machine" (id, "constructeurId", "categorieId", name, variant, range, description, '
                '"imageUrl", "sourceUrl", specs, statut, "statutValidation", "createdAt", "updatedAt") '
                "VALUES (gen_random_uuid()::text, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, "
                '%s::"StatutMachine", %s::"StatutValidation", now(), now()) RETURNING id, "statutValidation"',
                (constructeur_id, categorie_id, b.nom, b.variante or "", b.gamme or None, b.description or None,
                 b.image_url or None, b.source_url or None, json.dumps(b.specs, ensure_ascii=False), statut, a_verifier),
            )
            row = cur.fetchone()
        machine_id, statut_validation = row

        if not nouvelle:
            cur.execute(
                'SELECT "contenuHash" FROM "MachineSource" WHERE "machineId" = %s AND url = %s '
                'ORDER BY "collecteAt" DESC LIMIT 1',
                (machine_id, b.source_url or ""),
            )
            precedent = cur.fetchone()
            if precedent and precedent[0] == hash_:
                return "inchangee"

        cur.execute(
            'INSERT INTO "MachineSource" (id, "machineId", url, methode, "contenuHash") '
            'VALUES (gen_random_uuid()::text, %s, %s, %s::"MethodeCollecte", %s) RETURNING id',
            (machine_id, b.source_url or "", methode, hash_),
        )
        source_id = cur.fetchone()[0]

        cur.execute(
            'SELECT DISTINCT champ FROM "AttributProvenance" WHERE "machineId" = %s AND statut = %s::"StatutValidation" '
            'AND "sourceId" IS NULL',
            (machine_id, valide),
        )
        valides_a_la_main = {r[0] for r in cur.fetchall()}
        cur.execute(
            "SELECT " + ", ".join(f'"{c}"' for c in COLONNES) + ' FROM "Machine" WHERE id = %s', (machine_id,)
        )
        actuelles = dict(zip(COLONNES, cur.fetchone()))

        a_ecrire: dict[str, object] = {}
        a_revoir = False
        for p in f.propositions:
            if p.champ not in COLONNES:
                continue
            valeur = p.valeur
            if p.champ == "typeAttelage":
                valeur = self.enum("TypeAttelage", str(valeur))
                if not valeur:
                    continue
            cur.execute(
                'INSERT INTO "AttributProvenance" (id, "machineId", "sourceId", champ, valeur, extrait, confiance, statut) '
                'VALUES (gen_random_uuid()::text, %s, %s, %s, %s::jsonb, %s, %s, %s::"StatutValidation")',
                (machine_id, source_id, p.champ, json.dumps(valeur), p.extrait, p.confiance, a_verifier),
            )
            actuelle = actuelles.get(p.champ)
            identique = actuelle is not None and str(actuelle) == str(valeur) or (
                isinstance(actuelle, (int, float)) and isinstance(valeur, (int, float)) and abs(actuelle - valeur) < 1e-6
            )
            if identique:
                continue
            modifiable = statut_validation != valide and p.champ not in valides_a_la_main
            if modifiable:
                a_ecrire[p.champ] = valeur
                self.compteurs["colonnes_ecrites"] += 1
            else:
                a_revoir = True
                self.compteurs["valeurs_proposees"] += 1

        sets = ['specs = %s::jsonb', 'range = %s', 'description = COALESCE(%s, description)',
                '"sourceUrl" = COALESCE(%s, "sourceUrl")', '"updatedAt" = now()']
        params: list[object] = [json.dumps(b.specs, ensure_ascii=False), b.gamme or None, b.description or None,
                                b.source_url or None]
        for champ, valeur in a_ecrire.items():
            sets.append(f'"{champ}" = %s{CASTS.get(champ, "")}')
            params.append(valeur)
        if a_revoir and statut_validation == valide:
            sets.append('"statutValidation" = %s::"StatutValidation"')
            params.append(a_verifier)
        cur.execute(f'UPDATE "Machine" SET {", ".join(sets)} WHERE id = %s', (*params, machine_id))
        return "creee" if nouvelle else "mise_a_jour"
