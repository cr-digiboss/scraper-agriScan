"""Lecture des fiches brutes : collecte en direct, fichier Excel ou JSON d'une collecte précédente."""

from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from .modele import FicheBrute

log = logging.getLogger("scraper_bis")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Les 37 marques collectées : fonction de scraper.py, constante de ses pages
# d'entrée (catégories ou accueil : sert à vérifier robots.txt et à limiter un
# test avec --max-categories), méthode de collecte. Même ordre que l'ancien
# scraper de nuit.
MARQUES = {
    "kverneland": {"nom": "Kverneland", "fonction": "scrape_kverneland", "categories": "KVERNELAND_HOME"},
    "claas": {"nom": "Claas", "fonction": "scrape_claas", "categories": "CLAAS_TRACTEURS_URL"},
    "fendt": {"nom": "Fendt", "fonction": "scrape_fendt", "categories": "FENDT_HOME"},
    "massey-ferguson": {"nom": "Massey Ferguson", "fonction": "scrape_massey_ferguson", "categories": "MF_HOME"},
    "new-holland": {"nom": "New Holland", "fonction": "scrape_new_holland", "categories": "NEW_HOLLAND_CATEGORIES"},
    "case-ih": {"nom": "Case IH", "fonction": "scrape_case_ih", "categories": "CASEIH_CATEGORIES"},
    "monosem": {"nom": "Monosem", "fonction": "scrape_monosem", "categories": "MONOSEM_CATEGORIES", "methode": "EXTRACTION_PDF"},
    "same": {"nom": "Same", "fonction": "scrape_same", "categories": "SDF_SITES", "methode": "EXTRACTION_PDF"},
    "avr": {"nom": "AVR", "fonction": "scrape_avr", "categories": "AVR_CATEGORIES"},
    "mchale": {"nom": "McHale", "fonction": "scrape_mchale", "categories": "MCHALE_HOME"},
    "kemper": {"nom": "Kemper", "fonction": "scrape_kemper", "categories": "KEMPER_HOME"},
    "pottinger": {"nom": "Pöttinger", "fonction": "scrape_pottinger", "categories": "POTTINGER_CATEGORIES"},
    "grimme": {"nom": "Grimme", "fonction": "scrape_grimme", "categories": "GRIMME_HOME"},
    "vaderstad": {"nom": "Väderstad", "fonction": "scrape_vaderstad", "categories": "VADERSTAD_HOME"},
    "lemken": {"nom": "Lemken", "fonction": "scrape_lemken", "categories": "LEMKEN_CATEGORIES"},
    "kuhn": {"nom": "Kuhn", "fonction": "scrape_kuhn", "categories": "KUHN_CATEGORIES"},
    "jcb": {"nom": "JCB", "fonction": "scrape_jcb", "categories": "JCB_CATEGORIES"},
    "valtra": {"nom": "Valtra", "fonction": "scrape_valtra", "categories": "VALTRA_SERIES"},
    "john-deere": {"nom": "John Deere", "fonction": "scrape_johndeere", "categories": "JOHNDEERE_CATEGORIES"},
    "kubota": {"nom": "Kubota", "fonction": "scrape_kubota", "categories": "KUBOTA_CATEGORIES"},
    "krone": {"nom": "Krone", "fonction": "scrape_krone", "categories": "KRONE_CATALOGUE_URL"},
    "guttler": {"nom": "Güttler", "fonction": "scrape_guttler", "categories": "GUTTLER_SITEMAP_URL"},
    "actisol": {"nom": "Actisol", "fonction": "scrape_actisol", "categories": "ACTISOL_CATEGORIES"},
    "mccormick": {"nom": "McCormick", "fonction": "scrape_mccormick", "categories": "MCCORMICK_CATALOGUE_URL"},
    "franquet": {"nom": "Franquet", "fonction": "scrape_franquet", "categories": "FRANQUET_CATEGORIES"},
    "vicon": {"nom": "Vicon", "fonction": "scrape_vicon", "categories": "VICON_HOME"},
    "horsch": {"nom": "Horsch", "fonction": "scrape_horsch", "categories": "HORSCH_HOME"},
    "sulky": {"nom": "Sulky", "fonction": "scrape_sulky", "categories": "SULKY_HOME"},
    "hardi": {"nom": "Hardi", "fonction": "scrape_hardi", "categories": "HARDI_HOME"},
    "berthoud": {"nom": "Berthoud", "fonction": "scrape_berthoud", "categories": "BERTHOUD_GAMME_URL"},
    "ropa": {"nom": "Ropa", "fonction": "scrape_ropa", "categories": "ROPA_HOME"},
    "samson": {"nom": "Samson", "fonction": "scrape_samson", "categories": "SAMSON_HOME"},
    "bogballe": {"nom": "Bogballe", "fonction": "scrape_bogballe", "categories": "BOGBALLE_MODELES_URL"},
    "niubo": {"nom": "Niubo", "fonction": "scrape_niubo", "categories": "NIUBO_CATEGORIES"},
    "agrisem": {"nom": "Agrisem", "fonction": "scrape_agrisem", "categories": "AGRISEM_HOME"},
    "einboeck": {"nom": "Einböck", "fonction": "scrape_einboeck", "categories": "EINBOECK_HOME", "methode": "EXTRACTION_PDF"},
    "rauch": {"nom": "Rauch", "fonction": "scrape_rauch", "categories": "RAUCH_CATEGORIES"},
}


