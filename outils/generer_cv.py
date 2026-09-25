#!/usr/bin/env python3
"""Génère les CV PDF (français et anglais) à partir des pages du site.

Les pages HTML sont la seule source du contenu : ce script n'en contient aucun,
seulement la mise en page et les intitulés de section. Modifier le CV, c'est
modifier cv.html / en/cv.html, puis relancer :

    python outils/generer_cv.py

Le PDF produit vise une lecture fiable par les ATS : une seule colonne, aucun
tableau ni image, du texte réel dans l'ordre de lecture, des titres de section
standard et les coordonnées dans le corps du document.
"""

from pathlib import Path
from xml.sax.saxutils import escape

from bs4 import BeautifulSoup, NavigableString, Tag
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer

RACINE = Path(__file__).resolve().parent.parent
SITE = "https://baptistefeldmann.github.io/"

LANGUES = {
    "fr": {
        "dossier": "",
        "sortie": "CV_Baptiste_Feldmann_FR.pdf",
        "lieu": "Rennes, Bretagne, France",
        "aujourdhui": "aujourd'hui",
        "deux_points": " : ",
        "mots_cles": "Mots-clés",
        "titres": {
            "profil": "Profil",
            "experience": "Expérience professionnelle",
            "formation": "Formation",
            "competences": "Compétences techniques",
            "publications": "Publications",
            "langues": "Langues",
            "interets": "Centres d'intérêt",
        },
    },
    "en": {
        "dossier": "en",
        "sortie": "CV_Baptiste_Feldmann_EN.pdf",
        "lieu": "Rennes, Brittany, France",
        "aujourdhui": "Present",
        "deux_points": ": ",
        "mots_cles": "Keywords",
        "titres": {
            "profil": "Profile",
            "experience": "Work experience",
            "formation": "Education",
            "competences": "Technical skills",
            "publications": "Publications",
            "langues": "Languages",
            "interets": "Interests",
        },
    },
}

# Types de publications retenus dans le PDF (les conférences et mémoires restent sur le site)
PUBLICATIONS_RETENUES = {"article", "chapter"}

ENCRE = colors.HexColor("#1c2a35")
ENCRE_DOUCE = colors.HexColor("#52616b")
ACCENT = colors.HexColor("#c0502a")
FILET = colors.HexColor("#c9c3b6")


# ---------- Lecture du HTML ----------

def lire(chemin):
    return BeautifulSoup((RACINE / chemin).read_text(encoding="utf-8"), "html.parser")


def texte(el):
    """Texte brut d'un élément, espaces normalisés."""
    return " ".join(el.get_text().split())


def balisage(el):
    """Convertit le contenu d'un élément HTML en balisage Paragraph de reportlab
    (gras, italique et liens conservés, le reste réduit à son texte)."""
    morceaux = []
    for enfant in el.children:
        if isinstance(enfant, NavigableString):
            morceaux.append(escape(str(enfant)))
        elif isinstance(enfant, Tag):
            interieur = balisage(enfant)
            if enfant.name in ("strong", "b"):
                morceaux.append(f"<b>{interieur}</b>")
            elif enfant.name in ("em", "i"):
                morceaux.append(f"<i>{interieur}</i>")
            elif enfant.name == "a" and enfant.get("href", "").startswith("http"):
                morceaux.append(f'<a href="{escape(enfant["href"])}" color="#1c2a35">{interieur}</a>')
            else:
                morceaux.append(interieur)
    return " ".join("".join(morceaux).split())


def periode(li, conf):
    def fmt(d):
        return f"{d[5:7]}/{d[:4]}" if len(d) == 7 else d
    debut, fin = li.get("data-start", ""), li.get("data-end", "")
    return f"{fmt(debut)} – {fmt(fin) if fin else conf['aujourdhui']}"


def organisme(li):
    """« Siradel · Saint-Grégoire, Bretagne » → « Siradel, Saint-Grégoire, Bretagne »."""
    return ", ".join(p.strip() for p in texte(li.select_one(".waypoint__org")).split("·") if p.strip())


def etapes(soup, section, conf):
    for li in soup.select(f'[data-cv="{section}"] .waypoint'):
        if li.get("data-cv") == "skip":
            continue
        puces = [balisage(x) for x in li.select("ul:not(.tags) > li")]
        description = [balisage(p) for p in li.find_all("p", recursive=False)
                       if "waypoint__org" not in (p.get("class") or [])]
        yield {
            "titre": texte(li.find("h3")),
            "organisme": organisme(li),
            "periode": periode(li, conf),
            "puces": puces,
            "description": description,
            "mots_cles": [texte(t) for t in li.select(".tags .tag")],
        }


def extraire(conf):
    d = conf["dossier"]
    accueil = lire(Path(d, "index.html"))
    cv = lire(Path(d, "cv.html"))
    pubs = lire(Path(d, "publications.html"))

    liens = {a.get_text(strip=True): a["href"] for a in accueil.select(".footer-links a")}
    courriel = next(a["href"].removeprefix("mailto:") for a in accueil.select('.footer-links a[href^="mailto:"]'))

    publications = []
    for art in pubs.select(".pub"):
        if art.get("data-type") not in PUBLICATIONS_RETENUES:
            continue
        doi = next((a["href"] for a in art.select(".pub__links a") if a.get_text(strip=True) == "DOI"), None)
        publications.append({
            "annee": texte(art.select_one(".pub__year")),
            "auteurs": balisage(art.select_one(".pub__authors")),
            "titre": texte(art.find("h3")),
            "support": balisage(art.select_one(".pub__venue")),
            "doi": doi,
        })

    return {
        "nom": texte(accueil.find("h1")),
        "poste": texte(accueil.select_one(".hero__role")),
        "profil": [texte(accueil.select_one(".about .lead")), texte(accueil.select_one(".hero__lead"))],
        "courriel": courriel,
        "linkedin": liens["LinkedIn"],
        "github": liens["GitHub"],
        "site": SITE + (f"{d}/" if d else ""),
        "experiences": list(etapes(cv, "experience", conf)),
        "formations": list(etapes(cv, "education", conf)),
        "competences": [(texte(g.find("h3")), texte(g.find("p"))) for g in cv.select('[data-cv="skills"] .legend__group')],
        "langues": [balisage(p) for p in cv.select('[data-cv="languages"] p.note')],
        "interets": [balisage(p) for p in cv.select('[data-cv="interests"] p.note')],
        "publications": publications,
    }


