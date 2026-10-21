import requests
import re

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

r = requests.get("https://www.mahindratractor.com/english-sitemap.xml", timeout=20, headers={"User-Agent": UA})
urls = re.findall(r"<loc>(.*?)</loc>", r.text)
print(f"{len(urls)} URLs au total")
# Affiche tout, pour reperer le bon pattern de slug produit
for u in sorted(urls):
    print(" ", u)
