#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Banana banana banana.
#
# Dependencies : python-mpd
#                pysqlite

import os.path
import mpd
import random
import sqlite3
import time
from socket import error as socketerror

## Config
server="127.0.0.1"
port=6600
trigger=8 # A new song will be added when the playlist
          #  has less songs than this
delay=0.8 # Make this higher if hogging cpu (not likely) 
playtime=70 # Percentage of a song that must be played before
            #  play count is incremented
mintime=25 # A song must be longer than mintime seconds for
             # its playcount to be incremented. This way, samples
             # and other short bonus tracks' karma will quickly dive
             # and the songs will seldom be added.
dbfile="~/music/.autodb"
flood_delay=12*60 # Minutes to wait before adding the same song again
## End config

db = sqlite3.connect(os.path.expanduser(dbfile))
cursor = db.cursor()

random.seed()
client = mpd.MPDClient()

## Functions

def reconnect(iter=0):
  print "Reconnecting"
  if iter==10:
    print "Connection lost"
    exit(1)
  try:
    client.connect(server, port)
  except socketerror:
    reconnect(iter+1)


def addsong():
  rand=random.uniform(-0.1, 1.5)
  cursor.execute("select * from songs where karma>? and time < ?", (rand, int(time.time()-(60*(flood_delay-trigger*3)))))
  data=cursor.fetchall()
  if data == []:
    addsong()
  else:
    songdata=random.choice(data)
    newkarma=karma(songdata, 2)
    cursor.execute("update songs set added=?, karma=?, time=? where file=?", (songdata[2]+1, newkarma, int(time.time()), songdata[0],))
    db.commit()
    client.add(songdata[0])

def getsong(song):
  cursor.execute("select * from songs where file=?", (song,))
  data=cursor.fetchone()
  if data == None:
    cursor.execute("insert into songs values (?, 0, 0, 0.5, 0)", (song,))
    data = (song, 0, 0)
  return data

def karma(songdata, which=0):
  listened=float(songdata[1])
  added=float(songdata[2])

  if which == 1:
    listened+=1
  elif which == 2:
    added+=1

  if listened==0:
    listened=0.1
  if added==0:
    added=0.1
  return listened/added

def listened(song):
  songdata=getsong(song)
  newkarma=karma(songdata, 1)
  cursor.execute("update songs set listened=?, karma=?, time=? where file=?", (songdata[1]+1, newkarma, int(time.time()), song))
  db.commit()

## End functions

try:
  client.connect(server, port)
except socketerror:
  reconnect()

## Startup
print "Updating database..."
cursor.execute("create table if not exists songs(file text, listened int, added int, karma real, time int);")
stale=[]
for song in cursor.execute("select file from songs"):
  if not os.path.isfile("/home/codl/music/" + song[0]):
    stale.append(song[0])
for song in stale:
  cursor.execute("delete from songs where file=?", (song,))
db.commit()
for song in client.list("file"):
  nothing=getsong(unicode(song, "utf-8"))
db.commit()
print "Done"
armed=1

while True:
  while len(client.playlist()) < trigger:
    addsong()

  if client.status()['state'] == "play":
    times=client.status()['time'].split(":")
    pos=int(times[0])
    end=int(times[1])
    if armed==1 and (end > mintime) and (pos > playtime*end/100):
      armed=0 # Disarm until the next song
      listened(unicode(client.currentsong()["file"], "utf-8"))
      songid=(client.currentsong()["id"])

  if armed==0 and not songid == client.currentsong()["id"]: 
    armed=1
  
  time.sleep(delay)
