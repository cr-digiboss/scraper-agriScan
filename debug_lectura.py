from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

URL = "https://www.lectura-specs.fr/fr/specification/machine-agricole/charrue"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # Test 1 : contexte normal
    ctx1 = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        locale="fr-FR",
    )
    p1 = ctx1.new_page()
    p1.goto(URL, wait_until="networkidle")
    time.sleep(3)
    p1.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(5)
    html1 = p1.content()
    soup1 = BeautifulSoup(html1, "html.parser")
    links1 = [a["href"] for a in soup1.find_all("a", href=True) if "modele" in a["href"]]
    print(f"Contexte 1 (frais) : {len(links1)} liens /modele/")
    ctx1.close()

    # Test 2 : réutiliser le même contexte après avoir visité d'autres pages
    ctx2 = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        locale="fr-FR",
    )
    p2 = ctx2.new_page()
    # Visiter d'abord la page principale (comme le scraper fait)
    p2.goto("https://www.lectura-specs.fr/fr/specification/machine-agricole", wait_until="networkidle")
    time.sleep(8)
    # Puis visiter la catégorie
    p2.goto(URL, wait_until="networkidle")
    time.sleep(3)
    p2.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(5)
    html2 = p2.content()
    soup2 = BeautifulSoup(html2, "html.parser")
    links2 = [a["href"] for a in soup2.find_all("a", href=True) if "modele" in a["href"]]
    print(f"Contexte 2 (après page principale) : {len(links2)} liens /modele/")
    
    # Afficher le titre pour voir si la page est bien chargée
    print(f"Titre : {soup2.title.string if soup2.title else 'aucun'}")
    print(f"Taille HTML : {len(html2)}")
    ctx2.close()
    
    browser.close()