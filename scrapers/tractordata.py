"""
AgriScan — Scraper TractorData.com
Specs techniques complètes pour tracteurs agricoles.
"""

from playwright.sync_api import Page
from bs4 import BeautifulSoup
import re, json, logging, time, random, os
from .base import Machine, clean, extract_year, traduire_specs

log = logging.getLogger("agriscan")
BASE = "https://www.tractordata.com"

MARQUES = {
    # "John Deere":      f"{BASE}/farm-tractors/tractor-brands/johndeere/johndeere-tractors.html",
    "Massey Ferguson": f"{BASE}/farm-tractors/tractor-brands/massey-ferguson/massey-ferguson-tractors.html",
    "New Holland":     f"{BASE}/farm-tractors/tractor-brands/newholland/newholland-tractors.html",
    "Case IH":         f"{BASE}/farm-tractors/tractor-brands/caseih/caseih-tractors.html",
    "Kubota":          f"{BASE}/farm-tractors/tractor-brands/kubota/kubota-tractors.html",
    "Ford":            f"{BASE}/farm-tractors/tractor-brands/ford/ford-tractors.html",
    "Fendt":           f"{BASE}/farm-tractors/tractor-brands/fendt/fendt-tractors.html",
    "Claas":           f"{BASE}/farm-tractors/tractor-brands/claas/claas-tractors.html",
    "Deutz-Fahr":      f"{BASE}/farm-tractors/tractor-brands/deutz/deutz-tractors.html",
    "Allis-Chalmers":  f"{BASE}/farm-tractors/tractor-brands/allischalmers/allischalmers-tractors.html",
    "International":   f"{BASE}/farm-tractors/tractor-brands/ih/ih-tractors.html",
    "Fiat":            f"{BASE}/farm-tractors/tractor-brands/fiat/fiat-tractors.html",
    "Mahindra":        f"{BASE}/farm-tractors/tractor-brands/mahindra/mahindra-tractors.html",
}

ONGLETS = ["Engine", "Transmission", "Dimensions"]
ANNEE_ANCETRE = 1980
ANNEE_VINTAGE = 2000
CACHE_FILE = "urls_scrapees.json"

def _badge(annee: str) -> str:
    try:
        a = int(annee[:4]) if annee else 0
        if a and a < ANNEE_ANCETRE:
            return "Ancêtre"
        if a and a < ANNEE_VINTAGE:
            return "Vintage"
    except:
        pass
    return ""

def _save_urls_cache(urls: set):
    try:
        existing = set()
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                existing = set(json.load(f))
        existing.update(urls)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(list(existing), f, ensure_ascii=False)
        log.info(f"  💾 Cache URLs : {len(existing)} URLs sauvegardées")
    except Exception as e:
        log.warning(f"Erreur sauvegarde cache : {e}")

def _connect(db_url: str):
    import psycopg2
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    return conn, cursor

def _ensure_connection(conn, cursor, db_url: str):
    """Vérifie la connexion et reconnecte si nécessaire."""
    try:
        cursor.execute("SELECT 1")
        return conn, cursor
    except:
        log.info("  🔄 Reconnexion Neon...")
        try:
            conn.close()
        except:
            pass
        return _connect(db_url)

def _extraire_specs(page: Page) -> dict:
    specs = {}
    for onglet in ONGLETS:
        try:
            page.click(f"text={onglet}", timeout=3000)
            time.sleep(1.5)
            soup = BeautifulSoup(page.content(), "html.parser")
            for table in soup.find_all("table"):
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        k = clean(cells[0].get_text())
                        v = clean(cells[1].get_text())
                        if k and v and k != "x" and "x" not in k and len(k) > 2:
                            specs[k] = v
        except:
            pass
    return specs

def _extraire_puissance(specs: dict, text: str) -> str:
    for k, v in specs.items():
        if any(x in k.lower() for x in ["power", "hp", "pto", "engine"]):
            m = re.search(r"(\d+\.?\d*)\s*hp", v, re.I)
            if m:
                return str(round(float(m.group(1)) * 0.7355))
    m = re.search(r"(\d+\.?\d*)\s*hp", text, re.I)
    if m:
        return str(round(float(m.group(1)) * 0.7355))
    return ""

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
    ON CONFLICT (brand, name, variant) DO NOTHING
