import random
import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode


class TrackCollector:
    """
    Sert à construire une liste de morceaux sans doublons.
    On l'utilise dans toutes les fonctions de recommandation pour
    accumuler des tracks au fil des phases, en gérant :
    - les doublons par ID Spotify
    - les doublons par nom (remasters, deluxe, live versions...)
    - un plafond de morceaux par artiste (pour pas avoir 10x le même)
    """

    def __init__(self, excluded_ids=None, max_per_artist=2):
        self.tracks = []
        self.seen_ids = set(excluded_ids or [])
        self.seen_names = set()
        self.artist_count = {}
        self.max_per_artist = max_per_artist

    def add(self, track):
        """Ajoute un morceau s'il passe tous les filtres anti-doublon."""
        if track['id'] in self.seen_ids:
            return False

        # On nettoie le nom pour attraper les variantes
        # ex: "Bohemian Rhapsody - Remastered 2011" → "bohemian rhapsody"
        a_name = track['artists'][0]['name'].lower() if track.get('artists') else ''
        t_name = track.get('name', '').lower().split(' - ')[0].split(' (')[0].strip()
        key = f"{t_name}|{a_name}"

        if key in self.seen_names:
            return False

        # Max 2 morceaux du même artiste par défaut
        a_id = track['artists'][0]['id'] if track.get('artists') else None
        if a_id and self.artist_count.get(a_id, 0) >= self.max_per_artist:
            return False

        self.tracks.append(track)
        self.seen_ids.add(track['id'])
        self.seen_names.add(key)
        if a_id:
            self.artist_count[a_id] = self.artist_count.get(a_id, 0) + 1
        return True

    def __len__(self):
        return len(self.tracks)

    def result(self, limit):
        """Mélange les morceaux et retourne les `limit` premiers."""
        random.shuffle(self.tracks)
        return {'tracks': self.tracks[:limit]}


class SpotifyAPI:
    """
    Wrapper pour les appels HTTP directs à l'API Spotify.

    Pourquoi ne pas juste utiliser spotipy ? Parce qu'en mode développeur
    Spotify, spotipy envoie parfois des paramètres en trop (genre position=None)
    qui déclenchent des erreurs 403. Du coup on fait nos propres requêtes
    pour les endpoints problématiques (search, POST/PUT sur les playlists).
    """

    def __init__(self, sp):
        """sp : un client spotipy déjà authentifié (on s'en sert pour le token)."""
        self.sp = sp

    def get_token(self):
        """Récupère le token d'accès depuis spotipy."""
        token_info = self.sp.auth_manager.get_access_token()
        if isinstance(token_info, dict):
            return token_info['access_token']
        return token_info

    def search(self, query, limit=10, search_type='track', market='FR'):
        """
        Recherche Spotify via HTTP direct.
        Le limit est cappé à 10 (max autorisé en mode dev).
        """
        token = self.get_token()
        params = {
            'q': query,
            'type': search_type,
            'limit': min(int(limit), 10),
            'market': market
        }
        url = f'https://api.spotify.com/v1/search?{urlencode(params)}'
        req = Request(url, headers={'Authorization': f'Bearer {token}'})
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())

    def post(self, url, body):
        """POST sur l'API Spotify (créer une playlist, ajouter des morceaux, etc.)."""
        token = self.sp.auth_manager.get_access_token(as_dict=False)
        data = json.dumps(body).encode('utf-8')
        req = Request(url, data=data, headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        })
        resp = urlopen(req)
        return json.loads(resp.read().decode('utf-8'))

    def put(self, url, body):
        """PUT sur l'API Spotify (modifier une playlist, etc.)."""
        token = self.sp.auth_manager.get_access_token(as_dict=False)
        data = json.dumps(body).encode('utf-8')
        req = Request(url, data=data, headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }, method='PUT')
        urlopen(req)


