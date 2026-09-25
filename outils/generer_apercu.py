#!/usr/bin/env python3
"""Génère les images d'aperçu (Open Graph) du site, affichées par LinkedIn et les messageries.

    python outils/generer_apercu.py        # écrit assets/apercu_fr.png et assets/apercu_en.png

Le relief reprend exactement celui de la page d'accueil (même bruit, même graine que js/main.js), dessiné à
quadruple résolution puis réduit en 2400 × 1254 pour lisser les traits. Les traits et les textes sont
volontairement plus épais que sur le site : LinkedIn affiche l'aperçu vers 550 px de large et le recompresse. Les images produites sont versionnées : ce script ne sert
qu'à les régénérer si le titre ou le style changent.
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RACINE = Path(__file__).resolve().parent.parent
L, H = 1200, 627          # format recommandé par LinkedIn (1,91:1), en unités de dessin
SORTIE = 2                # image livrée en 2400 × 1254 : reste nette une fois réduite par LinkedIn
K = 4                     # suréchantillonnage du dessin avant réduction

PAPIER, PAPIER_3 = "#f2ede1", "#fbf8f1"
ENCRE, ENCRE_DOUCE = (28, 42, 53), (82, 97, 107)
COURBE, EAU, ACCENT = (169, 121, 74), (45, 106, 136), (192, 80, 42)

POLICES = {
    "titre": ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", 0),
    "mono": ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 0),
    "sans": ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0),
}

TEXTES = {
    "fr": {
        "etiquette": ("FEUILLE 01 · PORTFOLIO", "RENNES · 2026"),
        "poste": "Ingénieur data géospatiale · GeoAI · MLOps",
        "accroche": "Pipelines de données géospatiales, deep learning et LiDAR",
        "sections": "CV · Publications · Projets",
        "ouest": "O",
    },
    "en": {
        "etiquette": ("SHEET 01 · PORTFOLIO", "RENNES · 2026"),
        "poste": "Geospatial Data Engineer · GeoAI · MLOps",
        "accroche": "Geospatial data pipelines, deep learning and LiDAR",
        "sections": "Résumé · Publications · Projects",
        "ouest": "W",
    },
}


def police(nom, taille):
    chemin, index = POLICES[nom]
    return ImageFont.truetype(chemin, int(taille * K), index=index)


# ---------- Relief : portage exact du bruit de js/main.js ----------

def champ(graine, echelle):
    M = 0xFFFFFFFF

    def imul(a, b):
        return ((a & M) * (b & M)) & M

    def hachage(x, y):
        h = (graine ^ imul(x, 374761393) ^ imul(y, 668265263)) & M
        h = imul(h ^ (h >> 13), 1274126177)
        h ^= h >> 16
        return h / 4294967296

    def lisse(t):
        return t * t * (3 - 2 * t)

    def bruit(x, y):
        ix, iy = math.floor(x), math.floor(y)
        fx, fy = lisse(x - ix), lisse(y - iy)
        a, b = hachage(ix, iy), hachage(ix + 1, iy)
        c, d = hachage(ix, iy + 1), hachage(ix + 1, iy + 1)
        return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy

    def f(px, py):
        x, y, amp, somme, norme = px / echelle, py / echelle, 1.0, 0.0, 0.0
        for _ in range(4):
            somme += amp * bruit(x, y)
            norme += amp
            amp *= 0.5
            x, y = x * 2.03 + 17.3, y * 2.03 + 5.7
        return somme / norme

    return f


SEGMENTS = [[], [3, 2], [2, 1], [3, 1], [0, 1], [3, 0, 2, 1], [0, 2], [3, 0],
            [3, 0], [0, 2], [0, 1, 3, 2], [0, 1], [3, 1], [2, 1], [3, 2], []]


def courbes(grille, cols, rangs, cellule, niveau):
    """Marching squares : segments de la courbe de niveau `niveau`, en pixels de l'image finale."""
    for j in range(rangs):
        for i in range(cols):
            a, b = grille[j][i], grille[j][i + 1]
            c, d = grille[j + 1][i + 1], grille[j + 1][i]
            idx = (a > niveau) << 3 | (b > niveau) << 2 | (c > niveau) << 1 | (d > niveau)
            if idx in (0, 15):
                continue
            x0, y0 = i * cellule, j * cellule

            def pt(e):
                if e == 0:
                    return x0 + (niveau - a) / (b - a) * cellule, y0
                if e == 1:
                    return x0 + cellule, y0 + (niveau - b) / (c - b) * cellule
                if e == 2:
                    return x0 + (niveau - d) / (c - d) * cellule, y0 + cellule
                return x0, y0 + (niveau - a) / (d - a) * cellule

            s = SEGMENTS[idx]
            for n in range(0, len(s), 2):
                yield pt(s[n]), pt(s[n + 1])


