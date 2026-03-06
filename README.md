# SpotiFlow_IA

Spotify playlist builder, using groq to recommend musics matching your profile.

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SPOTIFLOW_IA - FLUX D'EXÉCUTION                     │
└─────────────────────────────────────────────────────────────────────────────┘

                                  main.py
                                    ↓
                    ┌───────────────────────────────┐
                    │   load_dotenv()               │
                    │   run_app() (Streamlit)       │
                    └───────────────┬───────────────┘
                                    ↓
                 ┌──────────────────────────────────────────┐
                 │  show_not_connected() / show_login()     │
                 │  (Authentification OAuth Spotify)        │
                 └──────────────┬───────────────────────────┘
                                ↓
                    [Callback Spotify reçu]
                                ↓
            ┌───────────────────────────────────────────────┐
            │   callback_handler.py                         │
            │   - Récupère le code d'auth Spotify           │
            │   - Échange code → token + refresh_token      │
            │   - Sauvegarde dans .spotify_cache            │
            └───────────┬─────────────────────────────────┘
                        ↓
        ┌────────────────────────────────────────────────┐
        │   show_connected_app(sp)                       │
        │   Utilisateur authentifié ✓                    │
        └────────────┬─────────────────────────────────┘
                     ↓
         [3 actions principales]
            ├─ Mes statistiques
            ├─ Recommandations
            └─ Se déconnecter


═══════════════════════════════════════════════════════════════════════════════
                            BLOC : MES STATISTIQUES
═══════════════════════════════════════════════════════════════════════════════

    show_statistics(sp)
            ↓
    ┌──────────────────────────────────────────────┐
    │  Étape 1: Analyse IA du profil               │
    │  • spotify_client.get_user_top_tracks()      │
    │  • spotify_client.get_user_top_artists()     │
    │          ↓                                   │
    │  • groq_client.analyze_music_profile()       │
    │    → Texte d'analyse personnalisée           │
    │  • groq_client.suggest_discoveries()         │
    │    → Suggestions d'artistes/albums           │
    └──────────────────────────────────────────────┘
            ↓
    ┌──────────────────────────────────────────────┐
    │  Étape 2: Top 3 Morceaux + Podium            │
    │  • spotify_client.get_user_top_tracks(10)    │
    │  • show_podium() + show_track_list_item()    │
    └──────────────────────────────────────────────┘
            ↓
    ┌──────────────────────────────────────────────┐
    │  Étape 3: Top 3 Artistes + Podium            │
    │  • spotify_client.get_user_top_artists(10)   │
    │  • show_podium() + show_artist_list_item()   │
    └──────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                        BLOC : RECOMMANDATIONS (4 ONGLETS)
═══════════════════════════════════════════════════════════════════════════════

show_recommendations(sp)
        ↓
    [4 onglets]


    ONGLET 1: Recommandations IA
    ─────────────────────────────
    tab_discover_IA(sp)
            ↓
    • Entrées: Humeur + durée (minutes)
            ↓
    Branche A: "Recommandations IA"
    ├─ spotify_client.get_user_top_tracks(10)
    ├─ spotify_client.get_user_top_artists(10)
    │       ↓
    ├─ groq_client.get_ai_recommendations()
    │   (mood, total_minutes)
    │       ↓
    ├─ Pour chaque morceau IA:
    │  • find_ai_track_on_spotify(sp, item)
    │    → Recherche Spotify + vérif artiste
    │       ↓
    ├─ display_ai_tracks_grid()
    │       ↓
    └─ show_save_to_playlist()

    Branche B: "Suggestions de découverte"
    ├─ groq_client.suggest_discoveries()
    │   (top_tracks, top_artists)
    │       ↓
    └─ Affichage texte des artistes/albums


    ONGLET 2: À partir de mes chansons
    ────────────────────────────────────
    tab_from_top_tracks(sp)
            ↓
    • spotify_client.get_top_tracks_as_seeds(10)
    • spotify_client.get_top_artists_info(10)
            ↓
    • spotify_client.get_recommendations()
    • format_recommendations()
            ↓
    • display_tracks_grid()
            ↓
    • show_save_to_playlist()


    ONGLET 3: À partir d'une recherche
    ──────────────────────────────────
    tab_similar_tracks(sp)
            ↓
    • Recherche manuel: search_track(query)
    • L'utilisateur sélectionne une chanson
            ↓
    • spotify_client.get_similar_tracks(track_id)
            ↓
    • display_tracks_grid()
            ↓
    • show_save_to_playlist()


    ONGLET 4: Par genre
    ──────────────────
    tab_discover_genre(sp)
            ↓
    • Sélection genre + nombre de résultats
            ↓
    • spotify_client.discover_by_genre()
            ↓
    • display_raw_tracks_grid()
            ↓
    • show_save_to_playlist()


