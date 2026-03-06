"""
Configuration ngrok : fournit une URL publique pour le callback Spotify.
"""
import os

from pyngrok import ngrok
from dotenv import load_dotenv

# URL globale pour éviter d'en créer plusieurs
ngrok_url = None


def cleanup_ngrok():
    """Ferme proprement ngrok."""
    try:
        ngrok.kill()
    except Exception:
        pass

def get_ngrok_url(port=8501):
    """
    Démarre ngrok et retourne l'URL publique.
    Réutilise l'URL existante si on en a déjà une.
    """
    global ngrok_url
    
    # Si on a déjà une URL, on la réutilise
    if ngrok_url:
        return ngrok_url
    try:
        # On tue tous les tunnels existants pour repartir propre
        ngrok.kill()
        
        # Vérifier les tunnels orphelins
        try:
            for tunnel in ngrok.get_tunnels():
                ngrok.disconnect(tunnel.public_url)
        except Exception:
            pass
        
        ngrok_token = os.environ.get("ngrokauthtoken")
        if ngrok_token:
            ngrok.set_auth_token(ngrok_token)
        
        public_url = ngrok.connect(port)
        ngrok_url = str(public_url).split('"')[1].strip() if '"' in str(public_url) else str(public_url)
        return ngrok_url
    
    except Exception as e:
        print(f"❌ Erreur ngrok: {e}")
        return None

def get_spotify_redirect_uri(port=8501):
    """Construit l'URI de redirection Spotify à partir de l'URL ngrok."""
    ngrok_url = get_ngrok_url(port)
    if ngrok_url:
        return str(ngrok_url) + "/callback"
    return None

if __name__ == "__main__":
    load_dotenv()
    redirect_uri = get_spotify_redirect_uri()
    if redirect_uri:
        print(f"Spotify Redirect URI: {redirect_uri}")
    else:
        print("Impossible d'obtenir l'URL ngrok.")
        print(get_ngrok_url())