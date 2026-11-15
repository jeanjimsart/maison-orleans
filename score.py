"""Note chaque annonce : critères, doublons, prix du marché (DVF), travaux, vis-à-vis, affaire.
Produit data/dashboard.json pour le tableau de bord."""
import json, math, re, datetime, statistics
from pathlib import Path

ROOT = Path(__file__).parent
TODAY = datetime.date.today()
annonces = json.loads((ROOT / "data/annonces.json").read_text())
ventes = [v for v in json.loads((ROOT / "data/ventes_maisons.json").read_text()) if v["date"] >= "2023-01-01"]

BUDGET_MAX = 400_000
# Villes éloignées souvent citées par des mandataires qui mettent leur propre ville dans l'annonce
HORS_ZONE = ["chateaudun", "pithiviers", "montargis", "gien", "vendome", "blois", "beaugency", "meung-sur-loire",
             "sully-sur-loire", "romorantin", "vierzon", "chartres", "etampes", "nemours", "bourges", "lamotte-beuvron",
             "patay", "artenay", "lorris", "bellegarde", "briare", "malesherbes", "puiseaux", "dadonville",
             "la ferte-saint-aubin", "salbris", "chateaurenard", "neuville-aux-bois", "outarville", "beaune-la-rolande",
             "ouzouer", "clery-saint-andre", "tours", "le mans", "dreux", "fontainebleau", "auxerre"]
VILLAGES = {"Fay-aux-Loges", "Traînou", "Trainou", "Jargeau", "Vitry-aux-Loges", "Châteauneuf-sur-Loire"}


def norm(s):
    s = (s or "").lower()
    for a, b in (("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"), ("â", "a"), ("î", "i"), ("ô", "o"), ("û", "u"), ("ç", "c"), ("’", "'")):
        s = s.replace(a, b)
    return s


def has(txt, *mots):
    return [m for m in mots if re.search(m, txt)]


def km(a, b, c, d):
    p = math.pi / 180
    x = (d - b) * p * math.cos((a + c) / 2 * p)
    return 6371 * math.hypot(x, (c - a) * p)


def village(v):
    return norm(v).replace("i", "i") in {norm(x) for x in VILLAGES}


# ---------- prix du marché ----------
def marche(f):
    if not f.get("surface"):
        return None
    s = f["surface"]
    precis = f.get("lat") and f.get("flou") == "disk"
    rayons = [1.0, 1.5, 2.5] if not village(f["ville"]) else [2.0, 3.5, 5.0]
    comps, zone = [], ""
    if precis:
        for r in rayons:
            comps = [v for v in ventes if 0.75 * s <= v["surface"] <= 1.35 * s and km(f["lat"], f["lon"], v["lat"], v["lon"]) <= r]
            zone = f"à moins de {r:g} km"
            if len(comps) >= 10:
                break
    if len(comps) < 10:
        comps = [v for v in ventes if norm(v["commune"]) == norm(f["ville"]) and 0.65 * s <= v["surface"] <= 1.5 * s]
        if not village(f["ville"]) and f.get("cp"):
            sous = [v for v in comps if v.get("cp") == f["cp"]]
            comps, zone = (sous, f"code postal {f['cp']}") if len(sous) >= 10 else (comps, "toute la commune")
        else:
            zone = "toute la commune"
    if len(comps) < 5:
        return None
    # Le prix au m² baisse avec la surface (mesuré sur DVF) : on ramène chaque vente à la surface de l'annonce.
    el = 0.24 if village(f["ville"]) else 0.08
    pm2 = statistics.median(v["pm2"] * (v["surface"] / s) ** el for v in comps)
    # Les annonces d'agence affichent le prix frais d'agence inclus (~5 %), DVF est hors frais.
    prix_net = f["prix"] / 1.05 if f.get("vendeur") not in ("particulier", "notaire") else f["prix"]
    estim = pm2 * s
    exemples = sorted(comps, key=lambda v: v["date"], reverse=True)[:5]
    return {
        "pm2_marche": round(pm2), "pm2_annonce": round(prix_net / s), "estimation": round(estim, -3),
        "ecart": round((prix_net - estim) / estim * 100), "nb_ventes": len(comps), "zone": zone,
        "exemples": [{k: v[k] for k in ("date", "prix", "surface", "terrain", "adresse")} for v in exemples],
    }


