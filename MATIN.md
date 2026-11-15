# Mise à jour : J'aime les beaux volumes

Tourne dans une tâche cloud Claude (8h, 13h, 19h, heure de Paris), à la racine de ce dépôt.
Page : https://claude.ai/code/artifact/2da392fa-d87e-4720-86f2-039d3ab79051

## 0. Préparation
- `git pull --ff-only`
- Si `ffmpeg` est absent : `pip install pillow` (photos.py bascule alors sur Pillow).

## 1. Alertes e-mail (Gmail, lecture seule)
Chercher : `from:(leboncoin.fr OR pap.fr) newer_than:1d`.
Pour chaque annonce de MAISON citée : source (`leboncoin` ou `pap`), url, titre, prix (nombre), ville, cp, surface,
pieces, chambres, terrain, photo (url), description (texte de l'e-mail), vendeur (`particulier` si indiqué, sinon `agency`).
Champ inconnu = null, ne rien inventer. Écrire le tableau JSON dans `data/alertes_gmail.json` (`[]` si rien).
Ne jamais répondre, envoyer, supprimer ou modifier un e-mail. Ne pas ouvrir les pages Leboncoin / PAP.

## 2. Collecte, notation, photos
`bash build.sh`

## 3. Publication
1. Outil Artifact, `action: "read"`, `url` = la page ci-dessus, PUIS `action: "read"` avec `path: "data.json"` (les deux lectures sont obligatoires, sinon la publication est refusée).
2. Outil Artifact, publication : `url` = la page, `file_path` = chemin absolu de `site/index.html`, `root` = chemin absolu de `site`,
   `files` = `data.json` + chaque ligne de `site/nouveaux_fichiers.txt` (254 maximum par envoi ; au-delà, plusieurs envois).
   Ne pas passer `capabilities` ni `icon`.

## 4. Sauvegarde
`git add -A data site && git commit -m "Mise à jour des annonces $(date +%F' '%H:%M)" && git push`
(l'historique des prix vit dans `data/annonces.json` : ne pas sauter cette étape).

## 5. Résumé
Court, en français : nouvelles maisons retenues, les 3 meilleures nouvelles (prix, ville, surface, note, signal principal),
baisses de prix, et toute étape qui a échoué.