"""

def _insert_one(cursor, conn, m: Machine) -> bool:
    try:
        cursor.execute(INSERT_SQL, {
            "brand":       (m.brand or "")[:255],
            "range":       m.range or None,
            "name":        (m.name or "")[:255],
            "variant":     m.variant or "",
            "category":    (m.category or "")[:255],
            "subcategory": m.subcategory or None,
            "description": m.description or None,
            "specs":       m.specs or "{}",
            "imageUrl":    m.imageUrl or None,
            "videoUrl":    m.videoUrl or None,
            "sourceUrl":   m.sourceUrl or None,
        })
        conn.commit()
        return True
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        log.warning(f"    ❌ Erreur INSERT : {e}")
        return False

def scrape(page: Page, already_done: set = None) -> list[Machine]:
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    db_url = os.getenv("DATABASE_URL")

    # Connexion Neon
    existing_neon = set()
    conn = None
    cursor = None
    if db_url:
        try:
            conn, cursor = _connect(db_url)
            cursor.execute('SELECT brand, name, variant FROM "Machine"')
            existing_neon = {f"{r[0]}|{r[1]}|{r[2]}" for r in cursor.fetchall()}
            log.info(f"  📊 Neon : {len(existing_neon)} machines existantes")
        except Exception as e:
            log.error(f"  ❌ Connexion Neon : {e}")
            conn = None

    machines = []
    already_done = already_done or set()
    done = {u for u in already_done if "tractordata" in u}
    visited_this_session = set()
    log.info("🚜 TractorData — démarrage")

    for marque, liste_url in MARQUES.items():
        try:
            page.goto(liste_url, timeout=60000, wait_until="domcontentloaded")
            time.sleep(2)
        except Exception as e:
            log.warning(f"  ❌ {marque} : {e}")
            continue

        soup_liste = BeautifulSoup(page.content(), "html.parser")

        model_links = []
        for a in soup_liste.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("http"):
                href = BASE + href
            if "/farm-tractors/" in href and href.endswith(".html") and "tractor-brands" not in href:
                if href not in done and href not in visited_this_session:
                    model_links.append(href)

        log.info(f"  {marque} → {len(model_links)} nouveaux modèles")

        for i, url in enumerate(model_links, 1):
            # Reconnecter si nécessaire toutes les 100 machines
            if conn and db_url and i % 100 == 0:
                conn, cursor = _ensure_connection(conn, cursor, db_url)

            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                time.sleep(random.uniform(1.5, 2.5))
            except Exception as e:
                log.warning(f"    Erreur {url} → {e}")
                visited_this_session.add(url)
                continue

            soup_m = BeautifulSoup(page.content(), "html.parser")

            m = Machine()
            m.brand = marque
            m.category = "Tracteurs"
            m.sourceUrl = url
            m.imageUrl = ""

            h1 = soup_m.find("h1")
            if h1:
                titre = clean(h1.get_text())
                m.name = titre[len(marque):].strip() if titre.lower().startswith(marque.lower()) else titre

            if not m.name or len(m.name) < 2:
                visited_this_session.add(url)
                continue

            page_text = soup_m.get_text()
            annee = extract_year(page_text)
            m.variant = annee

            specs = _extraire_specs(page)
            cv = _extraire_puissance(specs, page_text)
            badge = _badge(annee)

            specs = traduire_specs(specs)
            specs["puissance_cv"] = cv
            specs["annee"] = annee
            specs["badge"] = badge
            m.specs = json.dumps(specs, ensure_ascii=False)

            neon_key = f"{m.brand}|{m.name}|{m.variant}"
            if neon_key in existing_neon:
                log.info(f"    [{i}] ⏭️  {m.name} ({annee}) déjà dans Neon")
                visited_this_session.add(url)
                continue

            if conn and cursor:
                inserted = _insert_one(cursor, conn, m)
                if inserted:
                    existing_neon.add(neon_key)
                    log.info(f"    [{i}] ✅ {m.name} {annee} {f'— {badge}' if badge else ''} → Neon")
            else:
                machines.append(m)
                log.info(f"    [{i}] ✓ {m.name} {annee}")

            visited_this_session.add(url)

            # Sauvegarder le cache toutes les 50 machines
            if i % 50 == 0:
                _save_urls_cache(visited_this_session)

        # Sauvegarder après chaque marque
        _save_urls_cache(visited_this_session)
        log.info(f"  ✅ {marque} terminé")

    if conn:
        try:
            cursor.close()
            conn.close()
        except:
            pass

    _save_urls_cache(visited_this_session)
    log.info(f"TractorData total : {len(machines)} machines (+ insertions directes Neon)")
    return machines