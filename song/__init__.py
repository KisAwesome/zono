import time
import zono.search as search
from mutagen.mp3 import MP3
from random import choice
from mutagen.id3 import ID3
import vlc
import os

print("Thnaks for using zono")

# os.add_dll_directory(r'C:\Program Files\VideoLAN\VLC')


class song:
    ids = []

    def __init__(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError
        self.mp3 = vlc.MediaPlayer(path)
        self.audio = MP3(path)
        self.elapsed_time = None

        self.ID3 = ID3(path)

        self.id = len(song.ids) + 1
        song.ids.append(self.id)
        # self.mp3_ide_tag = EasyMP3(path)
        # print(self.mp3_ide_tag)
        self.paused = False
        # print(self.audio['TIT2'][0])

        # self.audiofile = eyed3.load(path)
        self.tags = self.get_file_tags(path)
        self.title = self.tags[0]
        self.artist = self.tags[1]
        self.album = self.tags[2]

        # self.ide = ID3(path)e3
        self.tag_iter = list(self.tags)
        self.tag_iter.append(str(self.id))

        tags_ = []

        for i in self.tag_iter:
            tags_.append(str(i))
            # print(i)
        self.keywords = tuple(tags_)

        if self.title == None:
            self.title = os.path.basename(path).replace(".mp3", "")
        # print(self.ide.pprint())
        # try:
        #     self.pict = self.ide.get("APIC:").data
        #     self.picture = Image.open(BytesIO(self.pict))
        #     self.album_art = self.audiofile.tag.album_artist
        # except:
        #     self.album_art = None
        # self.composer = self.audiofile.tag.composer
        # self.genre = self.audiofile.tag.genre
        self.playing = False

        self.seconds = self.audio.info.length
        length = self.audio.info.length
        minutes = int(length / 60)
        seconds = int(length % 60)
        self.length = f"{minutes}:{seconds}"
        if seconds <= 9:
            self.length = f"{minutes}:0{seconds}"

        # print(self.length)

        s = os.stat(path).st_size
        filesize = round(os.stat(path).st_size / (1024 * 1024), 2)

        self.filesize = filesize
        self.filesize_form = f"{filesize}mb"
        # print(self.filesize)

        self.path = path

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

            rating = mp3["POPM:"].rating

        except:

            rating = "0"
        try:
            # print(mp3['TALB'])
            album = mp3["TALB"].text[0]

        except:

            album = None

        return (title, artist, album)

    def __repr__(self):
        return f"{self.title} by {self.artist} from {self.album} {self.length} long {self.filesize_form} id{self.id}"

    def get_info(self, Id=True):
        if not Id:
            return f"{self.title} by {self.artist} from {self.album} {self.length} long {self.filesize_form}"

        return f"{self.title} by {self.artist} from {self.album} {self.length} long {self.filesize_form} id{self.id}"

    def elapsed_seconds(self):
        try:
            s = self.mp3.get_time() / 1000
            return s
        except:
            return -1

    def play(self, volume):
        if self.isplaying():
            return -1

        self.playing = True
        self.paused = False

        self.mp3.play()
        self.mp3.audio_set_volume(volume)

    def sync(self):
        while self.isplaying():
            print("f")
            time.sleep(0.1)

    def stop(self):
        self.playing = False
        self.paused = False
        self.mp3.stop()

    def pause(self):
        self.mp3.pause()
        if self.paused:
            self.paused = False
        else:
            self.paused = True

    def isplaying(self):
        if self.paused:
            return True
        try:
            if self.mp3.is_playing():
                return True
            return False
        except:
            return -1


class playlist:
    shut = False

    def __init__(self, path, Print=True):
        r = os.listdir(path)
        self.playing = False
        self.print = Print
        self.path = path
        self.curr_song = None
        self.volume = 100
        self.songno = -1
        self.ids = []
        self.album_song_dict = {}
        self.keywords_song_dict = {}
        self.title_song_dict = {}
        self.artist_song_dict = {}
        self.songs = []
        self.current_playing = None
        self.id_song_dict = {}

        shut = False
        if not r:
            r = []
            shut = True

        if not shut:
            DICT = {}
            song.ids.clear()
            for i in r:
                if not ".mp3" in i:
                    continue

                ID = len(self.ids) + 1
                el = song(path + "/" + i)
                DICT[(el.title, el.id)] = 0
                self.artist_song_dict[(el.artist, el.id)] = el
                self.album_song_dict[(el.album, el.id)] = el
                self.id_song_dict[ID] = el
                self.songs.append(el)
                self.ids.append(ID)
                self.keywords_song_dict[el.keywords] = el
                self.title_song_dict[el.title] = el

        self.length_of_songs = len(self.songs)

        # if os.path.exists(path+'\\playlist_inf\\plays.pickle'):
        #     pass
        # else:
        #     os.makedirs(path+'\\playlist_inf')
        #     with open(path+'\\playlist_inf\\plays.pickle','wb') as file:
        #         pickle.dump(DICT,file)

    def search_playlist_id(self, idnumber):
        if idnumber in self.id_song_dict:
            return [self.id_song_dict[idnumber]]
        else:
            return []
        # for i in

    def search_playlist_artist(self, term):

        song_mathing_criteria = []
        for i in self.artist_song_dict:
            hold_search = search.search([str(i[0]).lower()])
            ans = hold_search.search(str(term.lower()))
            if ans:
                song_mathing_criteria.append(self.artist_song_dict[i])
                # print(song_mathing_criteria)
        return song_mathing_criteria

    def search_play_list_album(self, term):
        song_matching_criteria = []
        for i in self.album_song_dict:
            hold_search = search.search([str(i[0]).lower()])
            ans = hold_search.search(str(term.lower()))

            if ans:
                song_matching_criteria.append(self.album_song_dict[i])

        return song_matching_criteria

    def sort_by_high_song_length(self):
        return [
            self.id_song_dict[elem[1]]
            for elem in [(song.seconds, song.id) for song in self.songs].sort(
                key=lambda x: x[0], reverse=False
            )
        ]

    def sort_by_a_z(self):
        return [
            self.id_song_dict[elem[1]]
            for elem in [(song.name, song.id) for song in self.songs].sort(
                key=lambda x: x[0]
            )
        ]

    def sort_by_z_a(self):
        return [
            self.id_song_dict[elem[1]]
            for elem in [(song.name, song.id) for song in self.songs].sort(
                key=lambda x: x[0], reverse=True
            )
        ]

    def sort_by_low_song_length(self):
        return [
            self.id_song_dict[elem[1]]
            for elem in [(song.seconds, song.id) for song in self.songs].sort(
                key=lambda x: x[0], reverse=True
            )
        ]

    def search_playlist_song_name(self, song_name):
        songs_matching_criteria = []
        for i in self.title_song_dict:
            hold_search = search.search([str(i).lower().strip()])
            ans = hold_search.search(str(song_name).lower().strip())

            if ans:
                songs_matching_criteria.append(self.title_song_dict[i])
            # print(songs_matching_criteria)
        return songs_matching_criteria

    def search_playlist(self, term):
        songs_matching_criteria = []
        for i in self.keywords_song_dict:
            # print(i)
            hold_search = search.search(i)
            ans = hold_search.search(term.lower())

            if ans:
                songs_matching_criteria.append(self.keywords_song_dict[i])
                # print(self.keywords_song_dict[i])
                # print(songs_matching_criteria)
        # print(songs_matching_criteria)

        return songs_matching_criteria

    def play(self, internal=False, mode="shuffle", state="forword"):
        global song

        if self.playing:
            return -1

        self.playing = True
        # song_ = choice(self.songs
        if mode == "shuffle":
            song_ = choice(self.songs)
        elif mode == "skip":
            if state == "back":
                if self.songno < 0:
                    self.songs[0].play(self.volume)
                    self.songno += 1
                    self.curr_song = self.songs[0]
                    return 0

                current_song = self.songs[self.songno - 1]
                self.songno -= 1
                self.curr_song = current_song
                current_song.play(self.volume)
                return 0
            elif state == "forword":
                if self.songno + 1 > len(self.songs):
                    return 0
                current_song = self.songs[self.songno + 1]

                self.songno += 1

                current_song.play(self.volume)

                self.curr_song = current_song

                return 0

        self.curr_song = song_
        song_.play(self.volume)
        time.sleep(0.09)

    def stop(self):
        self.playing = False
        self.curr_song.stop()
