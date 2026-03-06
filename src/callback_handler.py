import os
import streamlit as st

from src.spotify_client import get_spotify_auth

CACHE_PATH = ".spotify_cache"

def get_auth_code_from_url():
    """
    Récupère le code d'auth dans les paramètres de l'URL grace à `st.query_params`.
    """
    try:
        query_params = st.query_params

        if 'code' in query_params:
            auth_code = query_params['code']
            if isinstance(auth_code, list):
                auth_code = auth_code[0]
            return auth_code

        return None

    except Exception as e:
        st.error(f"Erreur lors de la lecture de l'URL : {e}")
        return None


def exchange_code_for_token(auth_code):
    """
    Échange le code d'auth contre un token d'accès.
    Spotipy gère l'échange et stocke le token dans le cache.
    """
    try:
        auth = get_spotify_auth()

        # Spotipy gère l'échange et met le token en cache
        token_info = auth.get_access_token(auth_code)

        return token_info

    except Exception as e:
        st.error(f"Erreur lors de l'échange du code : {e}")
        return None


def delete_cache():
    """Supprime le fichier de cache Spotify s'il existe."""
    if os.path.exists(CACHE_PATH):
        os.remove(CACHE_PATH)


def handle_spotify_callback():
    """
    Gère le callback complet de Spotify au lancement de l'app.

    - Code reçu → échange contre un token, nettoie l'URL, recharge.
    - Annulation/erreur → supprime le cache, pose un flag, recharge.

    Retourne True si le caller doit s'arrêter (erreur/annulation/rerun),
    False si pas de callback en cours.
    """

    # Spotify redirige avec ?error=access_denied si l'user annule
    if 'error' in st.query_params:
        error = st.query_params.get('error', 'inconnu')
        st.query_params.clear()
        # Supprimer le cache pour empêcher une reconnexion auto
        delete_cache()
        if error == 'access_denied':
            st.session_state['_auth_cancelled'] = True
        else:
            st.session_state['_auth_error'] = error
        st.rerun()
        return True

    # Après le rerun, on affiche le message stocké dans la session
    if st.session_state.pop('_auth_cancelled', False):
        st.warning(
            "Connexion annulée. Clique sur le bouton "
            "pour réessayer quand tu veux !"
        )
        return True

    if '_auth_error' in st.session_state:
        error = st.session_state.pop('_auth_error')
        st.error(
            f"Erreur d'authentification Spotify : {error}"
        )
        return True

    # On a reçu un code d'auth valide
    auth_code = get_auth_code_from_url()
    if auth_code:
        token_info = exchange_code_for_token(auth_code)

        if token_info:
            st.query_params.clear()
            st.rerun()
        else:
            st.query_params.clear()
            delete_cache()
            st.error(
                "Impossible d'obtenir le token. "
                "Essaie de te reconnecter."
            )
            return True

    # Pas de callback en cours
    return False