# ---------- travaux ----------
def travaux(f, t):
    gros = has(t, r"a renover", r"renovation (complete|totale)", r"gros travaux", r"a restaurer", r"a rehabiliter",
               r"toiture a (refaire|reprendre)", r"remise aux normes", r"travaux importants", r"entierement a refaire",
               r"electricite a refaire", r"a remettre en etat", r"plateau a amenager", r"a finir d'amenager",
               r"ensemble immobilier a renover", r"fort potentiel")
    rafr = has(t, r"a rafraichir", r"rafraichissement", r"travaux a prevoir", r"a moderniser", r"au gout du jour",
               r"quelques travaux", r"prevoir (des |quelques )?travaux", r"a actualiser", r"cuisine a refaire",
               r"salle de bains? a refaire", r"a personnaliser")
    neuf = has(t, r"refait(e)? a neuf", r"renove(e)?", r"aucun travaux", r"sans travaux", r"cle en main",
               r"poser vos valises", r"prete? a (vivre|habiter)", r"entierement refait", r"recemment renove")
    dpe = (f.get("dpe") or "").upper()
    raisons = []
    if gros:
        niveau = "Gros travaux"; raisons += gros
    elif rafr:
        niveau = "Rafraîchissement"; raisons += rafr
    elif neuf:
        niveau = "Aucun"; raisons += neuf
    else:
        niveau = "Non précisé"
    if dpe in ("F", "G"):
        raisons.append(f"DPE {dpe} : isolation / chauffage à revoir")
        if niveau in ("Aucun", "Non précisé", "Rafraîchissement"):
            niveau = "Gros travaux (énergie)"
    elif dpe == "E" and niveau in ("Aucun", "Non précisé"):
        raisons.append("DPE E : isolation probablement à améliorer")
        niveau = "Rafraîchissement" if niveau == "Non précisé" else niveau
    return niveau, [r.replace("\\", "").replace("(e)?", "").replace("?", "") for r in raisons]


# ---------- enveloppe pour atteindre un DPE C ----------
# Ordres de grandeur €/m² habitable (isolation + chauffage + ventilation), hors aides, à faire chiffrer.
BANDES_DPE = {"D": (80, 160), "E": (170, 280), "F": (260, 400), "G": (350, 550)}


def enveloppe_dpe(f):
    d, s, v = (f.get("dpe") or "").upper(), f.get("surface"), f.get("dpe_valeur")
    if d in ("A", "B", "C"):
        return {"etat": "ok"}
    if d not in BANDES_DPE or not s:
        return {"etat": "inconnu"}
    lo, hi = BANDES_DPE[d]
    if d == "D" and v and v <= 200:  # D tout juste : un seul poste suffit souvent
        lo, hi = 50, 110
    return {"etat": "travaux", "min": round(s * lo, -3), "max": round(s * hi, -3), "depuis": d, "kwh": v}


# ---------- vis-à-vis / lotissement / mitoyenneté ----------
def environnement(f, t):
    sans = has(t, r"sans vis[- ]a[- ]vis", r"aucun vis[- ]a[- ]vis", r"pas de vis[- ]a[- ]vis", r"a l'abri des regards",
               r"sans voisin", r"maison isolee", r"en impasse", r"au calme absolu", r"non mitoyenne", r"totalement independante")
    plus = has(t, r"au calme", r"arbore", r"impasse", r"campagne", r"en lisiere", r"en retrait", r"intimite", r"maison independante", r"au fond d'une allee")
    lotiss = has(t, r"lotissement", r"quartier pavillonnaire", r"residence (calme|recente)")
    mitoy = [m for m in has(t, r"mitoyenne", r"mitoyennete", r"maison de ville", r"accolee", r"jumelee") if not re.search(r"non mitoyenne", t)]
    terrain = f.get("terrain") or 0
    if sans:
        vv = "Sans vis-à-vis (annoncé)"
    elif mitoy or (terrain and terrain < 300):
        vv = "Douteux"
    elif (terrain >= 1500) or len(plus) >= 2:
        vv = "Probable"
    else:
        vv = "À vérifier"
    return vv, sans + plus, lotiss, mitoy


# ---------- travaux poste par poste ----------
def preuve(f, m):
    """Extrait lisible autour d'une correspondance trouvée dans norm(titre + " " + description)."""
    titre, desc = f.get("titre") or "", f.get("description") or ""
    off = len(titre) + 1
    if m.start() < off:
        return titre
    return extrait(desc, m.start() - off, m.end() - off)


