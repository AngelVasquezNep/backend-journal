import os
import sqlite3

from music_data import GENRES, ARTISTS, ALBUMS, TRACKS

# Nasty but enough to play
try:
    os.remove('db.sqlite3')
except OSError:
    pass

connexion = sqlite3.connect('db.sqlite3')
cursor = connexion.cursor()

cursor.execute("""CREATE TABLE Track (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    title       TEXT,
                    rating      INTEGER,
                    len         INTEGER,
                    count       INTEGER,
                    album_id    INTEGER,
                    genre_id    INTEGER,
                    FOREIGN KEY(album_id) REFERENCES Album(id),
                    FOREIGN KEY(genre_id) REFERENCES Genre(id)
                )""")

cursor.execute("""CREATE TABLE Album(
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    title       TEXT,
                    artist_id   INTEGER,
                    FOREIGN KEY(artist_id) REFERENCES Artist(id)
                )""")

cursor.execute("""CREATE TABLE Genre (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT
                )""")

cursor.execute("""CREATE TABLE Artist (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT
                )""")


connexion.commit()


cursor.executemany("INSERT INTO Genre (name) VALUES (?)", [
        (genre.get("name"),) for genre in GENRES
    ])
cursor.executemany("INSERT INTO Artist (name) VALUES (?)", [
        (artist.get("name"),) for artist in ARTISTS
    ])
cursor.executemany("INSERT INTO Album (title, artist_id) VALUES (?, ?)", [
        (album.get("title"), album.get("artist_id"),) for album in ALBUMS                
    ])
cursor.executemany("""
    INSERT INTO Track (title, rating, len, count, album_id, genre_id) VALUES (?, ?, ?, ?, ?, ?)""", [
        (track.get("title"), track.get("rating"), track.get("len"),
        track.get("count"), track.get("album_id"), track.get("genre_id"),)
        for track in TRACKS
    ])


# Just testign an idea
import re

class Serializer:
    def __init__(self, query:str, row: tuple):
        self.query = query
        self.row = row
        self.fields = re.search(r"(?<=SELECT\s)(.*?)(?=\sFROM)", query).group(0).split(', ')

    def to_json(self):
        data = {}
        for index, field in enumerate(self.fields):
            data[field] = self.row[index]
        return data

query = "SELECT Album.title, Album.artist_id, Artist.id, Artist.name FROM Album JOIN Artist ON Album.artist_id = Artist.id"
for track in cursor.execute(query):
    print(Serializer(query, track).to_json())
