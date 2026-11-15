# Mise à jour du matin : Maison Orléans-Loges

Dossier : `/Users/julienbh/cl/maison-orleans/`
Page : https://claude.ai/code/artifact/2da392fa-d87e-4720-86f2-039d3ab79051

## 1. Alertes e-mail (Gmail)
Chercher dans Gmail les alertes des 2 derniers jours :
`from:(leboncoin.fr OR pap.fr) newer_than:2d`
Pour chaque annonce de maison citée dans ces e-mails, extraire : source (`leboncoin` ou `pap`), url de l'annonce,
titre, prix (nombre), ville, cp, surface, pieces, chambres, terrain, photo (url de l'image), description (texte de l'e-mail
s'il y en a), vendeur (`particulier` si indiqué, sinon `agency` pour un pro). Champ inconnu = null. NE PAS inventer.
Écrire la liste dans `data/alertes_gmail.json` (tableau JSON). Si aucun e-mail : écrire `[]`.
Ne pas ouvrir les pages Leboncoin / PAP (bloquées aux robots), ne pas répondre aux e-mails, ne rien supprimer.

## 2. Collecte, notation, photos
`./build.sh` (Bien'ici, notaires, alertes, DVF, notation, photos, `site/data.json`).

## 3. Publication
Republier la page avec l'outil Artifact :
- `file_path` : `/Users/julienbh/cl/maison-orleans/site/index.html`
- `url` : l'adresse de la page ci-dessus (lire la page avec `action: "read"` d'abord si la session ne l'a pas encore lue)
- `root` : `/Users/julienbh/cl/maison-orleans/site`
- `files` : `data.json` + chaque ligne de `site/nouveaux_fichiers.txt` (bandeaux photo nouveaux, 254 max par envoi)
- ne pas passer `capabilities` ni `icon`.

## 4. Résumé
Terminer par un résumé court en français : nombre de nouvelles maisons retenues, les 3 meilleures nouvelles
(prix, ville, surface, note, signal principal), baisses de prix sur les maisons déjà vues.