def relief(graine=7, echelle=430, cellule=5, n_niveaux=16):
    f = champ(graine, echelle)
    cols, rangs = math.ceil(L / cellule), math.ceil(H / cellule)
    grille = [[f(i * cellule, j * cellule) for i in range(cols + 1)] for j in range(rangs + 1)]
    mini = min(map(min, grille))
    maxi = max(map(max, grille))
    etendue = maxi - mini or 1
    eau = mini + etendue * 0.14

    img = Image.new("RGBA", (L * K, H * K), (0, 0, 0, 0))

    # Plans d'eau : masque basse résolution agrandi et lissé
    masque = Image.new("L", (cols + 1, rangs + 1))
    masque.putdata([46 if v < eau else 0 for rang in grille for v in rang])
    masque = masque.resize(((cols + 1) * cellule * K, (rangs + 1) * cellule * K), Image.BILINEAR)
    nappe = Image.new("RGBA", masque.size, EAU + (0,))
    nappe.putalpha(masque)
    img.alpha_composite(nappe, (-cellule * K // 2, -cellule * K // 2))

    def tracer(niveau, couleur, alpha, epaisseur):
        calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
        dessin = ImageDraw.Draw(calque)
        for p, q in courbes(grille, cols, rangs, cellule, niveau):
            dessin.line([(p[0] * K, p[1] * K), (q[0] * K, q[1] * K)], fill=couleur + (int(255 * alpha),),
                        width=max(1, round(epaisseur * K)))
        img.alpha_composite(calque)

    for l in range(1, n_niveaux + 1):
        niveau = mini + etendue * l / (n_niveaux + 1)
        if niveau < eau:
            continue
        maitresse = l % 5 == 0
        tracer(niveau, COURBE, 0.9 if maitresse else 0.5, 2.0 if maitresse else 1.1)
    tracer(eau, EAU, 0.8, 1.5)
    return img


# ---------- Habillage cartographique ----------

def cadre(dessin, marge=18, bande=6, pas=48):
    x0, y0, x1, y1 = marge * K, marge * K, (L - marge) * K, (H - marge) * K
    b, p = bande * K, pas * K
    dessin.rectangle([x0, y0, x1, y1], outline=ENCRE, width=round(1.5 * K))
    dessin.rectangle([x0 + b, y0 + b, x1 - b, y1 - b], outline=ENCRE, width=round(1.5 * K))
    for x in range(x0, x1, 2 * p):
        dessin.rectangle([x, y0, min(x + p, x1), y0 + b], fill=ENCRE)
        dessin.rectangle([x, y1 - b, min(x + p, x1), y1], fill=ENCRE)
    for y in range(y0, y1, 2 * p):
        dessin.rectangle([x0, y, x0 + b, min(y + p, y1)], fill=ENCRE)
        dessin.rectangle([x1 - b, y, x1, min(y + p, y1)], fill=ENCRE)


def etiquette(dessin, xy, texte, ancre, fonte):
    boite = dessin.textbbox(xy, texte, font=fonte, anchor=ancre)
    dessin.rectangle([boite[0] - 6 * K, boite[1] - 3 * K, boite[2] + 6 * K, boite[3] + 3 * K], fill=PAPIER)
    dessin.text(xy, texte, font=fonte, fill=ENCRE_DOUCE, anchor=ancre)


def fleche_nord(dessin, cx, haut):
    s = K
    dessin.text((cx * s, haut * s), "N", font=police("mono", 16), fill=ENCRE, anchor="mt")
    pointe, bas, milieu = (cx * s, (haut + 20) * s), (haut + 64) * s, (haut + 54) * s
    contour = [pointe, ((cx + 11) * s, bas), (cx * s, milieu), ((cx - 11) * s, bas)]
    dessin.polygon(contour, outline=ENCRE, width=round(2 * s))
    dessin.polygon([pointe, (cx * s, milieu), ((cx - 11) * s, bas)], fill=ENCRE)


def barre_echelle(dessin, x, y, largeur=170):
    s, n = K, 4
    for i in range(n):
        x0 = x + i * largeur / n
        dessin.rectangle([x0 * s, y * s, (x0 + largeur / n) * s, (y + 9) * s],
                         fill=ENCRE if i % 2 == 0 else PAPIER_3, outline=ENCRE, width=round(1.5 * s))
    fonte = police("mono", 14)
    for texte, dx in (("0", 0), ("1", largeur / 2), ("2 km", largeur)):
        dessin.text(((x + dx) * s, (y + 14) * s), texte, font=fonte, fill=ENCRE_DOUCE, anchor="mt")


def cartouche(img, t):
    x, y, w, h = 78, 138, 700, 352
    s = K
    ombre = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ombre).rectangle([(x + 6) * s, (y + 20) * s, (x + w - 6) * s, (y + h + 18) * s],
                                    fill=(0, 0, 0, 70))
    img.alpha_composite(ombre.filter(ImageFilter.GaussianBlur(18 * s)))

    d = ImageDraw.Draw(img)
    d.rectangle([(x - 6) * s, (y - 6) * s, (x + w + 6) * s, (y + h + 6) * s], outline=ENCRE, width=round(1.5 * s))
    d.rectangle([x * s, y * s, (x + w) * s, (y + h) * s], fill=PAPIER_3, outline=ENCRE, width=round(1.5 * s))

    px, py = x + 40, y + 34
    mono = police("mono", 15)
    gauche, droite = t["etiquette"]
    d.text((px * s, py * s), gauche, font=mono, fill=ENCRE_DOUCE, anchor="lt")
    d.text(((x + w - 40) * s, py * s), droite, font=mono, fill=ENCRE_DOUCE, anchor="rt")
    d.line([(px * s, (py + 28) * s), ((x + w - 40) * s, (py + 28) * s)], fill=(210, 204, 192), width=round(1.5 * s))

    d.text((px * s, (py + 52) * s), "Baptiste Feldmann", font=police("titre", 60), fill=ENCRE, anchor="lt")
    d.text((px * s, (py + 150) * s), t["poste"], font=police("mono", 20), fill=ACCENT, anchor="lt")
    d.text((px * s, (py + 188) * s), t["accroche"], font=police("sans", 19), fill=ENCRE_DOUCE, anchor="lt")

    base = y + h - 46
    d.rectangle([px * s, (base - 7) * s, (px + 14) * s, (base + 7) * s], fill=ACCENT)
    d.text(((px + 26) * s, base * s), "baptistefeldmann.github.io", font=police("mono", 19), fill=ENCRE,
           anchor="lm")
    d.text(((x + w - 40) * s, base * s), t["sections"], font=police("mono", 15), fill=ENCRE_DOUCE, anchor="rm")


def generer(langue):
    t = TEXTES[langue]
    img = Image.new("RGBA", (L * K, H * K), PAPIER)
    # Graticule sur un calque : dessiner une couleur semi-transparente directement remplacerait le pixel
    grille = Image.new("RGBA", img.size, (0, 0, 0, 0))
    g = ImageDraw.Draw(grille)
    for gx in range(0, L, 80):
        g.line([(gx * K, 0), (gx * K, H * K)], fill=ENCRE + (18,), width=round(1.5 * K))
    for gy in range(0, H, 80):
        g.line([(0, gy * K), (L * K, gy * K)], fill=ENCRE + (18,), width=round(1.5 * K))
    img.alpha_composite(grille)

    img.alpha_composite(relief())
    d = ImageDraw.Draw(img)
    cadre(d)
    mono = police("mono", 15)
    o = t["ouest"]
    etiquette(d, (36 * K, 38 * K), f"48°09′36″N · 1°45′36″{o}", "lt", mono)
    etiquette(d, ((L - 36) * K, 38 * K), f"48°09′36″N · 1°36′00″{o}", "rt", mono)
    etiquette(d, (36 * K, (H - 38) * K), f"48°04′12″N · 1°45′36″{o}", "lb", mono)
    fleche_nord(d, L - 70, 66)
    barre_echelle(d, L - 230, H - 72)
    cartouche(img, t)

    sortie = RACINE / "assets" / f"apercu_{langue}.png"
    img.convert("RGB").resize((L * SORTIE, H * SORTIE), Image.LANCZOS).save(sortie, optimize=True)
    print(f"{langue} → {sortie.relative_to(RACINE)} ({sortie.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    for langue in TEXTES:
        generer(langue)
