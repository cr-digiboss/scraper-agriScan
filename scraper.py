import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
"""
AgriScan Scraper — Point d'entrée principal
Lance tous les scrapers et génère l'Excel global.

Usage :
    python scraper.py              → scrape toutes les marques activées
    python export_excel.py         → scrape + génère l'Excel
"""

from playwright.sync_api import sync_playwright
from scrapers.base import Machine
from scrapers import tractordata
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("agriscan")

# ─────────────────────────────────────────────────────────────────────────────
# Active / désactive chaque marque ici
# ─────────────────────────────────────────────────────────────────────────────

SCRAPERS = [
    ("Tractordata", tractordata, True),   # ✅ validé
]


# ─────────────────────────────────────────────────────────────────────────────

CACHE_FILE = "urls_scrapees.json"
MACHINES_FILE = "machines_cache.json"

def _load_cache() -> set:
    """Charge les URLs déjà scrapées."""
    import json, os
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def _save_cache(urls: set):
    """Sauvegarde les URLs scrapées."""
    import json
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(urls), f, ensure_ascii=False, indent=2)
    log.info(f"💾 Cache URLs sauvegardé : {len(urls)} URLs")

def _load_machines_cache() -> list[Machine]:
    """Charge les machines déjà scrapées."""
    import json, os
    from dataclasses import fields
    if os.path.exists(MACHINES_FILE):
        with open(MACHINES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        machines = []
        for d in data:
            m = Machine()
            for k, v in d.items():
                if hasattr(m, k):
                    setattr(m, k, v)
            machines.append(m)
        log.info(f"📋 {len(machines)} machines chargées depuis le cache")
        return machines
    return []

def _save_machines_cache(machines: list[Machine]):
    """Sauvegarde toutes les machines dans le cache."""
    import json
    from dataclasses import asdict
    with open(MACHINES_FILE, "w", encoding="utf-8") as f:
        json.dump([asdict(m) for m in machines], f, ensure_ascii=False, indent=2)
    log.info(f"💾 Cache machines sauvegardé : {len(machines)} machines")

def run_all() -> list[Machine]:
    # Charger les machines déjà scrapées
    all_machines = _load_machines_cache()
    already_done = _load_cache()
    if already_done:
        log.info(f"⏭️  {len(already_done)} URLs déjà scrapées — seules les nouvelles seront visitées")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="fr-FR",
            extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"},
        )
        page = context.new_page()

        for name, module, enabled in SCRAPERS:
            if not enabled:
                log.info(f"⏭️  {name} — désactivé")
                continue
            try:
                results = module.scrape(page, already_done=already_done)
                all_machines.extend(results)
                # Ajouter les nouvelles URLs au cache
                for m in results:
                    if m.url_source:
                        already_done.add(m.url_source)
                log.info(f"✅ {name} : {len(results)} nouvelles machines")
            except Exception as e:
                log.error(f"❌ Échec {name} : {e}")

        browser.close()

    # Normaliser les catégories vers les catégories officielles AgriScan
    from scrapers.categories import normaliser_categorie
    for m in all_machines:
        if hasattr(m, "category"):
            m.category = normaliser_categorie(m.category)
        elif hasattr(m, "categorie"):
            m.category = normaliser_categorie(m.categorie)

    # Dédoublonner sur marque + modèle (garder la première occurrence)
    seen = set()
    deduped = []
    for m in all_machines:
        brand = getattr(m, 'brand', '') or getattr(m, 'marque', '') or ''
        name = getattr(m, 'name', '') or getattr(m, 'modele', '') or ''
        variant = getattr(m, 'variant', '') or ''
        key = f"{brand.lower().strip()}|{name.lower().strip()}|{variant.lower().strip()}"
        if key not in seen:
            seen.add(key)
            deduped.append(m)
    doublons = len(all_machines) - len(deduped)
    if doublons:
        log.info(f"🧹 {doublons} doublons supprimés → {len(deduped)} machines uniques")
    all_machines = deduped

    _save_cache(already_done)
    # Sauvegarder seulement si on a plus de machines que avant
    cached = _load_machines_cache()
    if len(all_machines) >= len(cached):
        _save_machines_cache(all_machines)
        nouvelles = len(all_machines) - len(cached)
        log.info(f"\n🎯 Total : {len(all_machines)} machines ({nouvelles} nouvelles)")
    else:
        log.warning(f"⚠️  Cache non écrasé")

    # Insérer directement dans Neon si DATABASE_URL disponible
    db_url = os.getenv("DATABASE_URL")
    if db_url and all_machines:
        # Charger les machines existantes depuis Neon pour éviter les doublons
        existing_neon = _load_existing_neon(db_url)
        if existing_neon:
            avant = len(all_machines)
            all_machines = [
                m for m in all_machines
                if f"{getattr(m, 'brand', '')}|{getattr(m, 'name', '')}|{getattr(m, 'variant', '')}" not in existing_neon
            ]
            log.info(f"🔍 {avant - len(all_machines)} machines déjà dans Neon ignorées → {len(all_machines)} nouvelles à insérer")
        _insert_neon(all_machines, db_url)

    return all_machines


