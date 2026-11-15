"""Ajoute à data/annonces.json les annonces extraites des alertes e-mail Leboncoin / PAP.

Entrée : data/alertes_gmail.json, liste d'objets remplie par la tâche du matin (Claude lit Gmail) :
  {"source": "leboncoin"|"pap", "url": "...", "titre": "...", "prix": 289000, "ville": "Jargeau",
   "surface": 130, "pieces": 6, "chambres": 4, "terrain": 900, "photo": "https://...", "description": "...",
   "vendeur": "particulier"|"agency"}
Les champs inconnus restent à null. Le fichier est vidé après fusion.
Une annonce d'alerte reste active 60 jours après sa dernière apparition dans un e-mail."""
import json, re, datetime
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "annonces.json"
IN = ROOT / "data" / "alertes_gmail.json"
today = datetime.date.today()
base = json.loads(DATA.read_text()) if DATA.exists() else {}
nouvelles = json.loads(IN.read_text()) if IN.exists() else []

n_new = 0
for a in nouvelles:
    if not a.get("url") or not a.get("prix"):
        continue
    m = re.search(r"(\d{6,})", a["url"])
    key = f"{a['source']}:{m.group(1) if m else a['url']}"
    f = {
        "source": a["source"], "url": a["url"], "titre": a.get("titre"), "ville": a.get("ville"),
        "cp": a.get("cp"), "prix": a["prix"], "surface": a.get("surface"), "terrain": a.get("terrain"),
        "pieces": a.get("pieces"), "chambres": a.get("chambres"), "dpe": a.get("dpe"), "dpe_valeur": None,
        "annee": None, "description": a.get("description") or "", "photos": [a["photo"]] if a.get("photo") else [],
        "vendeur": a.get("vendeur") or ("particulier" if a["source"] == "pap" else None),
        "type_annonce": "buy", "neuf": False, "garage": None, "piscine": None, "jardin": None,
        "publication": None, "baisse_signalee": False, "lat": None, "lon": None, "bbox": None, "flou": None,
    }
    old = base.get(key)
    if old:
        if f["prix"] != old["prix"]:
            old["historique"].append({"date": str(today), "prix": f["prix"]})
        old.update({k: v for k, v in f.items() if v not in (None, "", [])}, vu_le=str(today), active=True)
    else:
        f.update(premier_vu=str(today), vu_le=str(today), active=True, historique=[{"date": str(today), "prix": f["prix"]}])
        base[key] = f
        n_new += 1

for f in base.values():
    if f["source"] in ("leboncoin", "pap"):
        f["active"] = (today - datetime.date.fromisoformat(f["vu_le"])).days <= 60

DATA.write_text(json.dumps(base, ensure_ascii=False, indent=1))
IN.write_text("[]")
print(f"Alertes e-mail : {len(nouvelles)} lues, {n_new} nouvelles annonces")
