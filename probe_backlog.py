import requests
import re

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

for url in [
    "https://www.landini.it/sitemap.xml",
    "https://www.landini.it/sitemap_index.xml",
    "https://landini.it/sitemap.xml",
    "https://landini.it/wp-sitemap.xml",
]:
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": UA})
        print(f"{url} -> {r.status_code}, {len(r.content)} bytes")
        if r.status_code == 200:
            print(r.text[:1500])
    except Exception as e:
        print(f"{url} -> ERREUR {e}")
    print()