def _load_existing_neon(db_url: str) -> set:
    """Charge les combinaisons brand+name+variant déjà dans Neon."""
    import psycopg2
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute('SELECT brand, name, variant FROM "Machine"')
        existing = {f"{r[0]}|{r[1]}|{r[2]}" for r in cursor.fetchall()}
        cursor.close()
        conn.close()
        log.info(f"📊 Neon : {len(existing)} machines existantes chargées")
        return existing
    except Exception as e:
        log.error(f"❌ Impossible de charger Neon : {e}")
        return set()

def _insert_neon(machines: list[Machine], db_url: str):
    """Insère les machines directement dans Neon avec ON CONFLICT."""
    import psycopg2
    from dataclasses import asdict

    INSERT_SQL = """
        INSERT INTO "Machine" (
            id, brand, range, name, variant,
            category, subcategory, description,
            specs, "imageUrl", "videoUrl", "sourceUrl", "createdAt"
        ) VALUES (
            gen_random_uuid()::text,
            %(brand)s, %(range)s, %(name)s, %(variant)s,
            %(category)s, %(subcategory)s, %(description)s,
            %(specs)s::jsonb, %(imageUrl)s, %(videoUrl)s, %(sourceUrl)s, NOW()
        )
        ON CONFLICT (brand, name, variant) DO UPDATE SET
            range       = EXCLUDED.range,
            category    = EXCLUDED.category,
            subcategory = EXCLUDED.subcategory,
            description = EXCLUDED.description,
            specs       = EXCLUDED.specs,
            "imageUrl"  = EXCLUDED."imageUrl",
            "sourceUrl" = EXCLUDED."sourceUrl"
    """

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        inseres = 0
        erreurs = 0

        for m in machines:
            try:
                import json as _json
                specs = m.specs or "{}"
                if isinstance(specs, dict):
                    specs = _json.dumps(specs, ensure_ascii=False)

                cursor.execute(INSERT_SQL, {
                    "brand":       (m.brand or "")[:255],
                    "range":       m.range or None,
                    "name":        (m.name or "")[:255],
                    "variant":     m.variant or "",
                    "category":    (m.category or "")[:255],
                    "subcategory": m.subcategory or None,
                    "description": m.description or None,
                    "specs":       specs,
                    "imageUrl":    m.imageUrl or None,
                    "videoUrl":    m.videoUrl or None,
                    "sourceUrl":   m.sourceUrl or None,
                })
                inseres += 1
            except Exception as e:
                conn.rollback()
                erreurs += 1

            if inseres % 100 == 0 and inseres > 0:
                conn.commit()
                log.info(f"  💾 Neon : {inseres} insérées, {erreurs} erreurs")

        conn.commit()
        cursor.close()
        conn.close()
        log.info(f"✅ Neon : {inseres} machines insérées/mises à jour, {erreurs} erreurs")

    except Exception as e:
        log.error(f"❌ Connexion Neon échouée : {e}")


if __name__ == "__main__":
    machines = run_all()
    print(f"\nRésultat : {len(machines)} machines collectées")