from os import environ
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import random

from src.models import TrackCollector, SpotifyAPI, PlaylistManager

def get_spotify_auth():
    """Crée l'objet d'authentification OAuth avec les identifiants du .env."""
    client_id = environ.get("spotify_clientid")
    client_secret = environ.get("spotify_clientsecret")
    redirect_uri = environ.get("spotify_redirect_uri")

    if not client_id or not client_secret:
        raise ValueError("SPOTIFY_CLIENT_ID et SPOTIFY_CLIENT_SECRET doivent être définis")

    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=[
            "user-read-private",
            "user-read-email",
            "user-top-read",
            "user-library-read",
            "playlist-read-private",
            "playlist-modify-public",
            "playlist-modify-private"
        ],
        cache_path=".spotify_cache",
        show_dialog=True,
    )


def get_spotify_client():
    """Retourne un client Spotify prêt à l'emploi."""
    auth = get_spotify_auth()
    return Spotify(auth_manager=auth)

def search_track(sp, query):
    """Cherche un morceau sur Spotify et retourne la liste de résultats."""
    try:
        api = SpotifyAPI(sp)
        results = api.search(query=query, limit=10)
        return results['tracks']['items']
    except Exception as e:
        raise Exception(f"Erreur lors de la recherche : {e}")


def format_recommendations(recommendations):
    """
    Transforme la réponse brute de l'API en une liste de dicts propres
    pour l'affichage (nom, artiste, album, url, image...).
    """
    formatted = []
    for track in recommendations.get('tracks', []):
        formatted.append({
            'name': track.get('name', 'Inconnu'),
            'artist': track['artists'][0]['name'] if track.get('artists') else 'Inconnu',
            'album': track['album']['name'] if track.get('album') else 'Inconnu',
            'id': track.get('id', ''),
            'popularity': track.get('popularity', 0),
            'url': track.get('external_urls', {}).get('spotify', ''),
            'preview_url': track.get('preview_url'),
            'image': (
                track['album']['images'][0]['url']
                if track.get('album', {}).get('images')
                else "https://media.licdn.com/dms/image/v2/D4E03AQHYrhOjn4nVmg/profile-displayphoto-shrink_200_200/profile-displayphoto-shrink_200_200/0/1693217951962?e=2147483647&v=beta&t=2G-b1Liu7zb6bnFpZGmDqZ9c6UpIhyUCxIS5U5jMFck"
            )
        })
    return formatted


def get_top_tracks_as_seeds(sp, limit=5):
    """Récupère les IDs des top morceaux de l'utilisateur (pour les utiliser comme seeds)."""
    try:
        top_tracks = sp.current_user_top_tracks(limit=limit)
        return [track['id'] for track in top_tracks['items']]
    except Exception as e:
        raise Exception(f"Erreur lors de la récupération des top tracks : {e}")


def get_top_artists_info(sp, limit=10):
    """Récupère les top artistes de l'utilisateur avec leurs genres."""
    try:
        top_artists = sp.current_user_top_artists(limit=limit)
        return [
            {'id': a['id'], 'name': a['name'], 'genres': a.get('genres', [])}
            for a in top_artists['items']
        ]
    except Exception:
        return []

def collect_seed_info(sp, seed_tracks):
    """Phase 1 : récupère les artistes et genres des morceaux seeds."""
    seed_artists_info = []
    all_genres = set()
    for track_id in seed_tracks:
        try:
            track_info = sp.track(track_id)
            artist_name = track_info['artists'][0]['name']
            artist_id = track_info['artists'][0]['id']
            seed_artists_info.append((artist_name, artist_id))
            artist_info = sp.artist(artist_id)
            for genre in artist_info.get('genres', []):
                all_genres.add(genre)
        except Exception:
            continue
    return seed_artists_info, all_genres


def search_by_seed_artists(api, seed_artists_info, collector, limit):
    """Phase 2 : cherche des morceaux des artistes seeds."""
    for artist_name, _ in seed_artists_info:
        try:
            results = api.search(query=artist_name, limit=10)
            for t in results.get('tracks', {}).get('items', []):
                collector.add(t)
                if len(collector) >= limit:
                    return
        except Exception:
            continue


