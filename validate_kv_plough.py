from playwright.sync_api import sync_playwright
import scraper

TEST_URLS = [
    # transposee, 1 seul modele repete en colonnes (regression precedente)
    "https://ien.kverneland.com/seeders/pneumatic-precision-drills/optima-r",
    # transposee, modeles distincts en colonnes
    "https://ien.kverneland.com/tillage-tools/rollers/kverneland-actiroll",
    # une ligne par modele (3 vrais modeles)
    "https://ien.kverneland.com/bale-choppers/mixer-feeders/siloking-trailedline-classic-compact",
    # NOUVEAU cas bug : charrues transposees avec peu de lignes d'attributs
    "https://ien.kverneland.com/ploughs/reversible-ploughs/kverneland-2300-s",
    "https://ien.kverneland.com/ploughs/reversible-ploughs/kverneland-2501-s-variomat",
    "https://ien.kverneland.com/ploughs/reversible-ploughs/kverneland-3300-s",
    "https://ien.kverneland.com/ploughs/reversible-ploughs/kverneland-6300-s-variomat",
    "https://ien.kverneland.com/tillage-tools/universal-cultivators/kverneland-turbo",
    "https://ien.kverneland.com/weeders/inter-row-cultivators/kverneland-onyx-2000-f",
]

scraper._kverneland_product_links = lambda page: set(TEST_URLS)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    machines = scraper.scrape_kverneland(page, existing_keys=set())
    browser.close()

print(f"{len(machines)} machines produites au total")
for m in machines:
    print(f"- [{m.sourceUrl.split('/')[-1]}] {m.name!r} specs={m.specs[:120]}")
