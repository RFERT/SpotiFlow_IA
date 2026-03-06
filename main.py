from os import environ
from dotenv import load_dotenv
from atexit import register as atexit_register

from src.ngrok_config import get_spotify_redirect_uri, cleanup_ngrok
from src.streamlit_app import run_app

def main():
    atexit_register(cleanup_ngrok)
    redirect_uri = get_spotify_redirect_uri(port=8501)
    if redirect_uri:
        environ["spotify_redirect_uri"] = redirect_uri
    else:
        raise ValueError("Impossible d'obtenir l'URL ngrok.")
    run_app()



if __name__ == "__main__":
    load_dotenv()
    main()