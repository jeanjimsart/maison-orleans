"""Construit site/data.json (données de la page) + la carte des communes (contours officiels geo.api.gouv.fr, mis en cache)."""
import json, math, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
CARTE = ROOT / "data" / "carte.json"
INSEE = {"45234": "Orléans", "45142": "Fay-aux-Loges", "45327": "Traînou", "45173": "Jargeau",
         "45346": "Vitry-aux-Loges", "45082": "Châteauneuf-sur-Loire"}
W = 1000


def contours():
    """Toutes les communes du Loiret autour de la zone (contours officiels), mises en cache."""
    if CARTE.exists():
        return json.loads(CARTE.read_text())
    u = "https://geo.api.gouv.fr/departements/45/communes?fields=nom,code,centre,contour&format=json"
    out = {}
    for d in json.load(urllib.request.urlopen(u, timeout=60)):
        lon, lat = d["centre"]["coordinates"]
        if 1.80 <= lon <= 2.36 and 47.79 <= lat <= 48.02 and d.get("contour"):
            out[d["code"]] = {"nom": d["nom"], "contour": d["contour"], "cible": d["code"] in INSEE}
    CARTE.write_text(json.dumps(out))
    return out


def build():
    c = contours()
    pts = [p for v in c.values() if v["cible"] for ring in (v["contour"]["coordinates"] if v["contour"]["type"] == "Polygon"
           else [r for poly in v["contour"]["coordinates"] for r in poly]) for p in ring]
    lon0, lon1 = min(p[0] for p in pts), max(p[0] for p in pts)
    lat0, lat1 = min(p[1] for p in pts), max(p[1] for p in pts)
    mx, my = (lon1 - lon0) * 0.05, (lat1 - lat0) * 0.08
    lon0, lon1, lat0, lat1 = lon0 - mx, lon1 + mx, lat0 - my, lat1 + my
    k = math.cos(math.radians((lat0 + lat1) / 2))
    sx = W / ((lon1 - lon0) * k)
    H = round((lat1 - lat0) * sx)
    proj = {"lon0": lon0, "lat1": lat1, "k": k, "s": sx, "w": W, "h": H}

    def xy(p):
        return round((p[0] - lon0) * k * sx, 1), round((lat1 - p[1]) * sx, 1)

    communes = []
    for code, v in c.items():
        g = v["contour"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        d = ""
        for poly in polys:
            for ring in poly:
                q = [xy(p) for p in ring[::2]]
                d += "M" + "L".join(f"{x},{y}" for x, y in q) + "Z"
        ring = polys[0][0]
        cx = sum(p[0] for p in ring) / len(ring); cy = sum(p[1] for p in ring) / len(ring)
        communes.append({"nom": v["nom"], "cible": v["cible"], "d": d, "label": xy((cx, cy))})

    data = json.loads((ROOT / "data/dashboard.json").read_text())
    for a in data["annonces"]:
        a.pop("photos", None)
        if a.get("lat") and a.get("position_precise"):
            a["xy"] = xy((a["lon"], a["lat"]))
        a.pop("lat", None); a.pop("lon", None)
    data["carte"] = {"proj": proj, "communes": communes}
    (ROOT / "site/data.json").write_text(json.dumps(data, ensure_ascii=False))
    print("site/data.json écrit,", sum(1 for a in data["annonces"] if a.get("xy")), "maisons placées sur la carte")


if __name__ == "__main__":
    build()
