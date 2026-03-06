from os import environ
import json
from groq import Groq

MODEL = "llama-3.3-70b-versatile"


def get_groq_client():
    """Crée un client Groq si la clé API est dispo, sinon None."""
    api_key = environ.get("groq_API_key")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def is_groq_available():
    """Vérifie si on a une clé Groq dans le .env."""
    return bool(environ.get("groq_API_key"))


def chat(system_prompt, user_prompt, max_tokens=1024):
    """
    Envoie un message au LLM et retourne sa réponse.
    Si ça plante (pas de clé, erreur réseau...) → None.
    """
    client = get_groq_client()
    if not client:
        return None
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[Groq] Erreur : {e}")
        return None


def analyze_music_profile(top_tracks, top_artists):
    """
    L'IA analyse les goûts musicaux de l'utilisateur et en fait
    un portrait (drôle et un peu méchant) en français.
    """
    system = (
        "Tu es un expert musical passionné. Tu analyses les goûts musicaux des gens "
        "à partir de leurs écoutes Spotify. Réponds en français, de manière drôle et piquante "
        "(avec des jeux de mots si possible). "
        "Sois clair et précis, mais moque-toi de leurs goûts (max 300 mots, sois incisif). "
        "Tu peux être méchant si les goûts sont vraiment mauvais, mais toujours drôle. "
        "Si les goûts sont bons, taquine quand même. "
        "L'objectif : une analyse honnête mais divertissante." \
        "après les grosses blague/jeux de mots importants ajoute '(😬), par ce que tu n'es pas très drôle   "
    )

    tracks_text = "\n".join(
        f"- {t['name']} par {t['artist']}" for t in top_tracks[:30]
    )
    artists_text = "\n".join(
        f"- {a['name']} (genres: {', '.join(a.get('genres', [])[:4]) or 'inconnu'})"
        for a in top_artists[:20]
    )

    user = (
        f"Voici les top morceaux de cet utilisateur :\n{tracks_text}\n\n"
        f"Et ses artistes favoris :\n{artists_text}\n\n"
        "Fais une analyse de son profil musical : genres dominants, "
        "type d'auditeur, personnalité musicale. "
        "Moque-toi avec des jeux de mots. Max 300 mots."
    )

    return chat(system, user)


def generate_playlist_description(playlist_name, tracks, mood):
    """
    Génère une petite description fun pour une playlist.
    1-2 phrases max, 150 caractères max.
    """
    system = (
        "Tu génères des descriptions de playlists Spotify. "
        "Réponds en français, UNE ou DEUX phrases maximum. "
        "Sois créatif et accrocheur. Ne dépasse jamais 150 caractères."
    )

    tracks_text = ", ".join(track_label(t) for t in tracks[:8])
    user = (
        f"Playlist : « {playlist_name} »\n"
        f"Morceaux : {tracks_text}\n"
        f"{('Humeur : ' + mood) if mood else ''}\n"
        "Génère une description courte et fun."
    )

    return chat(system, user, max_tokens=100)


def suggest_discoveries(top_tracks, top_artists):
    """
    Propose 5 artistes ou albums que l'utilisateur ne connaît
    probablement pas mais qu'il pourrait kiffer.
    """
    system = (
        "Tu es un conseiller musical expert. À partir des écoutes Spotify d'un utilisateur, "
        "suggère-lui 5 artistes ou albums qu'il ne connaît probablement pas encore "
        "mais qu'il adorerait. Explique brièvement pourquoi pour chacun. "
        "Réponds en français, max 250 mots."
    )

    tracks_text = "\n".join(
        f"- {t['name']} par {t['artist']}" for t in top_tracks[:20]
    )
    artists_text = "\n".join(
        f"- {a['name']} (genres: {', '.join(a.get('genres', [])[:3]) or 'inconnu'})"
        for a in top_artists[:15]
    )

    user = (
        f"Top morceaux :\n{tracks_text}\n\n"
        f"Artistes favoris :\n{artists_text}\n\n"
        "Suggère 5 artistes ou albums à découvrir."
    )

    return chat(system, user)


def sanitize_mood(mood, max_length=200):
    """
    Nettoie le champ humeur avant de l'envoyer au LLM.
    On tronque, on vire les guillemets et les retours à la ligne
    pour éviter de casser le prompt.
    """
    mood = mood[:max_length]
    mood = mood.replace('"', "'").replace("\\", "")
    mood = " ".join(mood.split())
    return mood.strip()


def get_ai_recommendations(top_tracks, top_artists, mood, total_minutes):
    """
    Le gros morceau : des recos personnalisées selon les goûts,
    l'humeur et le temps d'écoute. Retourne une liste de dicts
    [{"title": ..., "artist": ..., "reason": ...}] qu'on ira
    chercher sur Spotify pour avoir les vrais liens.
    """
    mood = sanitize_mood(mood)

    # Easter egg
    if mood in ("taquin", "troll", "taquine"):
        return [{
            "title": "Rick Astley",
            "artist": "Never Gonna Give You Up",
            "reason": "Rick Rollé",
        }]

    nb_tracks = max(1, total_minutes // 3)
    # On demande un peu plus que nécessaire parce que Groq peut
    # halluciner des titres introuvables sur Spotify
    nb_requested = nb_tracks * 1.5

    system = (
        "Tu es un DJ expert et conseiller musical. "
        "À partir des goûts Spotify d'un utilisateur, de son humeur actuelle "
        "et du temps d'écoute souhaité, tu recommandes des morceaux. "
        "RÈGLE CRITIQUE : chaque morceau DOIT réellement exister sur Spotify. "
        "Utilise les TITRES EXACTS et NOMS D'ARTISTES EXACTS. "
        "N'invente JAMAIS un titre ou un artiste. "
        "Tu DOIS répondre UNIQUEMENT avec un JSON valide, sans texte autour. "
        "Format : tableau JSON d'objets avec les clés : "
        '"title" (titre EXACT), "artist" (nom EXACT), '
        '"reason" (explication courte en français, même ton que l\'utilisateur). '
        "Pas de ```json, juste le JSON pur. "
        "Sois créatif mais reste fidèle aux goûts de l'utilisateur."
    )

    tracks_text = "\n".join(
        f"- {t['name']} par {t['artist']}" for t in top_tracks[:10]
    )
    artists_text = "\n".join(
        f"- {a['name']} (genres: {', '.join(a.get('genres', [])[:3]) or 'inconnu'})"
        for a in top_artists[:10]
    )

    user = (
        f"Top morceaux :\n{tracks_text}\n\n"
        f"Artistes favoris :\n{artists_text}\n\n"
        f"Humeur actuelle : \"{mood}\"\n"
        f"Temps d'écoute : {total_minutes} minutes\n\n"
        f"Recommande exactement {nb_requested} morceaux. "
        f"Chaque titre et artiste DOIT exister sur Spotify. "
        f"Réponds UNIQUEMENT avec le JSON."
    )

    raw = chat(system, user, max_tokens=2048)
    if not raw:
        return None

    # Nettoyage du JSON (Groq met parfois des ```json...```)
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        return None
    except json.JSONDecodeError:
        # JSON cassé → on renvoie quand même le texte brut
        return [{"title": "", "artist": "", "reason": raw}]


def track_label(track):
    """Fabrique un label 'Titre – Artiste' à partir d'un dict track."""
    name = track.get('name', '?')
    artist = track.get('artist')
    if not artist:
        artists = track.get('artists', [])
        artist = artists[0]['name'] if artists else '?'
    return f"{name} – {artist}"
