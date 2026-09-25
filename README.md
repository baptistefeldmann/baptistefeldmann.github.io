# baptistefeldmann.github.io

Portfolio de Baptiste Feldmann, en français et en anglais : présentation, CV, publications et projets.
Site statique en HTML, CSS et JavaScript, sans framework ni étape de build pour les pages.

En ligne : <https://baptistefeldmann.github.io>

## Structure

```
index.html, cv.html, publications.html, projets.html   pages françaises
en/                                                   pages anglaises (projects.html)
css/style.css                                         styles, thèmes clair et sombre
js/main.js                                            thème, courbes de niveau, filtres
outils/generer_cv.py                                  génération des CV PDF
.github/workflows/publication.yml                     génération des CV et déploiement
```

## Aperçu local

```bash
python3 -m http.server 8000
```

Puis <http://127.0.0.1:8000>.

## CV PDF

Les CV téléchargeables (`assets/CV_Baptiste_Feldmann_FR.pdf` et `_EN.pdf`) sont **générés à partir des pages**
`cv.html`, `en/cv.html`, `index.html` et `publications.html`. Pour modifier le CV, on modifie les pages. Les PDF ne
sont pas versionnés.

Le PDF est conçu pour les ATS : une colonne, du texte réel dans l'ordre de lecture, des titres de section standard,
sans tableau, image ni jauge.

Quelques attributs guident la génération :

| Attribut | Rôle |
|---|---|
| `data-cv="experience"`, `data-cv="education"` | blocs d'étapes repris dans le PDF |
| `data-start="2022-07" data-end=""` | dates d'une étape (`AAAA-MM` ou `AAAA`, fin vide = en cours) |
| `data-cv="skip"` | étape affichée sur le site mais absente du PDF |
| `data-cv="skills"`, `"languages"`, `"interests"` | encarts de la colonne latérale |

Générer les PDF en local :

```bash
python3 -m venv .venv
.venv/bin/pip install -r outils/requirements.txt
.venv/bin/python outils/generer_cv.py
```

## Déploiement

À chaque push sur `main`, GitHub Actions génère les CV, vérifie qu'ils tiennent en deux pages et que leur texte est
lisible, puis publie le site. Réglage à faire une fois dans le dépôt : *Settings → Pages → Source : GitHub Actions*.