def extrait(desc, i, j):
    a, b = max(0, i - 50), min(len(desc), j + 110)
    return ("…" if a else "") + desc[a:b].replace("\n", " ").strip() + ("…" if b < len(desc) else "")


# (clé, libellé, regex « à prévoir », regex « fait / bon état », coût bas, coût haut, unité)  unité : "f" forfait, "m2" par m² habitable
POSTES = [
    ("toiture", "Toiture / charpente", r"toiture (a refaire|a reprendre|a revoir|ancienne|vieillissante)|couverture a (refaire|reprendre)|charpente a (revoir|traiter)|infiltration",
     r"toiture (refaite|neuve|recente|renovee|en bon etat|saine)|couverture (refaite|neuve)", 12000, 35000, "f"),
    ("isolation", "Isolation", r"isolation (a revoir|a prevoir|a refaire|a ameliorer|insuffisante)|(pas|peu|mal) isolee?|absence d'isolation",
     r"isolation (refaite|recente|renforcee|neuve|par l'exterieur)|(bien|tres bien|parfaitement) isolee?|combles isoles|isolation thermique par l'exterieur", 8000, 25000, "f"),
    ("fenetres", "Fenêtres / menuiseries", r"simple vitrage|menuiseries? (a changer|a remplacer|anciennes|bois d'origine)|fenetres? (a changer|a remplacer)",
     r"double vitrage|triple vitrage|menuiseries? (pvc|alu|recentes|neuves|changees)|fenetres? (neuves|recentes|changees)", 8000, 16000, "f"),
    ("chauffage", "Chauffage", r"fioul|fuel|convecteurs?|chaudiere (ancienne|a changer|a remplacer|vetuste)|radiateurs? electriques? (anciens|grille-pain)",
     r"pompe a chaleur|pac\b|chaudiere (a condensation|recente|neuve)|poele a granules|plancher chauffant|chauffage (recent|neuf)", 9000, 18000, "f"),
    ("electricite", "Électricité", r"electricite (a refaire|a revoir|a reprendre|a remettre|ancienne|vetuste|a mettre aux normes)|mise aux normes electrique|tableau electrique a changer",
     r"electricite (refaite|recente|neuve|aux normes|renovee)|tableau electrique (neuf|recent)", 90, 130, "m2"),
    ("plomberie", "Plomberie", r"plomberie (a refaire|a revoir|ancienne|vetuste)|canalisations? (plomb|a changer)",
     r"plomberie (refaite|recente|neuve)", 5000, 12000, "f"),
    ("cuisine", "Cuisine", r"cuisine (a refaire|a renover|a moderniser|a rafraichir|ancienne|a creer|a amenager)",
     r"cuisine (neuve|recente|refaite|renovee|amenagee et equipee recente|haut de gamme)", 6000, 15000, "f"),
    ("sdb", "Salle de bains", r"salles? (de bains?|d'eau) (a refaire|a renover|a moderniser|a rafraichir|ancienne)",
     r"salles? (de bains?|d'eau) (neuve|recente|refaite|renovee)", 6000, 12000, "f"),
    ("finitions", "Sols / peintures", r"a rafraichir|rafraichissement|peintures? (a refaire|a prevoir)|revetements? (a changer|a refaire)|papiers? peints?|moquettes?|au gout du jour",
     r"peintures? (neuves|refaites|recentes)|sols? (neufs|recents|refaits)|parquet (neuf|refait|vitrifie)", 30, 60, "m2"),
    ("assainissement", "Assainissement", r"fosse septique|assainissement (individuel|non collectif|a mettre aux normes|non conforme)|micro-station",
     r"tout[- ]a[- ]l'egout|assainissement (collectif|conforme|aux normes)|raccorde(e)? au tout", 7000, 13000, "f"),
    ("facade", "Façade / ravalement", r"ravalement (a prevoir|a faire|a refaire)|facade a (refaire|reprendre|rafraichir)|fissures?",
     r"ravalement (recent|refait|fait)|facade (refaite|recente|renovee)", 8000, 20000, "f"),
    ("humidite", "Humidité", r"humidite|salpetre|remontees capillaires|moisissures?",
     r"aucune humidite|pas d'humidite|maison saine|\bsaine\b", 3000, 10000, "f"),
    ("ventilation", "Ventilation (VMC)", r"pas de vmc|sans vmc|ventilation a (prevoir|revoir)",
     r"vmc( double flux| hygro)?|ventilation mecanique", 1500, 4500, "f"),
]


