"""Bandeaux photo : UN fichier par bien, site/s/<hash>.jpg (5 photos côte à côte pour les biens retenus,
1 seule pour les écartés). Un fichier par bien = publication en un seul envoi (limite 255 fichiers).

Fonctionne sans cache local (tâche cloud) : data/bandeaux.json mémorise combien de photos chaque bandeau
contient ; un bandeau à jour n'est ni retéléchargé ni reconstruit.
Assemblage avec ffmpeg si présent, sinon Pillow (pip install pillow).
Écrit la liste des bandeaux nouveaux ou modifiés dans site/nouveaux_fichiers.txt."""
import io, json, hashlib, shutil, subprocess, urllib.request, concurrent.futures as cf
from pathlib import Path

ROOT = Path(__file__).parent
STRIP = ROOT / "site" / "s"
CACHE = ROOT / "data" / "photos_cache"
REG = ROOT / "data" / "bandeaux.json"
STRIP.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
H = 480
FFMPEG = shutil.which("ffmpeg")

d = json.loads((ROOT / "data/dashboard.json").read_text())
reg = json.loads(REG.read_text()) if REG.exists() else {}


def get(url):
    dest = CACHE / (hashlib.md5(url.encode()).hexdigest() + ".src")
    if dest.exists():
        return dest
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read()
        dest.write_bytes(raw)
        return dest
    except Exception:
        return None


def build(srcs, dest):
    if FFMPEG:
        args = [FFMPEG, "-loglevel", "error", "-y"]
        for x in srcs:
            args += ["-i", str(x)]
        chains = "".join(f"[{i}:v]scale=-2:{H},setsar=1[v{i}];" for i in range(len(srcs)))
        flt = chains + "".join(f"[v{i}]" for i in range(len(srcs))) + f"hstack=inputs={len(srcs)}[o]" if len(srcs) > 1 else chains.rstrip(";").replace("[v0]", "[o]")
        subprocess.run(args + ["-filter_complex", flt, "-map", "[o]", "-q:v", "6", str(dest)], capture_output=True, check=True)
        return
    from PIL import Image
    ims = []
    for x in srcs:
        im = Image.open(x).convert("RGB")
        ims.append(im.resize((max(1, round(im.width * H / im.height)), H)))
    out = Image.new("RGB", (sum(i.width for i in ims), H))
    xo = 0
    for i in ims:
        out.paste(i, (xo, 0)); xo += i.width
    out.save(dest, "JPEG", quality=72, optimize=True)


def bandeau(a):
    h = hashlib.md5(a["id"].encode()).hexdigest()[:12]
    urls = (a.get("photos") or [])[: (1 if a["ecartee"] else 5)]
    dest = STRIP / f"{h}.jpg"
    a["images"], a["nb_photos"] = ([f"s/{h}.jpg"], reg.get(h, 1)) if dest.exists() else ([], 0)
    if not urls or (dest.exists() and reg.get(h) == len(urls)):
        return None
    srcs = [p for p in (get(u) for u in urls) if p]
    if not srcs or (dest.exists() and reg.get(h, 0) >= len(srcs)):
        return None
    try:
        build(srcs, dest)
    except Exception:
        return None
    reg[h] = len(srcs)
    a["images"], a["nb_photos"] = [f"s/{h}.jpg"], len(srcs)
    return f"s/{h}.jpg"


with cf.ThreadPoolExecutor(6) as ex:
    modifies = [x for x in ex.map(bandeau, d["annonces"]) if x]

REG.write_text(json.dumps(reg))
(ROOT / "data/dashboard.json").write_text(json.dumps(d, ensure_ascii=False))
(ROOT / "site/nouveaux_fichiers.txt").write_text("\n".join(modifies))
print(len(modifies), "bandeaux nouveaux ou modifiés")