═══════════════════════════════════════════════════════════════════════════════
                          BLOC : SAUVEGARDE PLAYLIST
═══════════════════════════════════════════════════════════════════════════════

show_save_to_playlist(sp, tracks)
        ↓
    [2 actions]


    ACTION 1: Créer une nouvelle playlist
    ──────────────────────────────────────
    show_create_new_playlist(sp, tracks)
            ↓
    • Saisir nom + is_public
            ↓
    • playlist_description_fragment()
      ├─ Saisir description manuelle
      │  OU
      └─ Bouton "IA" → groq_client.generate_playlist_description()
            ↓
    • spotify_client.create_playlist_from_recommendations()
      ├─ models.PlaylistManager.create()
      ├─ models.SpotifyAPI.put() [bypass dev-mode]
      ├─ Ajouter les morceaux
      └─ Retourner URL Spotify
            ↓
    ✓ Playlist créée sur Spotify


    ACTION 2: Ajouter à une playlist existante
    ──────────────────────────────────────────
    show_add_to_existing_playlist(sp, tracks)
            ↓
    • spotify_client.get_user_playlists()
      → models.PlaylistManager.get_user_playlists()
            ↓
    • L'utilisateur sélectionne une playlist
            ↓
    • Cocher "Éviter les doublons" (optionnel)
            ↓
    • spotify_client.add_tracks_to_playlist()
      ├─ models.TrackCollector.filter_duplicates()
      │  (si coché)
      ├─ models.SpotifyAPI.post() [bypass dev-mode]
      └─ Retourner stats (tracks_added, dupes_skipped)
            ↓
    ✓ Morceaux ajoutés à la playlist


═══════════════════════════════════════════════════════════════════════════════
                        MODULES ET RESPONSABILITÉS
═══════════════════════════════════════════════════════════════════════════════