def postes_travaux(f, t):
    surf = f.get("surface") or 120
    out = []
    for cle, lib, rx_mal, rx_bon, lo, hi, unite in POSTES:
        mal, bon = re.search(rx_mal, t), re.search(rx_bon, t)
        if cle == "finitions" and not mal and travaux_niveau_global(t) == "rafr":
            mal = None
        etat = "prevoir" if mal and not bon else "fait" if bon and not mal else "mixte" if mal and bon else "inconnu"
        m = mal or bon
        c_lo, c_hi = (lo * surf, hi * surf) if unite == "m2" else (lo, hi)
        out.append({"k": cle, "l": lib, "etat": etat, "min": round(c_lo, -2), "max": round(c_hi, -2),
                    "preuve": preuve(f, m) if m else None})
    reno = re.search(r"a renover|renovation (complete|totale|a prevoir)|entierement a (refaire|renover)|a rehabiliter|a restaurer|a remettre en etat", t)
    if reno:
        out.insert(0, {"k": "renovation", "l": "Rénovation générale", "etat": "prevoir", "min": round(400 * surf, -3), "max": round(800 * surf, -3),
                       "preuve": preuve(f, reno)})
    dpe = (f.get("dpe") or "").upper()
    if dpe in ("F", "G"):  # DPE très bas : isolation et chauffage quasi certains
        for o in out:
            if o["k"] in ("isolation", "chauffage") and o["etat"] == "inconnu":
                o["etat"] = "prevoir"; o["preuve"] = f"DPE {dpe} : poste presque toujours à reprendre"
    return out


def travaux_niveau_global(t):
    return "rafr" if re.search(r"a rafraichir|rafraichissement", t) else ""


# ---------- budget et négociation ----------
def budget(f, postes, env, m, jours, baisse, niveau):
    prix = f["prix"]
    notaire = round(prix * (0.025 if f.get("neuf") else 0.075), -2)
    tr = [o for o in postes if o["etat"] in ("prevoir", "mixte")]
    t_lo, t_hi = sum(o["min"] for o in tr if o["k"] != "renovation"), sum(o["max"] for o in tr if o["k"] != "renovation")
    reno = next((o for o in tr if o["k"] == "renovation"), None)
    if reno:  # la rénovation générale englobe les autres postes
        t_lo, t_hi = max(t_lo, reno["min"]), max(t_hi, reno["max"])
    e_lo, e_hi = (env["min"], env["max"]) if env.get("etat") == "travaux" else (0, 0)
    # l'enveloppe énergie recoupe isolation / chauffage / fenêtres : on garde le plus grand des deux
    w_lo, w_hi = max(t_lo, e_lo), max(t_hi, e_hi)
    neg, raisons = 3, ["marge habituelle"]
    if jours > 180: neg += 3; raisons.append(f"en vente depuis {jours} jours")
    elif jours > 90: neg += 2; raisons.append(f"en vente depuis {jours} jours")
    if baisse: neg += 1; raisons.append("prix déjà baissé, vendeur pressé")
    if m and m["ecart"] > 5: neg += 3; raisons.append(f"{m['ecart']} % au-dessus du secteur")
    if niveau.startswith("Gros"): neg += 2; raisons.append("gros travaux à chiffrer")
    if (f.get("dpe") or "").upper() in ("F", "G"): neg += 2; raisons.append("passoire énergétique")
    neg = min(neg, 15)
    return {"prix": prix, "notaire": notaire, "travaux_min": w_lo, "travaux_max": w_hi,
            "total_min": prix + notaire + w_lo, "total_max": prix + notaire + w_hi,
            "neg_min": max(2, neg - 3), "neg_max": neg, "neg_raisons": raisons,
            "offre": round(prix * (1 - neg / 100), -3)}


