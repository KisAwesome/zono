import zono.search as search
from mutagen.mp3 import MP3
import yt_dlp as youtube_dl
import requests
import datetime
import random
import pafy
import vlc
import os


def seconds_to_formatted_time(seconds):

    time_delta = datetime.timedelta(seconds=seconds)
    time_string = str(time_delta)

    if time_string.startswith("0:"):
        time_string = time_string[2:]
    if time_string.startswith("0"):
        time_string = time_string[1:]

    if time_string.startswith("1 day, "):
        time_string = time_string[8:]

    if "." in time_string:
        time_string = time_string[: time_string.index(".")]

    return time_string


if os.name == "nt":
    os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")


class _Song:
    @property
    def playing(self):
        if self._player is None:
            return False
        return self.player.is_playing()

    @property
    def artwork(self):
        if self.loaded_artwork:
            return self._artwork

        mp3 = MP3(self.path)
        artwork = mp3.get("APIC:", mp3.get("APIC:Front cover", mp3.get("covr")))
        if artwork:
            self._artwork = artwork.data
        else:
            self._artwork = None
        return self._artwork

    def get_file_tags(self, f):

        mp3 = MP3(f)
        try:

            title = mp3["TIT2"][0]

        except:

            title = f.split("/")[-1][:-4]

        try:

            artist = mp3["TPE1"][0]

        except:

            artist = "Unknown"

        try:
            album = mp3["TALB"].text[0]

        except:

            album = "None"

        return [title, artist, album]

    def __repr__(self):
        return self.get_info(id=False)

    def __str__(self):
        return self.get_info(id=False)

    def get_info(self, id=True):
        if not id:
            return f"{self.title} by {self.artist} from {self.album} {self.length} long {self.filesize_form}"

        return f"{self.title} by {self.artist} from {self.album} {self.length} long {self.filesize_form} id{self.id}"

    def info(self):
        return dict(
            title=self.title,
            artist=self.artist,
            album=self.album,
            length=self.length,
            filesize=self.filesize_form,
            id=self.id,
        )

    def elapsed_seconds(self):
        try:
            s = self.player.get_time() / 1000
            return s
        except:
            return -1

    def play(self, volume=100):
        if self.playing:
            return -1

        self.paused = False
        self.player.stop()
        self.player.play()
        self.player.audio_set_volume(volume)

    def stop(self):
        self.paused = False
        self.player.stop()

    def pause(self):
        self.player.pause()
        self.paused = not self.paused


