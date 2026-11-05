#!/usr/bin/env python3
"""
Synchronise automatiquement les dépôts en production de @Mrthomaslef qui concernent Marie
et génère `projects.json` avec leurs titres, descriptions, catégories, vrais logos officiels et URLs live.
Exclut strictement les applications réservées à la radiologie Cochin, aux internes, au suivi IA,
ainsi que MediCalc, TomatoCalc, ColisTrack, Forestia et Holidamn.
"""
from __future__ import annotations
import json
import os
import re
import urllib.request

GITHUB_USERNAME = "Mrthomaslef"

# Applications exclues du Mapp Store
EXCLUDED_REPOS = {
    "allinone",
    "mapp-store",
    "gemini-ultra",
    "news-ai",
    "biblioosteo",
    "agenda-cochin",
    "agenda-internes",
    "guide-interne-cochin-os",
    "guide-infiltration",
    "archive-des-internes",
    "quiz-imagerie",
    "radio-thomas",
    "dicomviewer",
    "tpack-cases",
    "m4-gaming",
    "medicalc",
    "tomatocalc",
    "colistrack",
    "forestia-mobile",
    "holidamn",
}

KNOWN_METADATA = {
    "film-et-serie": {
        "title": "CinePreload — Films & Séries (Stremio + TorBox)",
        "subtitle": "Préchargement local 4K/VF des films et séries sur le Mac mini du salon",
        "category": "famille-quotidien",
        "emoji": "🎬",
        "prodUrl": "https://mrthomaslef.github.io/allinone/film-et-serie/",
        "logoUrl": "https://mrthomaslef.github.io/allinone/film-et-serie/assets/icon.svg?v=2",
    },
    "biblio-marie": {
        "title": "BiblioMarie — Infectiologie pédiatrique",
        "subtitle": "Le Carnet de Marie — veille bibliographique pédiatrie & infectiologie, résumés en français",
        "category": "pediatrie-clinique",
        "emoji": "🧸",
        "logoUrl": "https://mrthomaslef.github.io/biblio-marie/assets/apple-touch-icon.png",
    },
    "agenda-famille": {
        "title": "Agenda Famille — Marie & Thomas",
        "subtitle": "Planning partagé, gardes, relais Émile & indisponibilités à la maison",
        "category": "famille-quotidien",
        "emoji": "🏡",
        "logoUrl": "https://mrthomaslef.github.io/agenda-famille/icon.svg",
    },
    "restaurant": {
        "title": "Resto en Amoureux — Marie & Thomas",
        "subtitle": "Créneaux libres M&T + Émile chez les grands-parents & Réservation auto",
        "category": "famille-quotidien",
        "emoji": "🍷",
        "logoUrl": "https://mrthomaslef.github.io/restaurant/assets/icon.svg",
    },
    "photo-famille": {
        "title": "Album Famille Fontenay — WhatsApp",
        "subtitle": "1 432 photos de famille classées par thème (Émile, Étretat/Yport/Corse, Ski, Fêtes & Messages)",
        "category": "famille-quotidien",
        "emoji": "📸",
        "logoUrl": "https://mrthomaslef.github.io/photo-famille/apple-touch-icon.png",
    },
    "voyages-voyages": {
        "title": "Voyages • Voyages — Hub & Cartes",
        "subtitle": "Cartes Avantage SNCF & Air France Week-End+ (Marie & Thomas), Vacances & Guichet Express",
        "category": "famille-quotidien",
        "emoji": "✈️",
        "logoUrl": "https://mrthomaslef.github.io/voyages-voyages/assets/icon.svg",
    },
    "assistante-maternelle": {
        "title": "AssMat — Paie & Pajemploi",
        "subtitle": "Calculateur de salaire, présence d'Émile chez Mabrouka, congés & fiche de paie",
        "category": "famille-quotidien",
        "emoji": "👶",
        "logoUrl": "https://mrthomaslef.github.io/assistante-maternelle/apple-touch-icon.png",
    },
    "dinociel-app-educative": {
        "title": "DinoCiel — Petit Dino",
        "subtitle": "App éducative interactive pour Émile (3 ans) avec Petit Dino animé",
        "category": "emile-loisirs",
        "emoji": "🦕",
        "logoUrl": "https://mrthomaslef.github.io/dinociel-app-educative/assets/dino-emotion-happy.jpg",
    },
    "pocket-tcg-family": {
        "title": "milTCG — Pocket Family",
        "subtitle": "Ouverture de boosters & collection de cartes personnalisées en famille",
        "category": "emile-loisirs",
        "emoji": "🃏",
        "logoUrl": "https://mrthomaslef.github.io/pocket-tcg-family/apple-touch-icon.png",
    },
    "quiz-trentenaires": {
        "title": "QUIZ du 7TER",
        "subtitle": "Grand Quiz Show multijoueur (2 couples / 4 joueurs)",
        "category": "emile-loisirs",
        "emoji": "🎉",
        "logoUrl": "https://mrthomaslef.github.io/quiz-trentenaires/apple-touch-icon.png",
    },
    "monopoly": {
        "title": "Jolly Roger's — Monopoly 3D",
        "subtitle": "Jeu de plateau Monopoly 3D des Caraïbes (Batailles navales, Îles & Trésors)",
        "category": "emile-loisirs",
        "emoji": "🏴‍☠️",
        "logoUrl": "https://mrthomaslef.github.io/monopoly/assets/pirate_logo.png",
    },
    "quiz-pokemon": {
        "title": "PokéQuiz — Attrape-les tous !",
        "subtitle": "Quiz interactif pour apprendre les noms des Pokémon (Générations 1 à 3)",
        "category": "emile-loisirs",
        "emoji": "⚡",
        "logoUrl": "https://mrthomaslef.github.io/quiz-pokemon/apple-touch-icon.png",
    },
}