# ---------- atouts ----------
def atouts(f, t):
    """Atouts choisis par Julien et sa compagne/son conjoint (15/11/2026). Les autres équipements vont dans « equipements »."""
    out, eq = [], []
    desc = f.get("description") or ""
    def add(lst, cle, label, cond):
        if cond and cle not in [o["k"] for o in lst]:
            o = {"k": cle, "l": label}
            if isinstance(cond, re.Match):
                o["preuve"] = preuve(f, cond)
            lst.append(o)
    sej = [int(m.group(2)) for m in re.finditer(r"(sejour|salon|piece de vie|piece a vivre|salle a manger)[^.;\n]{0,40}?(\d{2,3})(?:[.,]\d+)?\s?m", t)]
    sej = [x for x in sej if 30 <= x <= 150]
    terr = f.get("terrain") or 0
    add(out, "dependance", "Dépendance", re.search(r"dependance|grange|longere|atelier|studio independant|maison d'amis|gite|annexe habitable|pool house", t))
    msej = re.search(r"(sejour|salon|piece de vie|piece a vivre|salle a manger)[^.;\n]{0,40}?(\d{2,3})(?:[.,]\d+)?\s?m", t)
    add(out, "sejour", f"Séjour {max(sej) if sej else ''} m²", (msej if msej else True) if sej and max(sej) >= 40 else None)
    add(out, "terrain", f"Terrain {terr / 10000:.1f} ha".replace(".", ",") if terr >= 10000 else f"Terrain {round(terr, -2):,.0f} m²".replace(",", " "), terr >= 1500)
    add(out, "soussol", "Sous-sol" if re.search(r"sous-sol|sous sol", t) else "Combles aménageables",
        re.search(r"sous-sol|sous sol|combles? (amenageables?|a amenager)|grenier (amenageable|a amenager)", t))
    add(out, "cheminee", "Cheminée / poêle", f.get("cheminee") or re.search(r"cheminee|insert|poele a (bois|granules)", t))
    add(out, "bureau", "Bureau", re.search(r"\bbureau\b", t))
    add(out, "cachet", "Cachet", re.search(r"cachet|de caractere|en pierre|pierre de taille|longere|maison de maitre|bourgeoise|authentique|tomettes|poutres apparentes|meuliere|annees 30|maison ancienne|charme de l'ancien", t))
    add(eq, "garage", "garage", f.get("garage") or re.search(r"garage", t))
    add(eq, "piscine", "piscine", f.get("piscine") or re.search(r"piscine", t))
    add(eq, "terrasse", "terrasse", f.get("terrasse") or re.search(r"terrasse", t))
    add(eq, "suite", "suite parentale", re.search(r"suite parentale", t))
    add(eq, "plainpied", "plain-pied", re.search(r"plain[- ]pied|chambre (au|en) rez-de-chaussee", t))
    add(eq, "cave", "cave", f.get("cave") or re.search(r"\bcave\b", t))
    add(eq, "veranda", "véranda", re.search(r"veranda", t))
    add(eq, "solaire", "panneaux solaires", re.search(r"panneaux? (solaires|photovoltaiques)|photovoltaique", t))
    add(eq, "volumes", "beaux volumes", re.search(r"beaux volumes|hauteur(s)? sous plafond|volumes? genereux", t))
    return out, eq


def contacts(f):
    d = f.get("description") or ""
    mails = sorted(set(m.lower() for m in re.findall(r"[\w.+-]+@[\w-]+\.[a-z]{2,}(?:\.[a-z]{2,})?", d)))
    tels = sorted(set(re.sub(r"\D", "", m) for m in re.findall(r"0[1-9](?:[ .]?\d{2}){4}", d)))
    return {"emails": mails[:2], "tels": [" ".join(x[i:i+2] for i in range(0, 10, 2)) for x in tels[:2]]}


# ---------- doublons ----------
def bande(f):
    s = f.get("surface") or 0
    return ("v" if village(f["ville"]) else "o") + ("1" if s < 130 else "2" if s < 170 else "3")


def meme_bien(a, b):
    if norm(a["ville"]) != norm(b["ville"]) or not a.get("surface") or not b.get("surface"):
        return False
    if abs(a["surface"] - b["surface"]) > 3:
        return False
    if (a.get("chambres") and b.get("chambres")) and a["chambres"] != b["chambres"]:
        return False
    ta, tb = a.get("terrain") or 0, b.get("terrain") or 0
    if ta and tb and abs(ta - tb) > 0.1 * max(ta, tb):
        return False
    if abs(a["prix"] - b["prix"]) > 0.08 * max(a["prix"], b["prix"]):
        return False
    if a.get("lat") and b.get("lat") and a.get("flou") == b.get("flou") == "disk":
        return km(a["lat"], a["lon"], b["lat"], b["lon"]) < 0.4
    return True


