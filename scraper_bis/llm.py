"""Passe LLM facultative (--llm) : Mistral complète les champs clés manquants à
partir des libellés non reconnus. Chaque valeur garde son extrait et une
confiance plafonnée à 0,5 : elle reste « à vérifier » dans la relecture.
"""

from __future__ import annotations

import json
import logging
import os

from .extraction import BORNES, ENTIERS, champs_cles
from .modele import FicheExtraite, Proposition

log = logging.getLogger("scraper_bis")

DESCRIPTION_CHAMPS = {
    "typeAttelage": "un de PORTE, SEMI_PORTE, TRAINE, FRONTAL, AUTOMOTEUR",
    "largeurTravailMinM": "largeur de travail minimale en mètres",
    "largeurTravailMaxM": "largeur de travail maximale en mètres",
    "largeurTransportM": "largeur au transport en mètres",
    "poidsVideKg": "poids à vide en kg",
    "puissanceRequiseMinCh": "puissance de tracteur requise minimale en ch",
    "puissanceRequiseMaxCh": "puissance de tracteur requise maximale en ch",
    "puissanceMoteurCh": "puissance du moteur en ch",
    "normeAntipollution": "norme antipollution, ex. Stage V",
}


def completer(extraites: list[FicheExtraite], maximum: int, appel=None) -> int:
    """Complète au plus `maximum` machines. `appel` permet de simuler l'API dans les tests."""
    appel = appel or _appel_mistral
    faites = 0
    for e in extraites:
        if faites >= maximum:
            break
        manquants = [c for c in champs_cles(e) if c not in e.champs]
        if e.tracteur is False and "largeurTravailMinM" in manquants:
            manquants.append("largeurTravailMaxM")
        if "puissanceRequiseMinCh" in manquants:
            manquants.append("puissanceRequiseMaxCh")
        specs = {k: e.brute.specs[k] for k in e.non_reconnus}
        if not manquants or not specs:
            continue
        faites += 1
        try:
            reponse = appel(e, {c: DESCRIPTION_CHAMPS.get(c, c) for c in manquants}, specs)
        except Exception as ex:
            log.warning(f"LLM : échec pour {e.brute.cle()} ({ex})")
            continue
        for champ, contenu in (reponse or {}).items():
            if champ not in manquants or not isinstance(contenu, dict):
                continue
            valeur, extrait = contenu.get("valeur"), str(contenu.get("extrait") or "")
            if valeur is None or not extrait or extrait.split(":")[0].strip() not in specs:
                continue  # pas de preuve dans les specs fournies : on n'invente rien
            if champ in BORNES:
                try:
                    valeur = float(valeur)
                except (TypeError, ValueError):
                    continue
                lo, hi = BORNES[champ]
                if not lo <= valeur <= hi:
                    continue
                valeur = int(round(valeur)) if champ in ENTIERS else round(valeur, 2)
            e.propositions.append(Proposition(champ, valeur, extrait[:300], 0.5, "llm"))
            e.champs[champ] = valeur
    return faites


def _appel_mistral(e: FicheExtraite, champs: dict[str, str], specs: dict[str, str]) -> dict:
    import requests

    cle = os.environ.get("MISTRAL_API_KEY")
    if not cle:
        raise RuntimeError("MISTRAL_API_KEY absent")
    consigne = (
        "Tu extrais des caractéristiques techniques de machines agricoles. Réponds uniquement en JSON : "
        '{"<champ>": {"valeur": <nombre ou texte>, "extrait": "<libellé exact> : <valeur exacte>"}}. '
        "N'utilise que les caractéristiques fournies. Si une valeur n'y figure pas, omets le champ. "
        "Ne déduis rien, ne convertis que les unités."
    )
    contenu = {
        "machine": f"{e.brute.marque} {e.brute.nom} {e.brute.variante}".strip(),
        "categorie": e.categorie_nom,
        "champs_demandes": champs,
        "caracteristiques": specs,
    }
    r = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {cle}"},
        json={
            "model": "mistral-small-latest",
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": consigne},
                         {"role": "user", "content": json.dumps(contenu, ensure_ascii=False)}],
        },
        timeout=60,
    )
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])
