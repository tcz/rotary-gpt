import os
from collections import Counter
from time import sleep

import spotipy
from spotipy import SpotifyOAuth

class Spotify:
    SCOPE = "user-library-read,user-read-playback-state,user-read-currently-playing,user-modify-playback-state,app-remote-control,streaming"
    COPYRIGHT_FREE_PLAYLIST = 'spotify:playlist:4GjBqUD0NyP09TwY6VeChd'

    def __init__(self, device_id):
        self.client = None
        self.device_id = device_id

    def play_copyright_free_songs(self, *args):
        return self._play(Spotify.COPYRIGHT_FREE_PLAYLIST, 'Copyright-free songs')

    def play_songs_from(self, parameters):
        if 'artist' not in parameters:
            return 'Missing artist name.'

        artist = parameters['artist']

        client = self._get_client()
        result = client.search(artist, type='artist')

        if len(result['artists']['items']) == 0:
            return 'Artist not found.'

        artist_id = result['artists']['items'][0]['id']
        artist_name_found = result['artists']['items'][0]['name']

        top_tracks = client.artist_top_tracks(artist_id)
        uris = [track['uri'] for track in top_tracks['tracks']]

        return self._play(uris, 'Top songs from ' + artist_name_found)

    def play_song(self, parameters):
        if 'song' not in parameters:
            return 'Missing song name.'

        song = parameters['song']

        client = self._get_client()
        result = client.search(song, type='track')

        if len(result['tracks']['items']) == 0:
            return 'Song not found.'

        track_uri = result['tracks']['items'][0]['uri']
        track_name_found = result['tracks']['items'][0]['name'] + ' by ' + result['tracks']['items'][0]['artists'][0]['name']

        uris = [track_uri,]

        result = client.recommendations(seed_tracks=[uris[0]], limit=50)
        uris = uris + [track['uri'] for track in result['tracks']]

        return self._play(uris, track_name_found)

    def play_songs_like_the_current_song(self, *args):
        client = self._get_client()

        currently_playing = client.currently_playing()
        result = client.recommendations(seed_tracks=[currently_playing['item']['uri']], limit=50)
        uris = [track['uri'] for track in result['tracks']]

        if len(uris) == 0:
            return 'No similar songs found.'

        return self._play(uris, 'Songs like ' + currently_playing['item']['name'] + ' by ' + currently_playing['item']['artists'][0]['name'])

    def play_some_high_energy_songs(self, *args):
        client = self._get_client()

        liked_songs = client.current_user_saved_tracks(limit=5)
        liked_song_uris = [song['track']['uri'] for song in liked_songs['items']]

        result = client.recommendations(seed_tracks=liked_song_uris,
                                        min_energy=0.9,
                                        limit=50)
        uris = [track['uri'] for track in result['tracks'] if 75 > track['popularity'] > 0]

        return self._play(uris, 'High energy songs')

    def pause(self, *args):
        if not self._is_device_available():
            return 'The configured Spotify speaker is not available.'
        self._get_client().pause_playback()
        return 'Playback paused.'

    def resume(self, *args):
        if not self._is_device_available():
            return 'The configured Spotify speaker is not available.'
        self._get_client().start_playback()
        return 'Playback resumed.'

    def lower_volume(self, *args):
        current_volume = self._get_current_volume()
        if current_volume is None:
            return 'The configured Spotify speaker is not available.'
        new_volume = current_volume - 5
        self._get_client().volume(new_volume, device_id=self.device_id)

        return 'Volume lowered to ' + str(new_volume)

    def raise_volume(self, *args):
        current_volume = self._get_current_volume()
        if current_volume is None:
            return 'The configured Spotify speaker is not available.'
        new_volume = current_volume + 5
        self._get_client().volume(new_volume, device_id=self.device_id)

        return 'Volume raised to ' + str(new_volume)

    def next(self, *args):
        if not self._is_device_available():
            return 'The configured Spotify speaker is not available.'
        self._get_client().next_track(device_id=self.device_id)

        return 'Track skipped.'

    def _play(self, uri, playback_name):
        if not self._is_device_available():
            return 'The configured Spotify speaker is not available.'

        if isinstance(uri, list):
            self._get_client().start_playback(device_id=self.device_id, uris=uri)
        elif 'track' in uri:
            self._get_client().start_playback(device_id=self.device_id, uris=[uri])
        else:
            self._get_client().start_playback(device_id=self.device_id, context_uri=uri)

        return 'Playing ' + playback_name

    def _is_device_available(self):
        devices = self._get_client().devices()
        for device in devices['devices']:
            if device['id'] == self.device_id:
                return True

        return False

    def _get_current_volume(self):
        devices = self._get_client().devices()
        for device in devices['devices']:
            if device['id'] == self.device_id:
                return device['volume_percent']

        return None

    def _get_client(self):
        if self.client is not None:
            return self.client

        self.client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=Spotify.SCOPE))

        return self.client


spotify = Spotify(os.environ['SPOTIFY_DEVICE_ID'])

GPT_FUNCTIONS = [
    {
        "name": "play_copyright_free_songs",
        "description": "Plays a playlist of songs that are free to use and copyright-free.",
        "callable": spotify.play_copyright_free_songs,
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        }
    },
    {
        "name": "play_songs_from",
        "description": "Plays songs from a given artist or band.",
        "callable": spotify.play_songs_from,
        "parameters": {
            "type": "object",
            "properties": {
                "artist": {
                    "type": "string",
                    "description": "The name of the arist of band to play songs from.",
                },
            },
            "required": ["artist"],
        }
    },
    {
        "name": "play_song",
        "description": "Plays a given song based on the title and optionally an artist or name.",
        "callable": spotify.play_song,
        "parameters": {
            "type": "object",
            "properties": {
                "song": {
                    "type": "string",
                    "description": "The name of the song with out without the artist. For example: Bohemian Rhapsody or Bohemian Rhapsody by Queen.",
                },
            },
            "required": ["song"],
        }
    },
    {
        "name": "play_songs_like_the_current_song",
        "description": "Plays songs that are similar to the currently played song.",
        "callable": spotify.play_songs_like_the_current_song,
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        }
    },
    {
        "name": "play_some_high_energy_songs",
        "description": "Plays high evergy songs that are danceable and boost your vigour.",
        "callable": spotify.play_some_high_energy_songs,
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        }
    },
    {
        "name": "pause",
        "description": "Pauses playback.",
        "callable": spotify.pause,
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        }
    },
    {
        "name": "resume",
        "description": "Resumes playback.",
        "callable": spotify.resume,
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        }
    },
    {
        "name": "lower_volume",
        "description": "Lowers volume.",
        "callable": spotify.lower_volume,
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        }
    },
    {
        "name": "raise_volume",
        "description": "Raises volume.",
        "callable": spotify.raise_volume,
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        }
    },
    {
        "name": "next",
        "description": "Skips to the next track.",
        "callable": spotify.next,
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
        }
    },
]

if __name__ == "__main__":
    client = spotify._get_client()

    devices = client.devices()
    for device in devices['devices']:
        print(device['name'], device['id'])