def search_by_genres(api, genres, seed_artist_ids, collector, limit):
    """Phase 3 : cherche par genre, en mettant les nouveaux artistes en priorité."""
    genre_list = list(genres)
    random.shuffle(genre_list)
    for genre in genre_list[:5]:
        try:
            results = api.search(query=genre, limit=10)
            items = results.get('tracks', {}).get('items', [])
            # On sépare les artistes déjà connus des nouveaux
            new = [t for t in items if t.get('artists') and t['artists'][0]['id'] not in seed_artist_ids]
            known = [t for t in items if t.get('artists') and t['artists'][0]['id'] in seed_artist_ids]
            for t in new + known:
                collector.add(t)
                if len(collector) >= limit:
                    return
        except Exception:
            continue


def search_by_top_artists(api, top_artists, seed_artist_ids, collector, limit):
    """Phase 4 : cherche via les top artistes de l'utilisateur (hors seeds)."""
    other_artists = [a for a in top_artists if a.get('id') not in seed_artist_ids]
    random.shuffle(other_artists)
    for artist in other_artists[:5]:
        try:
            results = api.search(query=artist['name'], limit=10)
            for t in results.get('tracks', {}).get('items', []):
                collector.add(t)
                if len(collector) >= limit:
                    return
        except Exception:
            continue


def explore_albums(sp, artists_info, collector, limit):
    """Phase 5 : fouille les albums des artistes pour compléter."""
    random.shuffle(artists_info)
    for artist_name, artist_id in artists_info[:3]:
        try:
            albums = sp.artist_albums(artist_id, album_type='album', limit=2)
            for album in albums.get('items', []):
                album_tracks = sp.album_tracks(album['id'])
                for t in album_tracks.get('items', []):
                    if t['id'] not in collector.seen_ids:
                        full_track = sp.track(t['id'])
                        collector.add(full_track)
                    if len(collector) >= limit:
                        return
        except Exception:
            continue


def get_recommendations(sp, seed_tracks, limit=20, top_artists=None, **kwargs):
    """
    Génère des recommandations diversifiées à partir des seeds.
    Combine 5 stratégies de recherche pour varier les résultats.
    """
    if not sp:
        raise ValueError("Le client Spotify est requis")
    if not seed_tracks:
        raise ValueError("Au moins un morceau seed est requis")
    if isinstance(seed_tracks, str):
        seed_tracks = [seed_tracks]
    seed_tracks = seed_tracks[:5]

    api = SpotifyAPI(sp)
    collector = TrackCollector(excluded_ids=seed_tracks)

    # Phase 1 : infos sur les seeds
    seed_artists_info, all_genres = collect_seed_info(sp, seed_tracks)
    if top_artists:
        for artist in top_artists:
            for genre in artist.get('genres', []):
                all_genres.add(genre)
    seed_artist_ids = {a_id for _, a_id in seed_artists_info}

    # Phase 2 : recherche par artiste seed
    search_by_seed_artists(api, seed_artists_info, collector, limit)

    # Phase 3 : recherche par genre
    if len(collector) < limit and all_genres:
        search_by_genres(api, all_genres, seed_artist_ids, collector, limit)

    # Phase 4 : top artistes de l'utilisateur
    if len(collector) < limit and top_artists:
        search_by_top_artists(api, top_artists, seed_artist_ids, collector, limit)

    # Phase 5 : exploration des albums
    if len(collector) < limit:
        all_artists = list(seed_artists_info)
        if top_artists:
            all_artists += [(a['name'], a['id']) for a in top_artists if a.get('id') not in seed_artist_ids]
        explore_albums(sp, all_artists, collector, limit)

    return collector.result(limit)

def similar_by_genres(api, genres, seed_artist_id, collector, limit):
    """Phase 1 : cherche par genres de l'artiste (priorité aux AUTRES artistes)."""
    search_genres = list(genres)
    random.shuffle(search_genres)
    for genre in search_genres[:4]:
        try:
            results = api.search(query=genre, limit=10)
            items = results.get('tracks', {}).get('items', [])
            others = [t for t in items if t.get('artists') and t['artists'][0]['id'] != seed_artist_id]
            same = [t for t in items if t.get('artists') and t['artists'][0]['id'] == seed_artist_id]
            for t in others + same:
                collector.add(t)
                if len(collector) >= limit:
                    return
        except Exception:
            continue


