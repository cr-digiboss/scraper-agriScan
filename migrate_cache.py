"""
Migration du cache machines_cache.json
Ancien format (marque/modele) → Nouveau format Prisma (brand/name)
Lance une seule fois : python migrate_cache.py
"""

import json, os

CACHE_FILE = "machines_cache.json"
BACKUP_FILE = "machines_cache_backup.json"

if not os.path.exists(CACHE_FILE):
    print("❌ Pas de cache trouvé")
    exit()

with open(CACHE_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"📋 {len(data)} machines à migrer")

# Backup
with open(BACKUP_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"💾 Backup sauvegardé : {BACKUP_FILE}")

migrated = []
for d in data:
    new = {
        "brand":       d.get("brand") or d.get("marque", ""),
        "range":       d.get("range", ""),
        "name":        d.get("name") or d.get("modele", ""),
        "variant":     d.get("variant", ""),
        "category":    d.get("category") or d.get("categorie", ""),
        "subcategory": d.get("subcategory", ""),
        "description": d.get("description", ""),
        "specs":       d.get("specs") or json.dumps({
            "puissance_cv": d.get("puissance_cv", ""),
            "annee":        d.get("annee", ""),
            "badge":        d.get("badge", ""),
        }, ensure_ascii=False),
        "imageUrl":    d.get("imageUrl") or d.get("image_url", ""),
        "videoUrl":    d.get("videoUrl", ""),
        "sourceUrl":   d.get("sourceUrl") or d.get("url_source", ""),
    }
    migrated.append(new)

with open(CACHE_FILE, "w", encoding="utf-8") as f:
    json.dump(migrated, f, ensure_ascii=False, indent=2)

print(f"✅ Migration terminée : {len(migrated)} machines")
print(f"   Lance maintenant : python export_excel.py → option 2")