def is_excluded_repo(name: str, description: str, topics: list[str]) -> bool:
    key = name.lower()
    if key in EXCLUDED_REPOS:
        return True
    t_list = [t.lower() for t in (topics or [])]
    text = f"{name} {description or ''} {' '.join(t_list)}".lower()
    if re.search(
        r"(cochin|osteo|ostéo|dicom|pacs|tpack|interne|irm|scanner|infiltration|tomatocalc|medicalc|colistrack|forestia|holidamn)",
        text,
    ):
        return True
    return False


def classify_repo(name: str, description: str, topics: list[str]) -> tuple[str, str]:
    t_list = [t.lower() for t in (topics or [])]
    text = f"{name} {description or ''} {' '.join(t_list)}".lower()
    if re.search(r"(marie|pediatr|pédiatr|infectio)", text):
        return "pediatrie-clinique", "🧸"
    if re.search(
        r"(quiz|tcg|game|jeu|carte|soiree|soirée|blindtest|monopoly|pirate|plunder|pokemon|poké|dino|enfant|emile|émile|plateau|board|arcade)",
        text,
    ):
        return "emile-loisirs", "🦕"
    return "famille-quotidien", "🏡"


def main():
    headers = {
        "User-Agent": "mappstore-sync/1.0",
        "Accept": "application/vnd.github+json",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        f"https://api.github.com/users/{GITHUB_USERNAME}/repos?per_page=100&sort=pushed",
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        repos = json.loads(r.read().decode("utf-8"))

    output = []
    for repo in repos:
        name = repo.get("name")
        if not name:
            continue
        key = name.lower()
        desc = repo.get("description") or ""
        topics = repo.get("topics") or []

        if is_excluded_repo(name, desc, topics):
            continue

        known = KNOWN_METADATA.get(key)
        homepage = (repo.get("homepage") or "").strip()
        has_pages = bool(repo.get("has_pages"))

        if not (has_pages or homepage.startswith("http") or known):
            continue

        prod_url = (
            homepage
            if homepage.startswith("http")
            else (known.get("prodUrl") if known and known.get("prodUrl") else f"https://{GITHUB_USERNAME.lower()}.github.io/{name}/")
        )

        auto_cat, auto_emoji = classify_repo(name, desc, topics)
        title = known["title"] if known and known.get("title") else name.replace("-", " ").title()
        logo_url = (
            known["logoUrl"]
            if known and known.get("logoUrl")
            else f"{prod_url.rstrip('/')}/apple-touch-icon.png"
        )
        subtitle = known["subtitle"] if known else (desc or "Application familiale en production")

        output.append(
            {
                "id": name,
                "title": title,
                "subtitle": subtitle,
                "category": known["category"] if known else auto_cat,
                "emoji": known["emoji"] if known else auto_emoji,
                "logoUrl": logo_url,
                "prodUrl": prod_url,
                "githubUrl": repo.get("html_url") or f"https://github.com/{GITHUB_USERNAME}/{name}",
                "pushedAt": repo.get("pushed_at") or repo.get("updated_at"),
            }
        )

    if not any(item["id"].lower() == "film-et-serie" for item in output):
        output.insert(
            0,
            {
                "id": "film-et-serie",
                "title": "CinePreload — Films & Séries (Stremio + TorBox)",
                "subtitle": "Préchargement local 4K/VF des films et séries sur le Mac mini du salon",
                "category": "famille-quotidien",
                "emoji": "🎬",
                "logoUrl": "https://mrthomaslef.github.io/allinone/film-et-serie/assets/icon.svg?v=2",
                "prodUrl": "https://mrthomaslef.github.io/allinone/film-et-serie/",
                "githubUrl": f"https://github.com/{GITHUB_USERNAME}/allinone/tree/main/film-et-serie",
                "pushedAt": output[0]["pushedAt"] if output else None,
            },
        )

    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Synced {len(output)} Marie apps into projects.json")


if __name__ == "__main__":
    main()
