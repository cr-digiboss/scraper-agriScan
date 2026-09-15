"""
AgriScan — Mapping des catégories
Aligne toutes les sources sur les catégories officielles de la plateforme.
"""

# Catégories officielles AgriScan (chat + catalogue)
AGRISCAN_CATEGORIES = {
    # Tracteurs
    "tracteur": "Tracteurs",
    "tracteurs": "Tracteurs",
    "tracteur-compact": "Tracteurs",
    "tracteurs compacts": "Tracteurs",

    # Moissonneuses
    "moissonneuse-batteuse": "Moissonneuses",
    "moissonneuses-batteuses": "Moissonneuses",
    "moissonneuse-batteuse-occasion": "Moissonneuses",
    "moissonneuses": "Moissonneuses",

    # Ensileuses
    "ensileuse": "Ensileuses",
    "ensileuse-automotrice": "Ensileuses",
    "ensileuses": "Ensileuses",

    # Matériels de récolte
    "arracheuse-betteraves": "Matériels de récolte",
    "arracheuse-de-pommes-de-terre": "Matériels de récolte",
    "moissoneuse-de-pomme-de-terre": "Matériels de récolte",
    "recolteurs-de-pois": "Matériels de récolte",
    "barre-de-coupe-pour-moissonneuse-batteuse": "Matériels de récolte",
    "materiel de recolte": "Matériels de récolte",

    # Semoirs
    "semoir": "Semoirs",
    "semoirs": "Semoirs",
    "semoir-combine": "Semoirs",
    "semoir-precision": "Semoirs",
    "semoir-engrais": "Semoirs",
    "semoir-planteuse": "Semoirs",
    "autre-semoir": "Semoirs",
    "semis": "Semoirs",
    "semis et fertilisation": "Semoirs",
    "strip-till": "Semoirs",

    # Pulvérisateurs
    "pulverisateur": "Pulvérisateurs",
    "pulvérisateurs": "Pulvérisateurs",
    "pulve": "Pulvérisateurs",
    "pulverisateurs-portes": "Pulvérisateurs",
    "pulverisateurs-traines": "Pulvérisateurs",
    "pulverisateurs-automoteurs": "Pulvérisateurs",
    "pulverisateur-vigne": "Pulvérisateurs",
    "technique de protection phytosanitaire": "Pulvérisateurs",

    # Charrues
    "charrue": "Charrues",
    "charrue-a-dents": "Charrues",
    "charrue-non-reversible": "Charrues",

    # Déchaumeurs
    "cultivateur-dechaumeur": "Déchaumeurs",
    "dechaumeurs-a-disques": "Déchaumeurs",
    "cultivateurs-a-dents": "Déchaumeurs",

    # Travail du sol
    "herse": "Travail du sol",
    "herse-combinee": "Travail du sol",
    "herse-rotative": "Travail du sol",
    "vibroculteur": "Travail du sol",
    "decompacteur-sarcleur": "Travail du sol",
    "outils-preparation-sol": "Travail du sol",
    "autres-outils-preparation-sol": "Travail du sol",
    "rouleau": "Travail du sol",
    "travail du sol": "Travail du sol",
    "fissuration": "Travail du sol",
    "travail de surface": "Travail du sol",

    # Épandeurs
    "epandeur": "Épandeurs",
    "epandeur-fumier": "Épandeurs",
    "epandeurs-d-engrais-liquide": "Épandeurs",
    "tonne-lisier": "Épandeurs",
    "autres-materiels-fertilisation": "Épandeurs",
    "fertilisation": "Épandeurs",
    "fertilisation localisée": "Épandeurs",
    "epandeurs portes": "Épandeurs",
    "epandeurs traines": "Épandeurs",

    # Presses
    "presse-balles-rondes": "Presses",
    "presse-cubique": "Presses",
    "enrubanneuse": "Presses",
    "presses": "Presses",

    # Fenaison
    "faucheuse": "Fenaison",
    "faucheuse-conditionneuse": "Fenaison",
    "faucheuse-andaineuse-automotrice": "Fenaison",
    "faucheuses-conditionneuses": "Fenaison",
    "andaineur": "Fenaison",
    "rateau-faneur": "Fenaison",
    "materiel-fenaison": "Fenaison",
    "autres-materiels-fenaison": "Fenaison",
    "materiel de fenaison": "Fenaison",

    # Bineuses
    "bineuse": "Bineuses",
    "bineuses-schmotzer": "Bineuses",
    "desherbage": "Bineuses",
    "butteuses": "Bineuses",
    "bineuse-venterra-1k": "Bineuses",

    # Broyeurs
    "tarup-broyeur": "Broyeurs",
    "broyeurs": "Broyeurs",

    # Chargeurs
    "chargeur-frontal-fourche": "Chargeurs",
    "chargeuse-multifonction": "Chargeurs",
    "chargeurs frontaux": "Chargeurs",
    "chargeur frontal": "Chargeurs",

    # Télescopiques
    "telescopique": "Télescopiques",
    "télescopiques": "Télescopiques",

    # Remorques agricoles
    "remorque": "Remorques agricoles",
    "remorque-auto-chargeuse": "Remorques agricoles",
    "benne-cerealiere": "Remorques agricoles",
    "remorque-multi-usage": "Remorques agricoles",
    "transbordeur": "Remorques agricoles",

    # Élevage & stabulation
    "materiel-elevage": "Élevage & stabulation",
    "salle-de-traite": "Élevage & stabulation",
    "tank-a-lait": "Élevage & stabulation",
    "melangeuse": "Élevage & stabulation",
    "desileuse": "Élevage & stabulation",
    "bac-ratelier": "Élevage & stabulation",
    "autres-materiels-elevage": "Élevage & stabulation",
    "elevage & stabulation": "Élevage & stabulation",

    # Vendange
    "machine-vendanger": "Vendange",
    "materiel-viticole": "Vendange",
    "autre-materiel-viticole": "Vendange",
    "travail-sol-viticole": "Vendange",
    "viticulture": "Vendange",
    "gamme vigne": "Vendange",

    # Cultures spécialisées
    "planteuse": "Cultures spécialisées",
    "planteurs-de-pommes-de-terre": "Cultures spécialisées",
    "materiel-pomme-de-terre": "Cultures spécialisées",

    # Stockage & séchage
    "sechoir-grains": "Stockage & séchage",
    "materiel-stockage-conditionnement": "Stockage & séchage",
    "stockage-conditionnement-autres": "Stockage & séchage",
    "tremies-et-silos": "Stockage & séchage",
    "vis-sans-fin": "Stockage & séchage",
    "souffleur-grains": "Stockage & séchage",

    # Matériel d'irrigation
    "arroseur-enrouleur": "Matériel d'irrigation",
    "irrigation": "Matériel d'irrigation",
    "pompes-d-irrigation": "Matériel d'irrigation",

    # Matériel de cour de ferme
    "entretien espaces verts": "Matériel de cour de ferme",
    "entretien-des-espaces-verts": "Matériel de cour de ferme",

    # Déneigement
    "chasse-neige": "Déneigement",
    "sableuse-saleuse": "Déneigement",
    "souffleuse-neige": "Déneigement",

    # Autre
    "agriculture---autres": "Autre",
    "autres-materiels": "Autre",
    "autres materiels": "Autre",
}


def normaliser_categorie(cat: str) -> str:
    """Normalise une catégorie vers les catégories officielles AgriScan."""
    cat_lower = cat.lower().strip()
    # Cherche correspondance exacte
    if cat_lower in AGRISCAN_CATEGORIES:
        return AGRISCAN_CATEGORIES[cat_lower]
    # Cherche correspondance partielle
    for key, val in AGRISCAN_CATEGORIES.items():
        if key in cat_lower or cat_lower in key:
            return val
    # Retourner tel quel si pas de correspondance
    return cat