"""Collecte des maisons en vente sur Bien'ici (API JSON publique du site).

Met à jour data/annonces.json : une fiche par annonce, avec historique des prix,
date de première et dernière apparition.
"""
import json, time, datetime, urllib.parse, urllib.request
from pathlib import Path

DATA = Path(__file__).parent / "data" / "annonces.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

ZONES = {
    "Orléans": "-147559",
    "Fay-aux-Loges": "-148202",
    "Traînou": "-165390",
    "Jargeau": "-165282",
    "Vitry-aux-Loges": "-148651",
    "Châteauneuf-sur-Loire": "-148201",
}
# Collecte un peu plus large que le budget pour voir les baisses de prix qui y entrent.
PRIX_MIN, PRIX_MAX = 200_000, 440_000


def fetch(zone_id, start):
    filters = {
        "size": 100, "from": start, "filterType": "buy", "propertyType": ["house"],
        "minPrice": PRIX_MIN, "maxPrice": PRIX_MAX, "onTheMarket": [True],
        "zoneIdsByTypes": {"zoneIds": [zone_id]},
        "sortBy": "publicationDate", "sortOrder": "desc",
    }
    url = "https://www.bienici.com/realEstateAds.json?" + urllib.parse.urlencode({"filters": json.dumps(filters)})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fiche(a):
    pos = (a.get("blurInfo") or {}).get("position") or {}
    return {
        "source": "bienici",
        "url": f"https://www.bienici.com/annonce/{a['id']}",
        "titre": a.get("title"),
        "ville": a.get("city"),
        "cp": a.get("postalCode"),
        "prix": a.get("price"),
        "surface": a.get("surfaceArea"),
        "terrain": a.get("landSurfaceArea"),
        "pieces": a.get("roomsQuantity"),
        "chambres": a.get("bedroomsQuantity"),
        "dpe": a.get("energyClassification"),
        "dpe_valeur": a.get("energyValue"),
        "annee": a.get("yearOfConstruction"),
        "description": a.get("description") or "",
        "photos": [p.get("url_photo") or p.get("url") for p in (a.get("photos") or [])][:12],
        "vendeur": a.get("accountType"),  # agency / mandatary / builder / particulier
        "type_annonce": a.get("adType"),
        "neuf": a.get("newProperty"),
        "garage": (a.get("parkingPlacesQuantity") or 0) > 0,
        "piscine": a.get("hasPool"),
        "jardin": a.get("hasGarden"),
        "cave": a.get("hasCellar"),
        "cheminee": a.get("hasFirePlace"),
        "terrasse": a.get("hasTerrace"),
        "publication": a.get("publicationDate"),
        "baisse_signalee": a.get("priceHasDecreased"),
        "lat": pos.get("lat"),
        "lon": pos.get("lon"),
        "bbox": (a.get("blurInfo") or {}).get("bbox"),
        "flou": (a.get("blurInfo") or {}).get("type"),        # disk = position à ~rayon près
        "flou_rayon": (a.get("blurInfo") or {}).get("radius"),
    }


def main():
    base = json.loads(DATA.read_text()) if DATA.exists() else {}
    today = datetime.date.today().isoformat()
    vus = set()
    for ville, zid in ZONES.items():
        start, total = 0, 1
        while start < total:
            d = fetch(zid, start)
            total = d.get("total", 0)
            for a in d.get("realEstateAds", []):
                if a.get("adType") == "lifeAnnuitySale":  # viager : hors sujet
                    continue
                key = "bienici:" + a["id"]
                vus.add(key)
                f = fiche(a)
                old = base.get(key)
                if old:
                    if f["prix"] and f["prix"] != old["prix"]:
                        old["historique"].append({"date": today, "prix": f["prix"]})
                    old.update(f)
                    old["vu_le"] = today
                    old["active"] = True
                else:
                    f.update(premier_vu=today, vu_le=today, active=True,
                             historique=[{"date": today, "prix": f["prix"]}])
                    base[key] = f
            start += 100
            time.sleep(1.5)
        print(f"{ville}: {total} annonces")
    for k, f in base.items():
        if f["source"] == "bienici" and k not in vus:
            f["active"] = False
    DATA.write_text(json.dumps(base, ensure_ascii=False, indent=1))
    print("Total en base :", len(base), "| actives :", sum(f["active"] for f in base.values()))


if __name__ == "__main__":
    main()