┌──────────────────────────────────────────────────────────────────────────────┐
│ 📦 main.py                                                                   │
│ Point d'entrée du programme                                                  │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ 🎨 src/streamlit_app.py (790 lignes)                                         │
│ Interface utilisateur Streamlit - Gestion de l'UI et du flux                  │
│ • run_app() — Point d'entrée                                                 │
│ • show_*() — Écrans principaux                                               │
│ • tab_*() — Onglets de recommandations                                        │
│ • display_*() — Rendu des cartes de morceaux                                  │
│ • Utilitaires: normalize(), artist_matches(), find_ai_track_on_spotify()      │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ 🔐 src/callback_handler.py (125 lignes)                                      │
│ Gestion OAuth Spotify - Échange code ↔ tokens                                │
│ • handle_spotify_callback() — Reçoit le code d'auth                          │
│ • Échange code contre access_token + refresh_token                           │
│ • Stockage dans .spotify_cache pour persistence                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ 🎵 src/spotify_client.py (519 lignes)                                        │
│ Client Spotify - Requêtes API et logique métier                              │
│ Utilise 3 classes du modèle:                                                 │
│  • SpotifyAPI — Wrapper HTTP (bypass mode dev-mode 403s)                     │
│  • PlaylistManager — CRUD playlists                                          │
│  • TrackCollector — Déduplication de morceaux                                │
│ Fonctions principales:                                                       │
│  • get_spotify_client() — Initialise spotipy.Spotify                         │
│  • get_recommendations() — Recos via seed tracks/artists                      │
│  • search_track() — Recherche par titre                                       │
│  • get_similar_tracks() — Morceaux similaires                                 │
│  • create_playlist_from_recommendations() — Crée playlist + ajoute tracks     │
│  • add_tracks_to_playlist() — Ajoute à une existante                          │
│  • get_user_playlists() — Liste des playlists utilisateur                     │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ 🤖 src/groq_client.py (220 lignes)                                           │
│ Client Groq - Recommandations & analyses IA                                  │
│ • get_groq_client() — Initialise client Groq                                 │
│ • analyze_music_profile() — Analyse style musical                            │
│ • get_ai_recommendations() — Recos basées sur humeur+durée                    │
│ • suggest_discoveries() — Suggestions d'artistes/albums                      │
│ • generate_playlist_description() — Desc auto pour playlist                  │
│ • track_label() — Genre/label pour un morceau                                │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ 🏗️ src/models.py (240 lignes)                                                │
│ Classes métier centralisées - Architecture                                    │
│ Classe 1: TrackCollector                                                     │
│   • Déduplication de morceaux                                                │
│   • Limite d'artistes par track (max_same_artist_count)                       │
│   • Méthode: filter_duplicates()                                             │
│                                                                              │
│ Classe 2: SpotifyAPI                                                         │
│   • Wrapper HTTP direct (urllib)                                             │
│   • Bypass restriction "mode dev" de l'API Spotify                           │
│   • Méthodes: search(), post(), put(), get()                                 │
│                                                                              │
│ Classe 3: PlaylistManager                                                    │
│   • CRUD opérations sur playlists                                            │
│   • Batch add tracks                                                         │
│   • Méthodes: create(), get_user_playlists(), add_tracks()                   │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ 🌐 src/ngrok_config.py (80 lignes)                                           │
│ Tunnel ngrok - Expose localhost pour callbacks OAuth                         │
│ • setup_ngrok() — Lance tunnel sur port 8501                                 │
│ • get_public_url() — Retourne URL publique du tunnel                         │
│ • Permet à Spotify d'envoyer les callbacks même en local                     │
└──────────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                        FLUX DE DONNÉES - VUE COMPLÈTE
═══════════════════════════════════════════════════════════════════════════════

USER (Streamlit UI)
    ↓
    ├─→ [Authentification]
    │   ├─→ streamlit_app.show_login_button()
    │   ├─→ [Spotify OAuth]
    │   ├─→ callback_handler.handle_spotify_callback()
    │   └─→ cache sauvegardé (.spotify_cache)
    │
    ├─→ [Mes Statistiques]
    │   ├─→ spotify_client.get_user_top_tracks()
    │   ├─→ spotify_client.get_user_top_artists()
    │   ├─→ groq_client.analyze_music_profile()
    │   └─→ streamlit_app.show_podium()
    │
    ├─→ [Recommandations]
    │   ├─→ Tab 1: groq_client.get_ai_recommendations()
    │   │   └─→ find_ai_track_on_spotify() × N
    │   │
    │   ├─→ Tab 2: spotify_client.get_recommendations()
    │   │   (seed tracks/artists)
    │   │
    │   ├─→ Tab 3: spotify_client.search_track()
    │   │   + get_similar_tracks()
    │   │
    │   └─→ Tab 4: spotify_client.discover_by_genre()
    │
    └─→ [Sauvegarde Playlist]
        ├─→ models.PlaylistManager.create()
        ├─→ models.SpotifyAPI.post() [add tracks]
        ├─→ Ou: add_tracks_to_playlist()
        │   ├─→ models.TrackCollector.filter_duplicates()
        │   └─→ models.SpotifyAPI.post()
        └─→ ✓ Playlist Spotify mise à jour


═══════════════════════════════════════════════════════════════════════════════
                            STACK TECHNIQUE
═══════════════════════════════════════════════════════════════════════════════

FRONTEND:     Streamlit 1.54.0 (@st.fragment decorator)
API SPOTIFY:  spotipy 2.25.2 + urllib (wrapper direct)
IA:           Groq 1.0.0 (LLM recommandations)
AUTH:         pyngrok 7.5.0 (tunnel local → Spotify callbacks)
CONFIG:       python-dotenv, json, datetime, time
PYTHON:       3.13 (type hints, walrus operator support)
```
