import requests
import re

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

r = requests.get("https://www.mahindratractor.com/english-sitemap.xml", timeout=20, headers={"User-Agent": UA})
print("status:", r.status_code, "bytes:", len(r.content))
urls = re.findall(r"<loc>(.*?)</loc>", r.text)
tractor_urls = sorted({u for u in urls if "/tractor/" in u})
print(f"{len(tractor_urls)} URLs /tractor/ trouvees sur {len(urls)} URLs au total")
for u in tractor_urls[:60]:
    print(" ", u)