def similar_by_featurings(sp, seed_album_id, collector, limit):
    """Phase 2 : regarde les featurings dans l'album du morceau."""
    if not seed_album_id:
        return
    try:
        album_tracks = sp.album_tracks(seed_album_id)
        for t in album_tracks.get('items', []):
            if t['id'] not in collector.seen_ids:
                for feat_artist in t.get('artists', [])[1:]:
                    try:
                        api = SpotifyAPI(sp)
                        feat_results = api.search(query=feat_artist['name'], limit=10)
                        for ft in feat_results.get('tracks', {}).get('items', []):
                            collector.add(ft)
                            if len(collector) >= limit:
                                return
                    except Exception:
                        continue
                    if len(collector) >= limit:
                        return
            if len(collector) >= limit:
                return
    except Exception:
        pass


def similar_by_track_name(api, track_name, seed_artist_id, collector, limit):
    """Phase 3 : cherche le même titre (covers, versions alternatives)."""
    try:
        results = api.search(query=track_name, limit=10)
        for t in results.get('tracks', {}).get('items', []):
            if t.get('artists') and t['artists'][0]['id'] != seed_artist_id:
                collector.add(t)
            if len(collector) >= limit:
                return
    except Exception:
        pass


def similar_from_other_albums(sp, seed_artist_id, seed_album_id, collector, limit):
    """Phase 4 : pioche dans les autres albums du même artiste."""
    try:
        albums = sp.artist_albums(seed_artist_id, album_type='album,single', limit=5)
        album_list = [a for a in albums.get('items', []) if a['id'] != seed_album_id]
        random.shuffle(album_list)
        for album in album_list[:2]:
            try:
                a_tracks = sp.album_tracks(album['id'])
                items = a_tracks.get('items', [])
                random.shuffle(items)
                for t in items[:3]:
                    if t['id'] not in collector.seen_ids:
                        full = sp.track(t['id'])
                        collector.add(full)
                    if len(collector) >= limit:
                        return
            except Exception:
                continue
    except Exception:
        pass


def similar_by_ambiance(api, genres, collector, limit):
    """Phase 5 : combine genre + mot-clé d'ambiance pour trouver des trucs."""
    combos = []
    ambiances = ['chill', 'energy', 'vibes', 'new', 'best', 'top']
    for g in genres[:3]:
        for a in random.sample(ambiances, min(2, len(ambiances))):
            combos.append(f"{g} {a}")
    random.shuffle(combos)
    for combo in combos[:4]:
        try:
            results = api.search(query=combo, limit=10)
            for t in results.get('tracks', {}).get('items', []):
                collector.add(t)
                if len(collector) >= limit:
                    return
        except Exception:
            continue


def get_similar_tracks(sp, track_id, limit=20):
    """
    Trouve des morceaux similaires à un titre donné.
    5 stratégies : genres, featurings, covers, autres albums, ambiance.
    """
    if not sp:
        raise ValueError("Le client Spotify est requis")

    api = SpotifyAPI(sp)
    collector = TrackCollector(excluded_ids=[track_id])

    # Récupérer les infos du morceau de départ
    try:
        track_info = sp.track(track_id)
    except Exception:
        return {'tracks': []}
    seed_artist_id = track_info['artists'][0]['id']
    seed_album_id = track_info.get('album', {}).get('id')
    track_name = track_info.get('name', '')
    genres = []
    try:
        artist_info = sp.artist(seed_artist_id)
        genres = artist_info.get('genres', [])
    except Exception:
        pass

    if genres:
        similar_by_genres(api, genres, seed_artist_id, collector, limit)
    if len(collector) < limit:
        similar_by_featurings(sp, seed_album_id, collector, limit)
    if len(collector) < limit:
        similar_by_track_name(api, track_name, seed_artist_id, collector, limit)
    if len(collector) < limit:
        similar_from_other_albums(sp, seed_artist_id, seed_album_id, collector, limit)
    if len(collector) < limit and genres:
        similar_by_ambiance(api, genres, collector, limit)

    return collector.result(limit)