class YoutubeSong(_Song):
    def __init__(self, url, end_event=None):

        self.loaded_artwork = False

        if isinstance(url, dict):
            self.url = url["url"]
            self.video = url
        else:
            self.video = None
            self.url = url
            if not self.check_if_song_exists(url):
                raise ValueError("Video does not exist")
        self.end_event = end_event
        self.title = self.video["title"]
        self.artist = self.video["channel"]
        self.album = "n/a"
        self.seconds = self.video.get("duration") or 0
        if self.seconds == 0:
            import pprint

            pprint.pprint(self.video)
            raise ValueError("Video is not available")

        self.length = seconds_to_formatted_time(self.seconds)
        self.id = self.video["id"]
        self.filesize = "n/a"
        self.filesize_form = "n/a"
        self.paused = False

        self.keywords = (
            self.title,
            self.artist,
            self.album,
            self.id,
            *self.video.get("tags", []),
        )

    @property
    def artwork(self):
        if self.loaded_artwork:
            return self._artwork

        allowed_codes = [200, 201]

        response = requests.get(self.video["thumbnail"])
        if response.status_code in allowed_codes:
            self._artwork = response.content
            return self._artwork

        else:
            print("Error:", response.status_code)

    def play(self, volume=100):
        # ydl_opts = {
        #     "format": "bestaudio/best",
        #     "postprocessors": [
        #         {
        #             "key": "FFmpegExtractAudio",
        #             "preferredcodec": "mp3",
        #             "preferredquality": "192",
        #         }
        #     ],
        #     "noplaylist": True,
        # }

        # try:
        #     with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        #         info = ydl.extract_info(self.url, download=False)
        #         audio_url = info["url"]
        #         self.video = info
        # except:
        #     return -1
        # audio = pafy.new(self.url).getbestaudio()
        # instance = vlc.Instance()
        # player = instance.media_player_new()
        # media = instance.media_new(self.url)
        # player.set_media(media)
        # player.play()
        self.player = vlc.MediaPlayer(self.url)
        self.player.audio_set_volume(volume)
        self._player = True
        self.is_playing = self.player.is_playing
        if callable(self.end_event):
            events = self.player.event_manager()
            events.event_attach(vlc.EventType.MediaPlayerEndReached, self.end_event)

    def check_if_song_exists(self, url):
        ydl_opts = {
            "quiet": True,
            "simulate": True,
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "noplaylist": True,
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                info_dict = ydl.extract_info(url, download=False)
                self.video = info_dict
                if info_dict["extractor"] == "youtube":
                    return True
            except youtube_dl.utils.DownloadError:
                pass
        return False


class Song(_Song):
    def __init__(self, path, end_event=None, _id=None):
        if not os.path.exists(path):
            raise FileNotFoundError
        self._player = None
        audio = MP3(path)
        self.elapsed_time = None

        self.id = _id
        self.paused = False
        tags = self.get_file_tags(path)
        self.title = tags[0]
        self.artist = tags[1]
        self.album = tags[2]

        tags.append(self.id)

        self.keywords = tuple(tags)

        if self.title == None:
            self.title = os.path.basename(path).replace(".mp3", "")

        self.seconds = audio.info.length
        self.length = seconds_to_formatted_time(self.seconds)

        filesize = round(os.stat(path).st_size / (1024 * 1024), 2)

        self.filesize = filesize
        self.filesize_form = f"{filesize}mb"
        self.loaded_artwork = False

        self.path = path
        self.end_event = end_event

    @property
    def player(self):
        if self._player is None:
            self._player = vlc.MediaPlayer(self.path)
            if callable(self.end_event):
                events = self.player.event_manager()
                events.event_attach(vlc.EventType.MediaPlayerEndReached, self.end_event)

            self.is_playing = self._player.is_playing

        return self._player


class Playlist:
    def __init__(self, path, end_event=None):
        r = os.listdir(path)
        self.path = path
        self.current_song = None
        self.volume = 100
        self.songno = -1
        self.album_song_dict = {}
        self.keywords_song_dict = {}
        self.title_song_dict = {}
        self.artist_song_dict = {}
        self.songs = []
        self.id_song_dict = {}

        for ID, i in enumerate(r):
            if not ".mp3" in i:
                continue

            el = Song(f"{path}/{i}", end_event, ID)
            self.artist_song_dict[el.artist] = el
            self.album_song_dict[el.album] = el
            self.id_song_dict[ID] = el
            self.songs.append(el)
            self.keywords_song_dict[el.keywords] = el
            self.title_song_dict[el.title] = el

        self.length_of_songs = len(self.songs)

    def isplaying(self):
        if self.current_song:
            return self.current_song.playing
        return False

    def search_playlist_id(self, idnumber):
        if idnumber in self.id_song_dict:
            return [self.id_song_dict[idnumber]]
        else:
            return []

    def search_playlist_artist(self, term):
        return [
            self.artist_song_dict[i]
            for i in self.artist_song_dict
            if term.lower() in i.lower()
        ]

    def search_play_list_album(self, term):
        return [
            self.album_song_dict[i]
            for i in self.album_song_dict
            if term.lower() in i.lower()
        ]

    def sort_by_high_song_length(self):
        return [
            self.id_song_dict[elem[1]]
            for elem in sorted(
                [(song.seconds, song.id) for song in self.songs],
                key=lambda x: x[0],
                reverse=False,
            )
        ]

    def sort_by_a_z(self):
        return [
            self.id_song_dict[elem[1]]
            for elem in sorted(
                [(song.title, song.id) for song in self.songs], key=lambda x: x[0]
            )
        ]

    def sort_by_z_a(self):
        return [
            self.id_song_dict[elem[1]]
            for elem in sorted(
                [(song.title, song.id) for song in self.songs],
                key=lambda x: x[0],
                reverse=True,
            )
        ]

    def sort_by_low_song_length(self):
        return [
            self.id_song_dict[elem[1]]
            for elem in sorted(
                [(song.seconds, song.id) for song in self.songs],
                key=lambda x: x[0],
                reverse=True,
            )
        ]

    def search_playlist_song_name(self, song_name):
        return [
            self.title_song_dict[i]
            for i in self.title_song_dict
            if song_name.lower() in i.lower()
        ]

    def search_playlist(self, term):
        return [
            self.keywords_song_dict[i]
            for i in self.keywords_song_dict
            if search.search(i).search(term)
        ]

    def shuffle(self):
        self.current_song = random.choice(self.songs)
        self.current_song.play(self.volume)

    def forward(self):
        if self.songno + 1 > len(self.songs):
            self.songno = 0

        self.current_song = self.songs[self.songno + 1]
        self.songno += 1

        self.current_song.play(self.volume)

    def back(self):
        if self.songno == 0:
            self.songno = len(self.songs) - 1
            self.current_song = self.songs[self.songno]
            self.current_song.play(self.volume)
            return
        self.current_song = self.songs[self.songno - 1]
        self.songno -= 1
        self.current_song.play(self.volume)

    def stop(self):
        if self.current_song is None:
            return
        self.current_song.stop()
        self.current_song = None


class YouTubePlaylist(Playlist):
    def __init__(self, url, end_event=None):
        entries = self.get_playlist(url)
        if entries is False:
            raise ValueError("Unable to access YouTube playlist")

        self.current_song = None
        self.volume = 100
        self.songno = -1
        self.album_song_dict = {}
        self.keywords_song_dict = {}
        self.title_song_dict = {}
        self.artist_song_dict = {}
        self.songs = []
        self.id_song_dict = {}

        for _id, i in enumerate(entries):
            if i["duration"] is None:
                continue
            song = YoutubeSong(i, end_event)
            song.video_id = str(song.id)
            song.id = _id
            self.artist_song_dict[song.artist] = song
            self.album_song_dict[song.album] = song
            self.id_song_dict[song.id] = song
            self.songs.append(song)
            self.keywords_song_dict[song.keywords] = song
            self.title_song_dict[song.title] = song

        self.length_of_songs = len(self.songs)

    def get_playlist(self, url):
        ydl_opts = {
            "extract_flat": "in_playlist",
            "skip_download": True,
            "quiet": True,
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                playlist_info = ydl.extract_info(url, download=False)
            except youtube_dl.utils.DownloadError:
                return False

        if "entries" not in playlist_info:
            return False

        return playlist_info["entries"]


if __name__ == "__main__":
    d = YoutubeSong('https://www.youtube.com/watch?v=6SLD1ZQZ_4Y')
    d.play()
    input()