def resoudre_marques(texte: str) -> tuple[list[str], list[str]]:
    """« toutes » ou « Kuhn, Massey Ferguson, pöttinger » → (clés connues, inconnues)."""
    import unicodedata

    def cle(x: str) -> str:
        x = "".join(c for c in unicodedata.normalize("NFD", x) if unicodedata.category(c) != "Mn")
        return "-".join(x.lower().replace("_", " ").split())

    demandees = [cle(m) for m in (texte or "").split(",") if m.strip()]
    if demandees in ([], ["toutes"], ["tout"], ["all"]):
        return list(MARQUES), []
    alias = {cle(c["nom"]): k for k, c in MARQUES.items()} | {k: k for k in MARQUES} | {k.replace("-", ""): k for k in MARQUES}
    connues = [alias[m] for m in demandees if m in alias]
    return list(dict.fromkeys(connues)), [m for m in demandees if m not in alias]


def _pages_categories(categories) -> list[tuple[str, str]]:
    """(nom de catégorie, URL) quelle que soit la forme de la constante de scraper.py :
    {nom: url}, {url: nom}, [url…] ou une seule URL d'accueil."""
    if isinstance(categories, str):
        return [("", categories)]
    if isinstance(categories, dict):
        return [(v, k) if str(k).startswith("http") else (k, v) for k, v in categories.items()]
    return [("", u) for u in categories]


NOMS_MARQUES = {
    "kuhn": "Kuhn", "lemken": "Lemken", "monosem": "Monosem", "new holland": "New Holland", "case ih": "Case IH",
    "john deere": "John Deere", "massey ferguson": "Massey Ferguson", "deutz fahr": "Deutz-Fahr",
    "mc cormick": "McCormick", "mchale": "McHale", "poettinger": "Pöttinger", "einboeck": "Einböck",
}


def nom_marque(brut: str) -> str:
    cle = (brut or "").strip().lower()
    return NOMS_MARQUES.get(cle) or " ".join(m[:1].upper() + m[1:] for m in cle.split())


def _specs_texte(texte: str) -> dict[str, str]:
    """« Largeur: 3m | Poids: 5220kg » → dict."""
    specs = {}
    for part in (texte or "").split(" | "):
        if ":" in part:
            k, v = part.split(":", 1)
            if k.strip():
                specs[k.strip()] = v.strip()
    return specs


def depuis_xlsx(chemin: str, marques: set[str] | None) -> list[FicheBrute]:
    import openpyxl

    ws = openpyxl.load_workbook(chemin, read_only=True).worksheets[0]
    lignes = ws.iter_rows(values_only=True)
    entete = [str(c) for c in next(lignes)]
    fiches = []
    for ligne in lignes:
        d = dict(zip(entete, ligne))
        if marques and str(d.get("brand", "")).lower() not in marques:
            continue
        source = str(d.get("source") or "")
        fiches.append(FicheBrute(
            marque=nom_marque(str(d.get("brand") or "")),
            nom=str(d.get("name") or "").strip(),
            variante=str(d.get("variant") or "").strip(),
            gamme=str(d.get("range") or "").strip(),
            categorie=str(d.get("category") or "autre"),
            sous_categorie=str(d.get("subcategory") or ""),
            description=str(d.get("description") or ""),
            specs=_specs_texte(str(d.get("specs") or "")),
            source_url=source if source.startswith("http") else f"fichier:{source.replace(chr(92), '/')}",
            methode="EXTRACTION_PDF" if source.lower().endswith(".pdf") else "CRAWL_HTML",
        ))
    return fiches


def depuis_json(chemin: str) -> list[FicheBrute]:
    return [FicheBrute(**d) for d in json.loads(Path(chemin).read_text(encoding="utf-8"))]


# ── Collecte en direct ───────────────────────────────────────────────────────