def discover_find_artists(api, genre_query):
    """Phase 1 : cherche des artistes du genre et les classe (vérifiés vs fallback)."""
    genre_lower = genre_query.lower().strip()
    verified = []
    fallback = []
    try:
        results = api.search(query=genre_query, limit=10, search_type='artist')
        for artist in results.get('artists', {}).get('items', []):
            artist_genres = [g.lower() for g in artist.get('genres', [])]
            if not artist_genres:
                fallback.append(artist)
            elif any(genre_lower in g or g in genre_lower for g in artist_genres):
                verified.append(artist)
            else:
                fallback.append(artist)
    except Exception:
        pass
    return verified if verified else fallback


def discover_from_playlists(api, sp, genre_query, collector, limit):
    """Phase 2 : fouille des playlists du genre."""
    try:
        results = api.search(query=genre_query, limit=5, search_type='playlist')
        playlists = results.get('playlists', {}).get('items', [])
        if playlists:
            random.shuffle(playlists)
            for pl in playlists[:3]:
                try:
                    pl_tracks = sp.playlist_items(pl['id'], limit=10)
                    items = pl_tracks.get('items', [])
                    random.shuffle(items)
                    for item in items:
                        t = item.get('track')
                        if t and t.get('id'):
                            collector.add(t)
                        if len(collector) >= limit:
                            return
                except Exception:
                    continue
    except Exception:
        pass


def discover_from_artist_search(api, artists, collector, limit):
    """Phase 3 : cherche les morceaux des artistes trouvés."""
    random.shuffle(artists)
    for artist in artists:
        try:
            results = api.search(query=artist['name'], limit=10)
            for t in results.get('tracks', {}).get('items', []):
                if t.get('artists') and t['artists'][0]['id'] == artist['id']:
                    collector.add(t)
                if len(collector) >= limit:
                    return
        except Exception:
            continue


def discover_from_albums(sp, artists, collector, limit):
    """Phase 4 : explore les albums des artistes pour compléter."""
    for artist in artists[:3]:
        try:
            albums = sp.artist_albums(artist['id'], album_type='album,single', limit=3)
            for album in albums.get('items', []):
                a_tracks = sp.album_tracks(album['id'])
                items = a_tracks.get('items', [])
                random.shuffle(items)
                for t in items[:2]:
                    if t['id'] not in collector.seen_ids:
                        full = sp.track(t['id'])
                        collector.add(full)
                    if len(collector) >= limit:
                        return
        except Exception:
            continue


def discover_keyword_fallback(api, genre_query, collector, limit):
    """Phase 5 : recherche directe par mot-clé, en dernier recours."""
    try:
        results = api.search(query=genre_query, limit=10)
        for t in results.get('tracks', {}).get('items', []):
            collector.add(t)
            if len(collector) >= limit:
                return
    except Exception:
        pass


def discover_by_genre(sp, genre_query, limit=10):
    """
    Découvre des morceaux d'un genre donné.
    5 stratégies : artistes du genre, playlists, morceaux, albums, mot-clé.
    """
    api = SpotifyAPI(sp)
    collector = TrackCollector()

    selected_artists = discover_find_artists(api, genre_query)
    discover_from_playlists(api, sp, genre_query, collector, limit)

    if len(collector) < limit and selected_artists:
        discover_from_artist_search(api, selected_artists, collector, limit)
    if len(collector) < limit and selected_artists:
        discover_from_albums(sp, selected_artists, collector, limit)
    if len(collector) < limit:
        discover_keyword_fallback(api, genre_query, collector, limit)

    return collector.result(limit)

def create_playlist_from_recommendations(sp, name, tracks, description="", public=False):
    """Crée une playlist et y ajoute les morceaux. Wrapper vers PlaylistManager."""
    pm = PlaylistManager(sp)
    return pm.create(name, tracks, description, public)


def add_tracks_to_playlist(sp, playlist_id, tracks, avoid_duplicates=True):
    """Ajoute des morceaux à une playlist existante. Wrapper vers PlaylistManager."""
    pm = PlaylistManager(sp)
    return pm.add_to_existing(playlist_id, tracks, avoid_duplicates)


def get_user_playlists(sp, limit=50):
    """Récupère les playlists de l'utilisateur. Wrapper vers PlaylistManager."""
    pm = PlaylistManager(sp)
    return pm.get_user_playlists(limit)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(get_spotify_auth())
    print(get_spotify_client())