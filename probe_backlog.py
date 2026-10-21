import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

for url in [
    "https://www.mahindratractor.com/sitemap.xml",
    "https://www.mahindratractor.com/sitemap",
]:
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": UA})
        print(f"{url} -> {r.status_code}, {len(r.content)} bytes")
        if r.status_code == 200:
            txt = r.text
            print(txt[:3000])
    except Exception as e:
        print(f"{url} -> ERREUR {e}")
