"""Tests de l'extraction (sans réseau ni base) : python -m scraper_bis.tests_extraction"""

from .extraction import dedoublonner, extraire, separer_variantes
from .modele import FicheBrute
from .unites import valeurs

CAS_UNITES = [
    ("180-320ch", "puissance", None, [180, 320]),
    ("90-175 kW / 120-240 Ch", "puissance", None, [120, 240]),
    ("107 kW / 150 ch", "puissance", None, [150]),
    ("129 kW", "puissance", None, [175.39]),
    ("3.00m - 4.00m - 5.00m", "longueur", None, [3, 4, 5]),
    ("2,9-3,5m", "longueur", None, [2.9, 3.5]),
    ("5357-5797 mm", "longueur", None, [5.357, 5.797]),
    ("13,6 t", "masse", None, [13600]),
    ("~8 tonnes", "masse", None, [8000]),
    ("jusqu'à 8800 kg", "masse", None, [8800]),
    ("3950", "masse", "kg", [3950]),
    ("121 (89)", "puissance", "ch", [121]),
    ("650 l à 1 730 l", "volume", None, [650, 1730]),
    ("8 m³", "longueur", None, []),
    ("110 l/min (load sensing)", "debit", None, [110]),
    ("6-12 km/h", "vitesse", None, [6, 12]),
    ("9'1\" (2.7 m)", "longueur", None, [2.7]),
]


def verifier_unites():
    for texte, dim, defaut, attendu in CAS_UNITES:
        obtenu = valeurs(texte, dim, defaut)
        assert [round(x, 2) for x in obtenu] == [round(x, 2) for x in attendu], (texte, obtenu, attendu)


def verifier_extraction():
    outil = extraire(FicheBrute(
        marque="Agrisem", nom="Rouleau T-Sem", categorie="déchaumeur", variante="Porté 3m",
        specs={"Largeur de travail": "3.00m", "Largeur de transport": "3.00m",
               "Puissance mini/maxi": "180-320ch", "Poids": "5220kg", "Type": "Porté fixe",
               "Attelage": "Cat. 3", "Nombre de disques": "17"},
    ))
    c = outil.champs
    assert c["largeurTravailMinM"] == 3 and c["largeurTravailMaxM"] == 3, c
    assert c["puissanceRequiseMinCh"] == 180 and c["puissanceRequiseMaxCh"] == 320, c
    assert c["poidsVideKg"] == 5220 and c["typeAttelage"] == "PORTE", c
    assert c["categorieAttelage"] == "3", c
    assert "Nombre de disques" in outil.non_reconnus

    tracteur = extraire(FicheBrute(
        marque="Fendt", nom="724 Vario", categorie="tracteur",
        specs={"Puissance max": "174 kW / 237 ch", "Moteur": "Deutz 6 cylindres Stage V",
               "Poids à vide": "7 820 kg", "Largeur": "2,55 m", "Vitesse max": "50 km/h"},
    ))
    t = tracteur.champs
    assert t["puissanceMoteurCh"] == 237 and t["normeAntipollution"] == "Stage V", t
    assert t["poidsVideKg"] == 7820 and t["largeurTransportM"] == 2.55 and t["vitesseMaxRouteKmh"] == 50, t
    assert "puissanceRequiseMinCh" not in t and "typeAttelage" not in t, t

    traine = extraire(FicheBrute(marque="Kuhn", nom="Optimer XL 600", categorie="déchaumeur", variante="Traîné 6m",
                                 specs={"Largeur de travail": "6 m"}))
    assert traine.champs["typeAttelage"] == "TRAINE", traine.champs

    ambigu = extraire(FicheBrute(marque="X", nom="Y", categorie="semoir", specs={"Poids": "8270kg - 9360kg"}))
    assert "poidsVideKg" not in ambigu.champs and ambigu.ecartes, ambigu

    fiches = separer_variantes(FicheBrute(
        marque="Agrisem", nom="Rouleau", categorie="déchaumeur", variante="Porté 4m | Porté 5m | Porté 6m",
        specs={"Largeur de travail": "4.00m - 5.00m - 6.00m", "Puissance mini/maxi": "200-300ch - 280-380ch - 350-450ch",
               "Largeur de transport": "3.00m"},
    ))
    assert [f.variante for f in fiches] == ["Porté 4m", "Porté 5m", "Porté 6m"]
    e = extraire(fiches[2]).champs
    assert e["largeurTravailMinM"] == 6 and e["puissanceRequiseMinCh"] == 350 and e["largeurTransportM"] == 3, e

    a = extraire(FicheBrute(marque="Agrisem", nom="Rouleau", gamme="Série 5", categorie="déchaumeur", specs={"Poids": "1 t"}))
    b = extraire(FicheBrute(marque="Agrisem", nom="Rouleau", gamme="Série 12", categorie="déchaumeur", specs={"Poids": "2 t"}))
    c = extraire(FicheBrute(marque="Agrisem", nom="Herse", categorie="déchaumeur", specs={}))
    d = extraire(FicheBrute(marque="Agrisem", nom="Herse", categorie="déchaumeur", specs={"Poids": "1 t"}))
    res, signales = dedoublonner([a, b, c, d])
    assert sorted(e.brute.nom for e in res) == ["Herse", "Série 12 Rouleau", "Série 5 Rouleau"], [e.brute.nom for e in res]
    assert len(signales) == 1 and next(e for e in res if e.brute.nom == "Herse").champs, signales

    # Formats vus sur kuhn.fr (collecte du 15/10)
    kuhn = extraire(FicheBrute(
        marque="Kuhn", nom="Venta 3030", categorie="Semis",
        specs={"Puissance maxi tracteur (kW/ch)": "44/60", "Puissance mini nécessaire (kW/ch)": "37/50",
               "Poids (kg) env (NSH)": "675", "Poids (kg) env (T)": "550", "Attelage": "Std 2",
               "Equipement hydraulique requis": "1 DE pour le troisième point hydraulique",
               "Poids total autorisé (kg)": "3500", "Largeur de coupe (pouces)": "120"},
    )).champs
    assert kuhn["puissanceRequiseMaxCh"] == 60 and kuhn["puissanceRequiseMinCh"] == 50, kuhn
    assert kuhn["poidsVideKg"] == 675 and kuhn["ptacKg"] == 3500, kuhn
    assert kuhn["categorieAttelage"] == "2" and kuhn["distributeursDERequis"] == 1, kuhn
    assert kuhn["largeurTravailMinM"] == 3.05, kuhn

    from .normalisation import famille
    assert famille("Travail du sol") == "TRAVAIL_DU_SOL" and famille("Paillage") == "ELEVAGE"
    assert famille("Protection des cultures") == "PROTECTION_CULTURES" and famille("Semis") == "SEMIS_PLANTATION"


if __name__ == "__main__":
    verifier_unites()
    verifier_extraction()
    print("Tous les tests passent.")