class PlaylistManager:
    """
    Tout ce qui touche aux playlists Spotify : créer, ajouter des morceaux,
    lister celles de l'utilisateur.

    On passe par SpotifyAPI au lieu de spotipy parce que les endpoints
    de playlists sont cassés en mode dev.
    """

    def __init__(self, sp):
        self.sp = sp
        self.api = SpotifyAPI(sp)

    def create(self, name, tracks, description="", public=False):
        """Crée une playlist et y ajoute les morceaux d'un coup."""
        if not name or not name.strip():
            raise ValueError("Il faut donner un nom à la playlist")
        if not tracks:
            raise ValueError("Il faut au moins un morceau")

        # Créer via /me/playlists (l'ancien endpoint /users/{id}/playlists
        # est bloqué en mode dev)
        playlist = self.api.post("https://api.spotify.com/v1/me/playlists", {
            "name": name.strip(),
            "public": public,
            "description": description,
        })

        # Spotify ignore parfois "public: false" à la création,
        # on le force avec un PUT derrière
        if not public:
            self.api.put(
                f"https://api.spotify.com/v1/playlists/{playlist['id']}",
                {"public": False}
            )

        track_ids = self._extract_ids(tracks)
        added = self._add_by_batch(playlist['id'], track_ids)

        return {
            'id': playlist['id'],
            'name': playlist['name'],
            'url': playlist.get('external_urls', {}).get('spotify', ''),
            'tracks_added': added
        }

    def add_to_existing(self, playlist_id, tracks, avoid_duplicates=True):
        """Ajoute des morceaux à une playlist existante (ignore les doublons si demandé)."""
        if not playlist_id:
            raise ValueError("Il faut un ID de playlist")
        if not tracks:
            raise ValueError("Il faut au moins un morceau")

        track_ids = self._extract_ids(tracks)
        duplicates_skipped = 0

        if avoid_duplicates:
            existing = self._get_existing_ids(playlist_id)
            before = len(track_ids)
            track_ids = [tid for tid in track_ids if tid not in existing]
            duplicates_skipped = before - len(track_ids)

        added = self._add_by_batch(playlist_id, track_ids)

        playlist_info = self.sp.playlist(playlist_id, fields='external_urls')
        playlist_url = playlist_info.get('external_urls', {}).get('spotify', '')

        return {
            'tracks_added': added,
            'duplicates_skipped': duplicates_skipped,
            'playlist_url': playlist_url
        }

    def get_user_playlists(self, limit=50):
        """Récupère seulement les playlists dont l'utilisateur est propriétaire."""
        user_id = self.sp.current_user()['id']
        results = self.sp.current_user_playlists(limit=limit)
        playlists = []
        for pl in results.get('items', []):
            if pl.get('owner', {}).get('id') == user_id:
                playlists.append({
                    'id': pl['id'],
                    'name': pl['name'],
                    'tracks_count': pl.get('tracks', {}).get('total', 0),
                    'url': pl.get('external_urls', {}).get('spotify', '')
                })
        return playlists

    # --- Méthodes internes ---

    def _extract_ids(self, tracks):
        """Extrait les IDs Spotify d'une liste de tracks (bruts ou formatés)."""
        return [t['id'] for t in tracks if t.get('id')]

    def _add_by_batch(self, playlist_id, track_ids):
        """Ajoute les morceaux par paquets de 100 (limite API)."""
        added = 0
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i:i + 100]
            uris = [f"spotify:track:{tid}" for tid in batch]
            self.api.post(
                f"https://api.spotify.com/v1/playlists/{playlist_id}/items",
                {"uris": uris}
            )
            added += len(batch)
        return added

    def _get_existing_ids(self, playlist_id):
        """Récupère les IDs des morceaux déjà dans une playlist (pour éviter les doublons)."""
        existing = set()
        offset = 0
        while True:
            results = self.sp.playlist_items(
                playlist_id, fields='items.track.id,next',
                limit=100, offset=offset
            )
            for item in results.get('items', []):
                track = item.get('track')
                if track and track.get('id'):
                    existing.add(track['id'])
            if not results.get('next'):
                break
            offset += 100
        return existing