"""Collecte des maisons en vente sur immobilier.notaires.fr (API publique du site)."""
import json, time, datetime, urllib.request
from pathlib import Path

DATA = Path(__file__).parent / "data" / "annonces.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
INSEE = {"45234": "Orléans", "45142": "Fay-aux-Loges", "45327": "Traînou",
         "45173": "Jargeau", "45346": "Vitry-aux-Loges", "45082": "Châteauneuf-sur-Loire"}
BASE = ("https://www.immobilier.notaires.fr/pub-services/inotr-www-annonces/v1/annonces"
        "?offset=0&page={p}&parPage=100&perimetre=0&typeBiens=MAI&typeTransactions=VENTE"
        "&departements=45&prixMin=200000&prixMax=440000")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    base = json.loads(DATA.read_text()) if DATA.exists() else {}
    today = datetime.date.today().isoformat()
    vus, p, pages = set(), 1, 1
    while p <= pages:
        d = get(BASE.format(p=p))
        pages = d.get("nbPages", 1)
        for a in d.get("annonceResumeDto", []):
            if a.get("inseeCommune") not in INSEE or a.get("viager") == "OUI":
                continue
            key = f"notaires:{a['annonceId']}"
            vus.add(key)
            prix = a.get("prixTotal") or a.get("prixAffiche")
            f = {
                "source": "notaires", "url": a.get("urlDetailAnnonceFr"),
                "titre": a.get("descriptionFr"), "ville": a.get("communeNom"), "cp": a.get("codePostal"),
                "prix": prix, "surface": a.get("surface"), "terrain": a.get("surfaceTerrain"),
                "pieces": a.get("nbPieces"), "chambres": a.get("nbChambres"),
                "dpe": None, "dpe_valeur": None, "annee": None,
                "description": a.get("descriptionFr") or "",
                "photos": [a["urlPhotoPrincipale"]] if a.get("urlPhotoPrincipale") else [],
                "vendeur": "notaire", "type_annonce": "buy", "neuf": a.get("ancienNeuf") == "NEUF",
                "garage": None, "piscine": None, "jardin": None,
                "publication": a.get("dateCreation"), "baisse_signalee": a.get("variation") == "BAISSE",
                "lat": None, "lon": None, "bbox": None,
            }
            old = base.get(key)
            if old:
                if prix and prix != old["prix"]:
                    old["historique"].append({"date": today, "prix": prix})
                old.update(f, vu_le=today, active=True)
            else:
                f.update(premier_vu=today, vu_le=today, active=True, historique=[{"date": today, "prix": prix}])
                base[key] = f
        p += 1
        time.sleep(1.5)
    for k, f in base.items():
        if f["source"] == "notaires" and k not in vus:
            f["active"] = False
    DATA.write_text(json.dumps(base, ensure_ascii=False, indent=1))
    print("Notaires :", len(vus), "annonces dans les 6 communes")


if __name__ == "__main__":
    main()
