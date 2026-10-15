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

# Marques branchées sur le scraper bis : fonction de scraper.py, constante des
# pages de catégories (pour limiter le test et vérifier robots.txt), méthode.
MARQUES = {
    "kuhn": {"nom": "Kuhn", "fonction": "scrape_kuhn", "categories": "KUHN_CATEGORIES", "methode": "CRAWL_HTML"},
    "lemken": {"nom": "Lemken", "fonction": "scrape_lemken", "categories": "LEMKEN_CATEGORIES", "methode": "CRAWL_HTML"},
    "monosem": {"nom": "Monosem", "fonction": "scrape_monosem", "categories": "MONOSEM_CATEGORIES", "methode": "EXTRACTION_PDF"},
}

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


def collecter(cles: list[str], max_categories: int | None) -> tuple[list[FicheBrute], dict[str, dict]]:
    """Lance les scrapers existants (scraper.py) sans filtrer les machines déjà en base."""
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
            categories = getattr(scraper, conf["categories"])
            if max_categories:
                limitees = dict(list(categories.items())[:max_categories]) if isinstance(categories, dict) else categories[:max_categories]
                setattr(scraper, conf["categories"], limitees)
                categories = limitees
            urls = list(categories.values()) if isinstance(categories, dict) else list(categories)

            ok, motif = robots_autorise(urls)
            log.info(f"{nom} : {motif}")
            journal[nom] = {"robots": motif, "erreur": None, "fiches": 0, "duree_s": 0}
            if not ok:
                continue

            debut = time.time()
            page = contexte.new_page()
            try:
                machines = getattr(scraper, conf["fonction"])(page, set())
            except Exception as e:
                log.error(f"{nom} : échec de la collecte ({e})")
                journal[nom]["erreur"] = str(e)
                machines = []
            finally:
                page.close()
            for m in machines:
                try:
                    specs = json.loads(m.specs) if m.specs else {}
                except json.JSONDecodeError:
                    specs = {}
                fiches.append(FicheBrute(
                    marque=m.brand, nom=m.name, variante=m.variant or "", gamme=m.range or "",
                    categorie=m.category or "Autre", sous_categorie=m.subcategory or "",
                    description=m.description or "", specs={str(k): str(v) for k, v in specs.items()},
                    source_url=m.sourceUrl or "", methode=conf["methode"], image_url=m.imageUrl or "",
                    statut=m.statut or "active",
                ))
            journal[nom]["fiches"] = len(machines)
            journal[nom]["duree_s"] = round(time.time() - debut)
            time.sleep(random.uniform(1.0, 2.0))
        navigateur.close()
    return fiches, journal