# ---------- Mise en page ----------

def styles():
    base = dict(fontName="Helvetica", fontSize=9.5, leading=12.8, textColor=ENCRE, alignment=TA_LEFT)
    return {
        "nom": ParagraphStyle("nom", **{**base, "fontName": "Helvetica-Bold", "fontSize": 20, "leading": 24}),
        "poste": ParagraphStyle("poste", **{**base, "fontSize": 11.5, "leading": 15, "textColor": ACCENT}),
        "contact": ParagraphStyle("contact", **{**base, "fontSize": 9, "leading": 12.5, "textColor": ENCRE_DOUCE}),
        "section": ParagraphStyle("section", **{**base, "fontName": "Helvetica-Bold", "fontSize": 10.5,
                                                "leading": 13, "textColor": ACCENT, "spaceBefore": 11}),
        "titre": ParagraphStyle("titre", **{**base, "fontName": "Helvetica-Bold", "fontSize": 10.2, "leading": 13}),
        "meta": ParagraphStyle("meta", **{**base, "fontSize": 9, "textColor": ENCRE_DOUCE, "spaceAfter": 2}),
        "corps": ParagraphStyle("corps", **base),
        "puce": ParagraphStyle("puce", **{**base, "leftIndent": 11, "bulletIndent": 1, "spaceAfter": 1.5}),
        "mots": ParagraphStyle("mots", **{**base, "fontSize": 8.6, "textColor": ENCRE_DOUCE, "spaceBefore": 1}),
    }


def section(titre, st):
    return [
        Paragraph(escape(titre.upper()), st["section"]),
        HRFlowable(width="100%", thickness=0.6, color=FILET, spaceBefore=2, spaceAfter=5),
    ]


def lien(url, st_couleur="#52616b"):
    visible = url.removeprefix("https://").removeprefix("www.").rstrip("/")
    return f'<a href="{escape(url)}" color="{st_couleur}">{escape(visible)}</a>'


def construire(donnees, conf, chemin):
    st = styles()
    t = conf["titres"]
    sep = conf["deux_points"]
    elements = [
        Paragraph(escape(donnees["nom"]), st["nom"]),
        Paragraph(escape(donnees["poste"]), st["poste"]),
        Paragraph(escape(conf["lieu"]) + " | "
                  + f'<a href="mailto:{donnees["courriel"]}" color="#52616b">{escape(donnees["courriel"])}</a>',
                  st["contact"]),
        Paragraph(" | ".join(lien(u) for u in (donnees["linkedin"], donnees["github"], donnees["site"])), st["contact"]),
    ]

    elements += section(t["profil"], st)
    elements += [Paragraph(" ".join(escape(p) for p in donnees["profil"]), st["corps"])]

    def bloc(e):
        contenu = [
            Paragraph(escape(e["titre"]), st["titre"]),
            Paragraph(f'{escape(e["organisme"])} | {escape(e["periode"])}', st["meta"]),
        ]
        contenu += [Paragraph(p, st["corps"]) for p in e["description"]]
        contenu += [Paragraph(p, st["puce"], bulletText="•") for p in e["puces"]]
        if e["mots_cles"]:
            contenu.append(Paragraph(f'{conf["mots_cles"]}{sep}' + escape(", ".join(e["mots_cles"])), st["mots"]))
        return [KeepTogether(contenu), Spacer(1, 6)]

    elements += section(t["experience"], st)
    for e in donnees["experiences"]:
        elements += bloc(e)

    elements += section(t["formation"], st)
    for e in donnees["formations"]:
        elements += bloc(e)

    elements += section(t["competences"], st)
    elements += [Paragraph(f"<b>{escape(g)}</b>{sep}{escape(outils)}", st["puce"], bulletText="•")
                 for g, outils in donnees["competences"]]

    elements += section(t["publications"], st)
    for p in donnees["publications"]:
        ref = f'{p["auteurs"]} ({escape(p["annee"])}). {escape(p["titre"])}. {p["support"]}.'
        if p["doi"]:
            ref += f' <a href="{escape(p["doi"])}" color="#52616b">doi:{escape(p["doi"].removeprefix("https://doi.org/"))}</a>'
        elements.append(Paragraph(ref, st["puce"], bulletText="•"))

    elements += section(t["langues"], st)
    elements += [Paragraph(p, st["puce"], bulletText="•") for p in donnees["langues"]]

    elements += section(t["interets"], st)
    elements += [Paragraph(p, st["puce"], bulletText="•") for p in donnees["interets"]]

    mots_cles = sorted({m for e in donnees["experiences"] for m in e["mots_cles"]})
    doc = SimpleDocTemplate(
        str(chemin), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title=f'CV — {donnees["nom"]} — {donnees["poste"]}',
        author=donnees["nom"],
        subject=donnees["poste"],
        keywords=", ".join(mots_cles),
        creator=SITE,
    )
    doc.build(elements)


def main():
    for code, conf in LANGUES.items():
        chemin = RACINE / "assets" / conf["sortie"]
        construire(extraire(conf), conf, chemin)
        print(f"{code} → {chemin.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
