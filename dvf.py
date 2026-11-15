"""Prépare les ventes réelles de maisons (DVF) des 6 communes -> data/ventes_maisons.json"""
import csv, json, glob
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
mut = defaultdict(list)
for f in glob.glob(str(ROOT / "data/dvf/*.csv")):
    with open(f, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            mut[r["id_mutation"]].append(r)

ventes = []
for mid, rows in mut.items():
    if rows[0]["nature_mutation"] != "Vente" or not rows[0]["valeur_fonciere"]:
        continue
    locaux = {(r["id_parcelle"], r["type_local"], r["surface_reelle_bati"]) for r in rows if r["type_local"]}
    maisons = [l for l in locaux if l[1] == "Maison"]
    if len(maisons) != 1 or any(l[1] in ("Appartement", "Local industriel. commercial ou assimilé") for l in locaux):
        continue
    surf = float(maisons[0][2] or 0)
    prix = float(rows[0]["valeur_fonciere"])
    if not (50 <= surf <= 400) or not (500 <= prix / surf <= 8000):
        continue
    terrain = sum({r["id_parcelle"]: float(r["surface_terrain"] or 0) for r in rows}.values())
    r0 = next((r for r in rows if r["type_local"] == "Maison"), rows[0])
    if not r0["latitude"]:
        continue
    ventes.append({
        "date": r0["date_mutation"], "prix": prix, "surface": surf, "terrain": terrain,
        "pieces": int(r0["nombre_pieces_principales"] or 0),
        "lat": float(r0["latitude"]), "lon": float(r0["longitude"]),
        "commune": r0["nom_commune"], "cp": r0["code_postal"], "pm2": round(prix / surf),
        "adresse": f'{r0["adresse_numero"]} {r0["adresse_nom_voie"]}'.strip(),
    })

(ROOT / "data/ventes_maisons.json").write_text(json.dumps(ventes, ensure_ascii=False))
by = defaultdict(list)
for v in ventes:
    by[v["commune"]].append(v["pm2"])
for c, l in sorted(by.items()):
    l.sort()
    print(f"{c}: {len(l)} ventes, médiane {l[len(l)//2]} €/m²")
print("Période :", min(v["date"] for v in ventes), "→", max(v["date"] for v in ventes))
