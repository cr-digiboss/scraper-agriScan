from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

URL = "https://www.tractordata.com/farm-tractors/000/0/3/35-john-deere-50.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    page = context.new_page()
    page.goto(URL, timeout=60000, wait_until="networkidle")
    time.sleep(3)
    
    # Cliquer sur chaque onglet et récupérer le contenu
    onglets = ["Engine", "Transmission", "Dimensions"]
    all_text = {}
    
    for onglet in onglets:
        try:
            page.click(f"text={onglet}", timeout=3000)
            time.sleep(2)
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            # Chercher les tables avec données
            for table in soup.find_all("table"):
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        k = cells[0].get_text(strip=True)
                        v = cells[1].get_text(strip=True)
                        if k and v and k != "×" and v != "×" and len(k) > 2:
                            all_text[k] = v
        except Exception as e:
            print(f"  Onglet {onglet} : {e}")
    
    browser.close()

print("=== SPECS TROUVÉES ===")
for k, v in all_text.items():
    print(f"  {k} : {v}")