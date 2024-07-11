import asyncio
import sounddevice as sd
from scipy.io.wavfile import write
from shazamio import Shazam, Serialize
import os
import requests
from bs4 import BeautifulSoup
import time

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotifyConfig import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET  # Include your own Client ID and Client Secret

DURATION = 5  # seconds
SAMPLE_RATE = 44100  # Sample rate in Hz (CD quality)
FILENAME = "songSnippet.mp3"
ERRORSTR = "\nNo Song Detected. Please Try Again"
SLEEP_DURATION = 2 # seconds
shazam = Shazam()


def searchSongOnSpotify(title, artist):
    query = f'{title}, {artist}'
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))
    results = sp.search(q=query, type='track', limit=1)
    if results['tracks']['items']:
        track = results['tracks']['items'][0]
        return track

    else:
        return None

def getAudioFeatures(track):
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))
    audioFeatures = sp.audio_features(track['id'])
    if audioFeatures and len(audioFeatures) > 0:
        return audioFeatures[0]
    else:
        return None

def getKeyName(key):
    # Map Spotify key integers to musical key names
    key_mapping = {
        0: "C", 1: "C♯/D♭", 2: "D", 3: "D♯/E♭", 4: "E", 5: "F",
        6: "F♯/G♭", 7: "G", 8: "G♯/A♭", 9: "A", 10: "A♯/B♭", 11: "B"
    }
    return key_mapping.get(key, "Unknown")

def getMode(mode):
    return "Major" if mode == 1 else "Minor"

def record_audio():
    recording = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1)
    sd.wait()
    write(FILENAME, SAMPLE_RATE, recording)


async def recognizeSong(songPath: str):
    # pass bytes
    with open(songPath, "rb") as file:
        response = await shazam.recognize(file.read())
        if response and "track" in response:
            serializedResponse = Serialize.full_track(response)
            return serializedResponse.track
        else:
            return None


def getSongPlaying() -> [str, str]: # returns title, artist tuple
    attempts = 0
    done = False
    while not done:
        record_audio()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop = asyncio.get_event_loop_policy().get_event_loop()
        song = loop.run_until_complete(recognizeSong(FILENAME))

        if song is not None:
            return song.title, song.subtitle
        else:
            attempts += 1
            # print("Attempt " + str(attempts))

        if attempts == 3:
            return ERRORSTR


def main():
    print("Listening...")
    loops = 0
    lastSong = ""
    while True:
        song = getSongPlaying()
        # song = "Time", "Pink Floyd"
        if song == ERRORSTR:
            print(ERRORSTR)
        else:
            title, artist = song
            # print(song)
            track = searchSongOnSpotify(title, artist)
            if track is not None:
                audioFeatures = getAudioFeatures(track)
                key = audioFeatures['key']
                mode = audioFeatures['mode']
                keyName = getKeyName(key)
                modeName = getMode(mode)

                if loops == 0:
                    print("\nSong: " + track.get('name') + " by " + track.get('artists')[0].get('name'))
                    print("Key: " + keyName + " " + modeName)
                elif lastSong != track.get('name'):
                    print("\nSong: " + track.get('name') + " by " + track.get('artists')[0].get('name'))
                    print("Key: " + keyName + " " + modeName)
                    loops = 0
                lastSong = track.get('name')


            else:
                print("Error in searchSongOnSpotify")

        os.remove(FILENAME)  # delete temp file
        loops += 1
        # print(loops)
        time.sleep(SLEEP_DURATION)


if __name__ == '__main__':
    main()
