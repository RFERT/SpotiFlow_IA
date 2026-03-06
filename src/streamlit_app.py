import streamlit as st
from dotenv import load_dotenv
import os
from datetime import datetime
from time import time

from src.spotify_client import *
from src.callback_handler import handle_spotify_callback
from src.groq_client import (
    is_groq_available,
    analyze_music_profile,
    generate_playlist_description,
    suggest_discoveries,
    get_ai_recommendations,
)

# Variables globales
CACHE_PATH = ".spotify_cache"
GENRES = [
    "", "acoustic", "afrobeat", "alt-rock", "alternative", "ambient",
    "anime", "black-metal", "bluegrass", "blues", "bossanova",
    "brazil", "breakbeat", "british", "cantopop", "chicago-house",
    "children", "chill", "classical", "club", "comedy", "country",
    "dance", "dancehall", "death-metal", "deep-house", "detroit-techno",
    "disco", "disney", "drum-and-bass", "dub", "dubstep", "edm",
    "electro", "electronic", "emo", "folk", "forro", "french",
    "funk", "garage", "german", "gospel", "goth", "grindcore",
    "groove", "grunge", "guitar", "happy", "hard-rock", "hardcore",
    "hardstyle", "heavy-metal", "hip-hop", "holidays", "honky-tonk",
    "house", "idm", "indian", "indie", "indie-pop", "industrial",
    "iranian", "j-dance", "j-idol", "j-pop", "j-rock", "jazz",
    "k-pop", "kids", "latin", "latino", "malay", "mandopop",
    "metal", "metal-misc", "metalcore", "minimal-techno", "movies",
    "mpb", "new-age", "new-release", "opera", "pagode", "party",
    "philippines-opm", "piano", "pop", "pop-film", "post-dubstep",
    "power-pop", "progressive-house", "psych-rock", "punk", "punk-rock",
    "r-n-b", "rainy-day", "reggae", "reggaeton", "road-trip", "rock",
    "rock-n-roll", "rockabilly", "romance", "sad", "salsa", "samba",
    "sertanejo", "show-tunes", "singer-songwriter", "ska", "sleep",
    "songwriter", "soul", "soundtracks", "spanish", "study", "summer",
    "swedish", "synth-pop", "tango", "techno", "trance", "trip-hop",
    "turkish", "work-out", "world-music"]

def run_app():
    """Point d'entrée de l'app Streamlit."""
    st.set_page_config(page_title="SpotiFlow (MVP)", page_icon=r"img\hetic_logo.html", layout="wide")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("SpotiFlow")
        st.markdown("---")
    if st.session_state.get('_disconnected'):
        if os.path.exists(CACHE_PATH):
            os.remove(CACHE_PATH)
        # On garde le flag tant que le cache existe
        if not os.path.exists(CACHE_PATH):
            del st.session_state['_disconnected']
        show_not_connected()
        return
    if handle_spotify_callback():
        show_not_connected()
        return

    if os.path.exists(CACHE_PATH):
        try:
            sp = get_spotify_client()
        except Exception as e:
            st.error(f"Erreur de connexion : {e}")
            # Erreur de connexion → on nettoie et on propose de se reconnecter
            clear_auth_data()
            st.info(
                "Clique sur le bouton ci-dessous "
                "pour te reconnecter."
            )
            show_login_button()
            return
        st.session_state['auth_time'] = time()
        show_connected_app(sp)
    else:
        show_not_connected()

def show_not_connected():
    """Page affichée quand on n'est pas connecté."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.warning("Tu n'es pas connecté à Spotify")
        st.write("Clique sur le bouton ci-dessous pour te connecter avec ton compte Spotify.")
        show_login_button()


def show_connected_app(sp):
    """Page principale quand l'utilisateur est connecté."""
    user_info = sp.current_user()
    show_user_profile(user_info)
    st.markdown("---")

    option = st.radio(
        "Que veux-tu faire ?",
        ["Mes statistiques", "Recommandations", "Se déconnecter"],
        horizontal=True
    )

    if option == "Mes statistiques":
        show_statistics(sp)
    elif option == "Recommandations":
        show_recommendations(sp)
    elif option == "Se déconnecter":
        handle_disconnect()