def robots_autorise(urls: list[str]) -> tuple[bool, str]:
    """Vérifie robots.txt du site pour les pages de catégories."""
    import requests

    if not urls:
        return True, "aucune URL à vérifier"
    u = urlparse(urls[0])
    robots_url = f"{u.scheme}://{u.netloc}/robots.txt"
    try:
        r = requests.get(robots_url, timeout=15, headers={"User-Agent": UA})
    except Exception as e:  # réseau
        return True, f"robots.txt inaccessible ({e}), collecte poursuivie"
    if r.status_code >= 400:
        return True, f"pas de robots.txt (HTTP {r.status_code})"
    rp = RobotFileParser()
    rp.parse(r.text.splitlines())
    refusees = [x for x in urls if not rp.can_fetch("*", x)]
    if refusees:
        return False, f"robots.txt interdit : {', '.join(refusees[:3])}"
    return True, "robots.txt : autorisé"


def collecter(
    cles: list[str], max_categories: int | None, existantes: set[str] | None = None, apres_marque=None
) -> tuple[list[FicheBrute], dict[str, dict]]:
    """Lance les fonctions de collecte de scraper.py.

    existantes : clés « marque|nom|variante » déjà en base. Comme l'ancien scraper de
    nuit, les fonctions sautent alors ces machines (collecte rapide des nouveautés).
    Vide → toutes les fiches sont relues (collecte complète).
    apres_marque(nom, fiches) : appelé après chaque marque (écriture au fil de l'eau,
    pour ne rien perdre si l'exécution est interrompue).
    """
    import scraper  # import tardif : playwright, pdfplumber… ne sont utiles qu'ici
    from playwright.sync_api import sync_playwright

    fiches: list[FicheBrute] = []
    journal: dict[str, dict] = {}
    with sync_playwright() as p:
        navigateur = p.chromium.launch(headless=True)
        contexte = navigateur.new_context(user_agent=UA, viewport={"width": 1280, "height": 800}, locale="fr-FR")
        for cle in cles:
            conf = MARQUES[cle]
            nom = conf["nom"]
            methode = conf.get("methode", "CRAWL_HTML")
            categories = getattr(scraper, conf["categories"])
            if max_categories and not isinstance(categories, str):
                limitees = dict(list(categories.items())[:max_categories]) if isinstance(categories, dict) else categories[:max_categories]
                setattr(scraper, conf["categories"], limitees)
                categories = limitees
            pages = _pages_categories(categories)
            urls = [u for _, u in pages if str(u).startswith("http")]

            ok, motif = robots_autorise(urls)
            log.info(f"{nom} : {motif}")
            journal[nom] = {"robots": motif, "erreur": None, "fiches": 0, "duree_s": 0}
            if not ok:
                continue

            debut = time.time()
            # Une page par marque : une redirection tardive d'un site ne doit pas
            # interrompre la marque suivante (cf. ancien scraper de nuit).
            page = contexte.new_page()
            try:
                machines = getattr(scraper, conf["fonction"])(page, set(existantes or ()))
            except Exception as e:
                log.error(f"{nom} : échec de la collecte ({e})")
                journal[nom]["erreur"] = str(e)
                machines = []
            finally:
                page.close()
            # normaliser_categorie() de scraper.py range certaines catégories explicites en
            # « Autre » (« Travail du sol », « Semis »…) : on reprend alors le nom de la
            # catégorie du site dont l'URL contient la fiche.
            pages_nommees = [(n, u) for n, u in pages if n and str(u).startswith("http")]
            for m in machines:
                if (m.category or "Autre") == "Autre" and m.sourceUrl:
                    chemin = urlparse(m.sourceUrl).path
                    for nom_cat, url_cat in pages_nommees:
                        if chemin.startswith(urlparse(url_cat).path.rstrip("/") + "/"):
                            m.category = nom_cat
                            break
                try:
                    specs = json.loads(m.specs) if m.specs else {}
                except json.JSONDecodeError:
                    specs = {}
                fiches.append(FicheBrute(
                    marque=m.brand, nom=m.name, variante=m.variant or "", gamme=m.range or "",
                    categorie=m.category or "Autre", sous_categorie=m.subcategory or "",
                    description=m.description or "", specs={str(k): str(v) for k, v in specs.items()},
                    source_url=m.sourceUrl or "", methode=methode, image_url=m.imageUrl or "",
                    video_url=m.videoUrl or "", statut=m.statut or "active",
                    annee_debut=str(m.anneeDebut or ""), annee_fin=str(m.anneeFin or ""),
                ))
            if apres_marque and machines:
                try:
                    apres_marque(nom, fiches[len(fiches) - len(machines):])
                except Exception as e:
                    log.error(f"{nom} : échec de l'écriture ({e})")
                    journal[nom]["erreur"] = f"écriture : {e}"
            journal[nom]["fiches"] = len(machines)
            journal[nom]["duree_s"] = round(time.time() - debut)
            log.info(f"{nom} : {len(machines)} fiches en {journal[nom]['duree_s']} s")
            time.sleep(random.uniform(1.0, 2.0))
        navigateur.close()
    return fiches, journal