actives = {k: f for k, f in annonces.items() if f.get("active") and f.get("prix")}
groupes = []
for k, f in sorted(actives.items(), key=lambda kv: kv[1]["prix"]):
    for g in groupes:
        if meme_bien(actives[g[0]], f):
            g.append(k); break
    else:
        groupes.append([k])

_tmp = {}
for g in groupes:
    m0 = marche(actives[g[0]])
    if m0:
        _tmp.setdefault(bande(actives[g[0]]), []).append(m0["ecart"])
REF = {b: statistics.median(l) for b, l in _tmp.items() if len(l) >= 5}
print("Écart médian des annonces par bande :", REF)
sortie = []
for g in groupes:
    k = g[0]
    f = dict(actives[k])
    autres = [actives[x] for x in g[1:]]
    for o in autres:  # complète les infos manquantes avec les doublons
        for champ in ("dpe", "terrain", "chambres", "lat", "lon", "flou"):
            if not f.get(champ) and o.get(champ):
                f[champ] = o[champ]
        if len(o.get("description", "")) > len(f.get("description", "")):
            f["description"] = o["description"]
    f["description"] = re.sub(r"<[^>]+>", "\n", f.get("description") or "").replace("&nbsp;", " ")
    f["description"] = re.sub(r"\n\s*\n+", "\n\n", f["description"]).strip()
    t = norm((f.get("titre") or "") + " " + f["description"])
    ch = f.get("chambres") or ((f["pieces"] - 1) if f.get("pieces") else None)
    vil = village(f["ville"])
    niveau, raisons_trav = travaux(f, t)
    vv, indices_vv, lotiss, mitoy = environnement(f, t)
    m = marche(f)

    ecarts = []
    if f["prix"] > BUDGET_MAX:
        ecarts.append(f"Au-dessus du budget ({f['prix']:,} €)".replace(",", " "))
    alertes = []
    if ch is not None and ch < 4:  # signalé, pas écarté (demande du 15/11)
        alertes.append(f"{ch} chambre{'s' if ch > 1 else ''} au lieu de 4" + (" (le bureau peut faire une chambre)" if re.search(r"\bbureau\b", t) else ""))
    if f.get("surface") and f["surface"] < 110:
        ecarts.append(f"{f.get('surface') or '?'} m²")
    if f.get("neuf") or f.get("vendeur") in ("builder", "developer"):
        ecarts.append("Maison neuve / projet de constructeur")
    if re.search(r"vente a terme|viager", t):
        ecarts.append("Vente à terme / viager")
    encheres = bool(re.search(r"immo-interactif|36h immo|encheres", t))
    cite = [v for v in HORS_ZONE if re.search(r"\b" + v.replace("-", "[- ]") + r"\b", t)]
    if cite:
        ecarts.append("Lieu douteux : l'annonce cite " + ", ".join(cite))
    if vil and lotiss:
        ecarts.append("Lotissement (" + ", ".join(lotiss) + ")")
    if vil and mitoy:
        ecarts.append("Mitoyenne (" + ", ".join(mitoy) + ")")

    # Note de correspondance (sur 100)
    corr = 50
    corr += min(ch - 4, 2) * 6 if ch and ch >= 4 else (-10 * (4 - ch) if ch else 0)
    corr += min(((f.get("surface") or 110) - 110) / 10, 5) * 2
    terr = f.get("terrain") or 0
    corr += 12 if terr >= 1500 else 8 if terr >= 800 else 4 if terr >= 400 else 0
    ats, eqs = atouts(f, t)
    corr += min(len(ats), 5) * 4
    corr += {"Sans vis-à-vis (annoncé)": 15, "Probable": 8, "À vérifier": 0, "Douteux": -12}[vv]
    corr += {"A": 6, "B": 6, "C": 4, "D": 2}.get((f.get("dpe") or "").upper(), 0)
    corr = max(0, min(100, round(corr)))

    # Note d'affaire (sur 100)
    hist = f.get("historique", [])
    baisse = (hist and hist[0]["prix"] and hist[-1]["prix"] < hist[0]["prix"]) or f.get("baisse_signalee")
    pub = (f.get("publication") or f.get("premier_vu") or str(TODAY))[:10]
    jours = (TODAY - datetime.date.fromisoformat(pub)).days
    if jours > 3650 or jours < 0:  # date de publication absente ou fantaisiste
        jours = (TODAY - datetime.date.fromisoformat(f.get("premier_vu") or str(TODAY))).days
    urgence = has(t, r"succession", r"urgent", r"a saisir", r"baisse de prix", r"prix revu", r"nouveau prix",
                  r"mutation", r"vente rapide", r"negociable", r"divorce", r"depart a l'etranger")
    aff, signaux = 40, []
    if m:
        aff += max(-30, min(40, -(m["ecart"] - REF.get(bande(f), 0)) * 2))
        if m["ecart"] <= -10:
            signaux.append(f"{-m['ecart']} % sous le prix du marché")
    if encheres:
        aff = min(aff, 50); signaux.append("Vente aux enchères en ligne : le prix affiché est un prix de départ")
    if baisse:
        aff += 10; signaux.append("Prix en baisse")
    if jours > 180:
        aff += 10; signaux.append(f"En vente depuis {jours} jours")
    elif jours > 90:
        aff += 5; signaux.append(f"En vente depuis {jours} jours")
    if urgence:
        aff += 8; signaux.append("Mots-clés : " + ", ".join(u.replace("\\", "") for u in urgence))
    if f.get("vendeur") in ("particulier", "notaire"):
        aff += 5; signaux.append("Vente " + f["vendeur"])
    if niveau.startswith("Gros"):
        signaux.append("Gros travaux : négociation possible")
    aff = max(0, min(100, round(aff)))

    postes = postes_travaux(f, t)
    env = enveloppe_dpe(f)
    bud = budget(f, postes, env, m, jours, baisse, niveau)
    geo = None
    if f.get("lat") and f.get("flou") == "disk":
        geo = f"https://www.geoportail.gouv.fr/carte?c={f['lon']},{f['lat']}&z=19&l0=ORTHOIMAGERY.ORTHOPHOTOS::GEOPORTAIL:OGC:WMTS(1)&permalink=yes"

    sortie.append({
        "id": k, "url": f["url"], "source": f["source"], "titre": f.get("titre"), "ville": f["ville"],
        "prix": f["prix"], "surface": f.get("surface"), "terrain": f.get("terrain"), "chambres": ch,
        "dpe": f.get("dpe"), "annee": f.get("annee"), "vendeur": f.get("vendeur"),
        "photos": f.get("photos", [])[:8], "description": f.get("description", ""),
        "lat": f.get("lat"), "lon": f.get("lon"), "position_precise": f.get("flou") == "disk",
        "vue_aerienne": geo, "historique": hist, "premier_vu": f.get("premier_vu"), "jours_en_ligne": jours,
        "nouveau": f.get("premier_vu") == str(TODAY),
        "travaux": niveau, "travaux_raisons": raisons_trav, "dpe_c": env, "postes": postes, "budget": bud, "dpe_valeur": f.get("dpe_valeur"),
        "atouts": ats, "equipements": eqs, "contact": contacts(f),
        "vis_a_vis": vv, "vis_a_vis_indices": [i.replace("\\", "") for i in indices_vv],
        "marche": m, "note_correspondance": corr, "note_affaire": aff,
        "note": round(0.55 * corr + 0.45 * aff), "signaux": signaux,
        "ecartee": bool(ecarts), "raisons_ecart": ecarts, "alertes": alertes,
        "aussi_sur": [{"source": o["source"], "url": o["url"], "prix": o["prix"]} for o in autres],
    })

sortie.sort(key=lambda x: (x["ecartee"], -x["note"]))
out = {"maj": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "annonces": sortie}
(ROOT / "data/dashboard.json").write_text(json.dumps(out, ensure_ascii=False))
ok = [x for x in sortie if not x["ecartee"]]
print(f"{len(sortie)} biens uniques, {len(ok)} retenus, {sum(x['nouveau'] for x in ok)} nouveaux")
for x in ok[:12]:
    e = x["marche"]["ecart"] if x["marche"] else None
    print(f"{x['note']:3} | {x['ville'][:12]:12} | {x['prix']:>7} € | {x['surface']} m² | {x['chambres']} ch | terrain {x['terrain']} | écart {e}% | {x['travaux']} | {x['vis_a_vis']}")