def show_user_profile(user_info):
    """Affiche le profil de l'utilisateur."""
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        images = user_info.get('images', [])
        if images and images[0].get('url'):
            st.image(images[0]['url'], width=300)
    with col2:
        display_name = user_info.get('display_name', 'Utilisateur')
        st.markdown(f"## {display_name}")
        followers = user_info.get('followers', {}).get('total', 0)
        st.markdown(f"**{followers}** follower{'s' if followers != 1 else ''}")
        st.markdown(f"[Voir sur Spotify]({user_info.get('external_urls', {}).get('spotify', '#')})")
        auth_time = st.session_state.get('auth_time', 0)
        if time() < auth_time + 5:
            st.success(f"Connecté en tant que {user_info.get('display_name', 'Utilisateur')}")


def show_login_button():
    """Affiche le bouton de connexion Spotify (redirige dans le même onglet)."""
    auth = get_spotify_auth()
    auth_url = auth.get_authorize_url()
    st.markdown(f"""
    <div style="display: flex; justify-content: center; margin: 20px 0;">
        <a href="{auth_url}" style="text-decoration: none;">
            <button style="
                background-color: #1DB954;
                color: white;
                padding: 12px 32px;
                border: none;
                border-radius: 500px;
                font-size: 16px;
                font-weight: 700;
                cursor: pointer;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 12px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                transition: background-color 0.3s ease;
            "
            onmouseover="this.style.backgroundColor='#1ed760'"
            onmouseout="this.style.backgroundColor='#1DB954'">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.499-.12-.32.179-.779.499-.899 4.561-1.123 8.582-.571 11.921 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.299-3.239-1.98-8.159-2.58-12.259-1.441-.479.12-1.02-.239-1.141-.718-.12-.479.239-1.02.718-1.141 4.561-1.38 9.921.603 13.659 1.801.479.301.599.921.301 1.299zm.12-3.36c-3.9-2.32-10.661-2.59-14.72-1.438-.479.12-1.02-.239-1.141-.718-.101-.479.239-1.02.718-1.141C9.6 9.927 17.26 10.207 21.676 12.826c.299.179.479.659.301 1.02-.179.361-.599.441-.899.261z"/>
                </svg>
                Se connecter avec Spotify
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)

    st.info("""
    **Comment ça marche :**
    1. Clique sur le bouton
    2. Tu seras redirigé vers Spotify
    3. Accepte les permissions demandées
    4. Tu seras automatiquement connecté à SpotiFlow
    """)


def handle_disconnect():
    """Gère la déconnexion (demande de confirmation)."""
    st.warning("Es-tu sûr de vouloir te déconnecter ?")
    if st.button("Confirmer la déconnexion"):
        clear_auth_data()

        # Flag pour bloquer toute reconnexion automatique
        st.session_state['_disconnected'] = True

        st.rerun()


def clear_auth_data():
    """
    Nettoie tout ce qui est lié à l'authentification :
    cache Spotify sur disque, session Streamlit, cookies navigateur.
    """
    # Supprimer le fichier cache (token sur disque)
    if os.path.exists(CACHE_PATH):
        os.remove(CACHE_PATH)

    # Nettoyer l'URL (au cas où il reste un ?code= ou ?error=)
    st.query_params.clear()

    # Vider le session_state
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # Supprimer les cookies/storage côté navigateur
    st.markdown(
        """
        <script>
            document.cookie.split(';').forEach(function(c) {
                document.cookie = c.trim().split('=')[0]
                    + '=;expires=Thu, 01 Jan 1970 00:00:00 UTC'
                    + ';path=/';
            });
            localStorage.clear();
            sessionStorage.clear();
        </script>
        """,
        unsafe_allow_html=True,
    )

def show_statistics(sp):
    """Page des stats : analyse IA + top tracks + top artistes."""
    st.subheader("Tes statistiques Spotify")
    show_ai_analysis(sp)
    st.markdown("---")
    show_top_tracks(sp)
    st.markdown("---")
    show_top_artists(sp)


def show_recommendations(sp):
    """Affiche les 4 onglets de recommandations."""
    st.subheader("Recommandations Musicales")
    tab1, tab2, tab3, tab4 = st.tabs(["Recommendation IA", "À partir de mes chansons", "À partir d'une recherche", "Par genre"])
    with tab1:
        tab_discover_IA(sp)
    with tab2:
        tab_from_top_tracks(sp)
    with tab3:
        tab_similar_tracks(sp)
    with tab4:
        tab_discover_genre(sp)

def show_ai_analysis(sp):
    """Analyse du profil musical par l'IA + suggestions."""
    if not is_groq_available():
        st.info("Ajoute ta clé `GROQ_API_KEY` dans le fichier `.env` pour activer l'analyse IA.")
        return

    st.markdown("### Ton profil musical vu par l'IA")

    # On met en cache les données pour pas les re-fetch à chaque clic
    if 'ai_profile_data' not in st.session_state:
        top_tracks_raw = sp.current_user_top_tracks(limit=10).get('items', [])
        top_artists_raw = sp.current_user_top_artists(limit=10).get('items', [])
        st.session_state['ai_profile_data'] = {
            'tracks': [{'name': t['name'], 'artist': t['artists'][0]['name']} for t in top_tracks_raw],
            'artists': [{'name': a['name'], 'genres': a.get('genres', [])} for a in top_artists_raw],
        }

    data = st.session_state['ai_profile_data']

    if st.button("Analyser mon profil", key="ai_analyze_btn"):
        with st.spinner("L'IA analyse tes goûts musicaux..."):
            result = analyze_music_profile(data['tracks'], data['artists'])
        if result:
            st.session_state['ai_analysis'] = result
        else:
            st.error("Erreur lors de l'analyse. Vérifie ta clé Groq.")

    if st.session_state.get('ai_analysis'):
        st.markdown("#### Analyse de ton profil")
        st.markdown(st.session_state['ai_analysis'])


def show_top_tracks(sp):
    """Affiche le classement des morceaux préférés avec podium."""
    st.markdown("### Tes chansons préférées")
    top_tracks = sp.current_user_top_tracks(limit=10)
    items = top_tracks['items']
    if len(items) >= 3:
        show_podium(items, item_type="track")
    if len(items) > 3:
        st.markdown("---")
        for i, track in enumerate(items[3:], 4):
            show_track_list_item(track, i)


def show_top_artists(sp):
    """Affiche le classement des artistes préférés avec podium."""
    st.markdown("### Tes artistes préférés")
    top_artists = sp.current_user_top_artists(limit=10)
    items = top_artists['items']
    if len(items) >= 3:
        show_podium(items, item_type="artist")
    if len(items) > 3:
        st.markdown("---")
        for i, artist in enumerate(items[3:], 4):
            show_artist_list_item(artist, i)

def tab_discover_IA(sp):
    """Onglet IA : recos personnalisées selon l'humeur et le temps d'écoute."""
    if not is_groq_available():
        st.info("Ajoute ta clé `GROQ_API_KEY` dans le fichier `.env` pour activer les recommandations IA.")
        return

    st.write("L'IA te recommande des morceaux en fonction de tes goûts, ton humeur et ton temps d'écoute")

    # Champs humeur + durée côte à côte
    col_mood, col_duration = st.columns([2, 1])
    with col_mood:
        mood = st.text_input("Quelle est ton humeur ? *(tu peux aussi prompter la playlist voulue)*", key="ia_mood")
    with col_duration:
        total_minutes = st.slider("Durée (minutes)", min_value=5, max_value=90, value=30, step=5, key="ia_duration")

    nb_tracks_estimate = max(1, total_minutes // 3)
    st.caption(f"≈ {nb_tracks_estimate} morceaux pour {total_minutes} min d'écoute")

    # On cache les données pour pas refaire les appels API (faut être scalable !)
    if 'ai_profile_data' not in st.session_state:
        with st.spinner("Chargement de tes données Spotify..."):
            top_tracks_raw = sp.current_user_top_tracks(limit=10).get('items', [])
            top_artists_raw = sp.current_user_top_artists(limit=10).get('items', [])
            st.session_state['ai_profile_data'] = {
                'tracks': [
                    {
                        'name': t['name'],
                        'artist': t['artists'][0]['name'],
                    }
                    for t in top_tracks_raw
                ],
                'artists': [
                    {
                        'name': a['name'],
                        'genres': a.get('genres', []),
                    }
                    for a in top_artists_raw
                ],
            }

    data = st.session_state['ai_profile_data']

    col_reco, col_suggest = st.columns(2)

    with col_reco:
        if st.button("Recommandations IA", key="ai_reco_btn"):
            if not mood.strip():
                st.warning("Décris ton humeur pour lancer les recos !")
            else:
                with st.spinner("L'IA compose ta playlist idéale..."):
                    ai_items = get_ai_recommendations(
                        data['tracks'], data['artists'],
                        mood=mood, total_minutes=total_minutes
                    )
                if ai_items:
                    # On cherche chaque morceau sur Spotify pour les vrais liens
                    spotify_tracks = []
                    target = nb_tracks_estimate
                    for item in ai_items:
                        if len(spotify_tracks) >= target:
                            break
                        track = find_ai_track_on_spotify(sp, item)
                        if track:
                            spotify_tracks.append(track)
                    st.session_state['ai_reco_tracks'] = spotify_tracks
                    if not spotify_tracks:
                        st.warning("Aucun morceau trouvé sur Spotify. Essaie une autre humeur !")
                else:
                    st.error("Erreur lors des recommandations. Vérifie ta clé Groq.")

    with col_suggest:
        if st.button("Suggestions de découverte", key="ai_suggest_btn"):
            with st.spinner("L'IA cherche des pépites pour toi..."):
                result = suggest_discoveries(data['tracks'], data['artists'])
            if result:
                st.session_state['ai_suggestions'] = result
            else:
                st.error("Erreur lors des suggestions. Vérifie ta clé Groq.")

    if st.session_state.get('ai_reco_tracks'):
        tracks = st.session_state['ai_reco_tracks']
        st.markdown(f"#### {len(tracks)} recommandations personnalisées")
        display_ai_tracks_grid(tracks)
        show_save_to_playlist(sp, tracks, key_prefix="ai_reco", mood=mood)

    if st.session_state.get('ai_suggestions'):
        st.markdown("#### Artistes & albums à découvrir")
        st.markdown(st.session_state['ai_suggestions'])


def tab_from_top_tracks(sp):
    """Onglet : recos à partir des top chansons de l'utilisateur."""
    st.write("Génère des recommandations basées sur tes meilleures chansons et tes artistes préférés")
    if st.button("Générer à partir de mes top chansons"):
        try:
            with st.spinner("Récupération de tes meilleures chansons et artistes..."):
                seeds = get_top_tracks_as_seeds(sp, limit=10)
                top_artists = get_top_artists_info(sp, limit=10)
            with st.spinner("Génération des recommandations diversifiées..."):
                recommendations = get_recommendations(sp, seed_tracks=seeds, limit=20, top_artists=top_artists)
                formatted = format_recommendations(recommendations)
            st.session_state['tab1_results'] = formatted
        except Exception as e:
            st.error(f"Erreur : {e}")

    # Afficher résultats + sauvegarde depuis session_state
    if st.session_state.get('tab1_results'):
        formatted = st.session_state['tab1_results']
        st.success(f"{len(formatted)} recommandations trouvées !")
        display_tracks_grid(formatted)
        show_save_to_playlist(sp, formatted, key_prefix="tab1")


def tab_similar_tracks(sp):
    """Onglet : titres similaires à une chanson recherchée."""
    st.write("Cherche une chanson et découvre des titres similaires")
    search_query = st.text_input("Cherche une chanson...")
    if not search_query:
        return
    try:
        tracks = search_track(sp, search_query)
        if not tracks:
            st.warning("Aucune chanson trouvée")
            return
        track_options = [f"{t['name']} - {t['artists'][0]['name']}" for t in tracks]
        selected = st.selectbox("Sélectionne une chanson :", track_options)
        selected_idx = track_options.index(selected)
        selected_track = tracks[selected_idx]
        if st.button("Trouver des titres similaires"):
            with st.spinner(f"Recherche de titres similaires à « {selected_track['name']} »..."):
                similar = get_similar_tracks(sp, track_id=selected_track['id'], limit=20)
                formatted = format_recommendations(similar)
            if formatted:
                st.session_state['tab2_results'] = formatted
            else:
                st.warning("Aucun titre similaire trouvé")
    except Exception as e:
        st.error(f"Erreur : {e}")

    # Afficher résultats + sauvegarde depuis session_state
    if st.session_state.get('tab2_results'):
        formatted = st.session_state['tab2_results']
        st.success(f"{len(formatted)} titres similaires trouvés !")
        display_tracks_grid(formatted)
        show_save_to_playlist(sp, formatted, key_prefix="tab2")


def tab_discover_genre(sp):
    """Onglet : découverte par genre musical."""
    st.write("Découvre de nouvelles chansons par genre ou ambiance")
    genre_query = get_genre_query()
    nb_results = st.slider("Nombre de résultats", 1, 10, 10)
    if st.button("Découvrir par genre"):
        if not genre_query:
            st.warning("Sélectionne ou tape un genre pour lancer la recherche")
            return
        try:
            with st.spinner(f"Recherche d'artistes et morceaux du genre « {genre_query} »..."):
                results = discover_by_genre(sp, genre_query=genre_query, limit=int(nb_results))
                tracks = results['tracks']
            if tracks:
                st.session_state['tab3_results'] = tracks
            else:
                st.warning(f"Aucun résultat pour « {genre_query} »")
        except Exception as e:
            st.error(f"Erreur : {e}")

    # Afficher résultats + sauvegarde depuis session_state
    if st.session_state.get('tab3_results'):
        tracks = st.session_state['tab3_results']
        st.success(f"{len(tracks)} chansons trouvées !")
        display_raw_tracks_grid(tracks)
        show_save_to_playlist(sp, tracks, key_prefix="tab3")

def show_save_to_playlist(sp, tracks, key_prefix, mood=None):
    """
    Boutons pour sauvegarder des morceaux dans une playlist.
    key_prefix sert à éviter les conflits de clés entre onglets.
    """
    st.markdown("---")
    st.markdown("#### Sauvegarder dans une playlist")

    action = st.radio(
        "Que veux-tu faire ?",
        ["Créer une nouvelle playlist", "Ajouter à une playlist existante"],
        key=f"{key_prefix}_action",
        horizontal=True
    )

    if action == "Créer une nouvelle playlist":
        show_create_new_playlist(sp, tracks, key_prefix, mood)
    else:
        show_add_to_existing_playlist(sp, tracks, key_prefix)


def show_create_new_playlist(sp, tracks, key_prefix, mood=None):
    """Formulaire pour créer une nouvelle playlist."""
    col_name, col_public = st.columns([3, 1])
    with col_name:
        date = datetime.now().strftime("%Y-%m-%d")
        playlist_name = st.text_input("Nom de la playlist", value=f"SpotiFlow Mix {date}", key=f"{key_prefix}_name")
    with col_public:
        is_public = st.checkbox("Publique", value=False, key=f"{key_prefix}_public")

    # La partie description est dans un fragment pour pouvoir
    # rafraîchir juste ce bloc quand l'IA génère une description
    description = playlist_description_fragment(playlist_name, tracks, key_prefix, mood)

    if st.button("Créer la playlist", key=f"{key_prefix}_create_btn"):
        if not playlist_name.strip():
            st.warning("Donne un nom à ta playlist !")
            return
        try:
            with st.spinner("Création de la playlist..."):
                result = create_playlist_from_recommendations(
                    sp, name=playlist_name, tracks=tracks,
                    description=description, public=is_public
                )
            st.success(f"Playlist « {result['name']} » créée avec {result['tracks_added']} morceaux !")
            if result['url']:
                st.markdown(f"[Ouvrir dans Spotify]({result['url']})")
        except Exception as e:
            st.error(f"Erreur lors de la création : {e}")


def show_add_to_existing_playlist(sp, tracks, key_prefix):
    """Formulaire pour ajouter des morceaux à une playlist existante."""
    try:
        playlists = get_user_playlists(sp)
    except Exception as e:
        st.error(f"Impossible de récupérer tes playlists : {e}")
        return

    if not playlists:
        st.info("Tu n'as aucune playlist. Crée-en une d'abord !")
        return

    playlist_options = [f"{pl['name']} ({pl['tracks_count']} titres)" for pl in playlists]
    selected = st.selectbox("Choisis une playlist :", playlist_options, key=f"{key_prefix}_select_pl")
    selected_idx = playlist_options.index(selected)
    selected_playlist = playlists[selected_idx]

    avoid_dupes = st.checkbox("Éviter les doublons", value=True, key=f"{key_prefix}_dupes")

    if st.button("Ajouter à la playlist", key=f"{key_prefix}_add_btn"):
        try:
            with st.spinner(f"Ajout à « {selected_playlist['name']} »..."):
                result = add_tracks_to_playlist(
                    sp, playlist_id=selected_playlist['id'],
                    tracks=tracks, avoid_duplicates=avoid_dupes
                )
            msg = f"{result['tracks_added']} morceaux ajoutés !"
            if result['duplicates_skipped'] > 0:
                msg += f" ({result['duplicates_skipped']} doublons ignorés)"
            st.success(msg)
            if result['playlist_url']:
                st.markdown(f"[Ouvrir dans Spotify]({result['playlist_url']})")
        except Exception as e:
            st.error(f"Erreur lors de l'ajout : {e}")


@st.fragment
def playlist_description_fragment(playlist_name, tracks, key_prefix, mood=None):
    """
    Fragment isolé pour le champ description + bouton IA.
    Comme c'est un fragment, le st.rerun(scope="fragment") ne rafraîchit
    que ce bloc au lieu de recharger toute la page.
    """
    desc_key = f"{key_prefix}_desc"
    col_desc, col_ai = st.columns([4, 1])
    with col_desc:
        description = st.text_input(
            "Description (optionnel)",
            value=st.session_state.get(f"{key_prefix}_ai_desc", "Playlist générée par SpotiFlow"),
            key=desc_key
        )
    with col_ai:
        st.markdown("<br>", unsafe_allow_html=True)
        if is_groq_available() and st.button("IA", key=f"{key_prefix}_ai_desc_btn", help="Générer une description avec l'IA"):
            with st.spinner("Génération de la description avec l'IA..."):
                ai_desc = generate_playlist_description(playlist_name, tracks, mood)
            if ai_desc:
                st.session_state[f"{key_prefix}_ai_desc"] = ai_desc
                st.rerun(scope="fragment")
    return description

def display_tracks_grid(formatted_tracks):
    """Affiche les morceaux formatés en grille de 2 colonnes."""
    cols = st.columns(2)
    for i, track in enumerate(formatted_tracks):
        with cols[i % 2]:
            display_track_card(track)


def display_track_card(track):
    """Affiche une carte pour un morceau (version formatée)."""
    if track['image']:
        st.image(track['image'], width=200)
    st.markdown(f"**{track['name']}**")
    st.caption(f"Par {track['artist']}")
    st.caption(f"Album : {track['album']}")
    st.markdown(f"[Écouter sur Spotify]({track['url']})")
    st.markdown("---")


def display_raw_tracks_grid(raw_tracks):
    """Affiche les morceaux bruts en grille de 2 colonnes."""
    cols = st.columns(2)
    for i, track in enumerate(raw_tracks):
        with cols[i % 2]:
            display_raw_track_card(track)


def display_raw_track_card(track):
    """Affiche une carte pour un morceau brut (tel que renvoyé par l'API)."""
    images = track.get('album', {}).get('images', [])
    if images:
        st.image(images[0]['url'], width=200)
    st.markdown(f"**{track['name']}**")
    st.caption(f"Par {track['artists'][0]['name']}")
    url = track.get('external_urls', {}).get('spotify', '')
    if url:
        st.markdown(f"[Écouter sur Spotify]({url})")
    st.markdown("---")


def display_ai_tracks_grid(tracks):
    """Affiche les morceaux recommandés par l'IA en grille de 2."""
    cols = st.columns(2)
    for i, track in enumerate(tracks):
        with cols[i % 2]:
            display_ai_track_card(track)


def display_ai_track_card(track):
    """Carte d'un morceau recommandé par l'IA (avec la raison en bonus)."""
    images = track.get('album', {}).get('images', [])
    if images:
        st.image(images[0]['url'], width=200)
    st.markdown(f"**{track['name']}**")
    st.caption(f"Par {track['artists'][0]['name']}")
    reason = track.get('_ai_reason', '')
    if reason:
        st.info(f"🤖 {reason}")
    url = track.get('external_urls', {}).get('spotify', '')
    if url:
        st.markdown(f"[🎧 Écouter sur Spotify]({url})")
    st.markdown("---")

def show_podium(items, item_type="track"):
    """Affiche le podium Top 3 : 🥈 à gauche, 🥇 au centre, 🥉 à droite."""
    medals = ["🥇", "🥈", "🥉"]
    podium_order = [1, 0, 2]
    cols = st.columns(3)
    for col_idx, rank_idx in enumerate(podium_order):
        size = 180 if rank_idx == 0 else 140
        with cols[col_idx]:
            show_podium_item(items[rank_idx], medals[rank_idx], size, item_type)


def show_podium_item(item, medal, size, item_type="track"):
    """Affiche un élément du podium avec sa médaille."""
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='margin-bottom:0;'>{medal}</h2>", unsafe_allow_html=True)

    if item_type == "track":
        image_url = item.get('album', {}).get('images', [{}])[0].get('url', '')
        if image_url:
            st.image(image_url, width=size)
        st.markdown(f"**{item['name']}**")
        artists = ", ".join(a['name'] for a in item['artists'])
        st.caption(artists)
        spotify_url = item.get('external_urls', {}).get('spotify', '')
        if spotify_url:
            st.markdown(f"[Écouter]({spotify_url})")
    else:
        image_url = item.get('images', [{}])[0].get('url', '')
        if image_url:
            st.image(image_url, width=size)
        st.markdown(f"**{item['name']}**")
        genres = ", ".join(item.get('genres', [])[:3])
        if genres:
            st.caption(genres)
        spotify_url = item.get('external_urls', {}).get('spotify', '')
        if spotify_url:
            st.markdown(f"[Profil Spotify]({spotify_url})")

    st.markdown("</div>", unsafe_allow_html=True)


def show_track_list_item(track, rank):
    """Affiche un morceau en format compact (miniature + infos sur une ligne)."""
    artists = ", ".join(a['name'] for a in track['artists'])
    image_url = track.get('album', {}).get('images', [{}])[0].get('url', '')
    col_img, col_info = st.columns([1, 5])
    with col_img:
        if image_url:
            st.image(image_url, width=60)
    with col_info:
        st.markdown(f"**{rank}.** {track['name']} — *{artists}*")


def show_artist_list_item(artist, rank):
    """Affiche un artiste en format compact (miniature + nom + genres)."""
    image_url = artist.get('images', [{}])[0].get('url', '')
    genres = ", ".join(artist.get('genres', [])[:2])
    col_img, col_info = st.columns([1, 5])
    with col_img:
        if image_url:
            st.image(image_url, width=60)
    with col_info:
        genre_text = f" — *{genres}*" if genres else ""
        st.markdown(f"**{rank}.** {artist['name']}{genre_text}")

def get_genre_query():
    """Affiche les contrôles de sélection de genre et retourne le choix."""
    col_select, col_custom = st.columns(2)
    with col_select:
        selected_genre = st.selectbox(
            "Choisis un genre :", GENRES,
            format_func=lambda x: "— Sélectionne un genre —" if x == "" else x.replace("-", " ").title())
    with col_custom:
        custom_genre = st.text_input("...ou tape un genre personnalisé")
    return custom_genre.strip() if custom_genre.strip() else selected_genre


def normalize(text):
    """Minuscule + strip pour comparer des textes."""
    return text.lower().strip()


def artist_matches(spotify_track, expected_artist):
    """
    Vérifie si un artiste du morceau Spotify correspond à celui
    suggéré par l'IA. Comparaison souple (inclusion dans un sens
    ou l'autre) pour gérer les variantes de noms.
    """
    expected = normalize(expected_artist)
    if not expected:
        return True  # Pas d'artiste attendu => on accepte tout
    for artist in spotify_track.get('artists', []):
        name = normalize(artist.get('name', ''))
        # "The Weeknd" dans "The Weeknd" ou l'inverse
        if expected in name or name in expected:
            return True
    return False


def find_ai_track_on_spotify(sp, ai_item):
    """
    Cherche un morceau recommandé par l'IA sur Spotify.
    Vérifie que l'artiste correspond (pour éviter covers/homonymes).

    Stratégie en 3 étapes :
    1. Recherche "titre artiste" + vérif artiste
    2. Recherche titre seul + vérif artiste
    3. Premier résultat, même sans match artiste
    """
    title = ai_item.get('title', '').strip()
    artist = ai_item.get('artist', '').strip()
    reason = ai_item.get('reason', '')

    if not title and not artist:
        return None

    # Tentative 1 : "titre artiste"
    results = search_track(sp, f"{title} {artist}")
    if results:
        for track in results:
            if artist_matches(track, artist):
                track['_ai_reason'] = reason
                return track

    # Tentative 2 : titre seul (parfois l'artiste brouille la recherche)
    if title:
        results = search_track(sp, title)
        if results:
            for track in results:
                if artist_matches(track, artist):
                    track['_ai_reason'] = reason
                    return track

    # Dernier recours : on prend ce qu'on trouve
    results = search_track(sp, f"{title} {artist}")
    if results:
        results[0]['_ai_reason'] = reason
        return results[0]

    return None

if __name__ == "__main__":
    load_dotenv()
    run_app()
