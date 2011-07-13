#!/usr/bin/env python2
# -*- coding: utf-8 -*-
'''
Keeps your MPD playlist filled with music you like

Dependencies : python-mpd
               pysqlite
'''

import os
import mpd
import random
import sqlite3
import time
import io
import sys
from socket import error as socketerror

## Config
server = "localhost"
port = 6600
password = False # Set to False if none
musicdir = "~/music/"
trigger = 8 # A new song will be added when the playlist
            #  has less songs than this
            #  You can set this to 0 if you only want the stats
playtime = 70 # Percentage of a song that must be played before
              #  play count is incremented
mintime = 25 # Minimum length of a track for it
             #  to be considered a song (in seconds)
flood_delay = 12*60 # Minutes to wait before adding the same song again

mindelay = 0.5 # These are the min and max polling delays
maxdelay = 3.0 # These values should be sane for pretty much any
               # remotely recent computer. Increase them if cpu usage
               # is too high
tries = 3 # Retry connecting this many times

debug = False
logfile = "/tmp/autoplay.log"
## /Config

#enc = sys.getfilesystemencoding()
enc = "UTF-8"

## Functions
def log(msg, stdout=False):
  """Logs to file, and optionally to stdout. Obvious enough"""
  if stdout or debug:
    print msg
  logio.write(unicode(msg, enc)+"\n")

def reconnect(i=1):
  if i == tries:
    log("Could not connect to server D:", stdout=True)
    exit(1)
  log("Tried "+str(i)+" times")
  try:
    client.connect(server, port)
  except socketerror:
    reconnect(i+1)


def addsong():
  """Adds a semi-random song to the playlist"""
  rand = random.uniform(-0.5, 2)
  cursor.execute("select * from songs where karma>? and time < ?",
    (rand, int(time.time()-(60*(flood_delay-trigger*3)))))
  data = cursor.fetchall()
  if data == []:
    updateone()
    addsong()
  else:
    songdata = random.choice(data)
    newkarma = karma(songdata, 2)
    cursor.execute(
      "update songs set added=?, karma=?, time=? where file=?",
      (songdata[2]+1, newkarma, int(time.time()), songdata[0],)
    )
    db.commit()
    log(("Adding song "+songdata[0]+" - Karma = "+
      str(songdata[3])+" - Karma limit = "+str(rand)).encode(enc))
    client.add(songdata[0].encode(enc))

def getsong(songfile):
  """Retrieve song data from DB"""
  cursor.execute("select * from songs where file=?", (songfile,))
  data = cursor.fetchone()
  if data == None:
    cursor.execute("insert into songs values (?, 0, 0, 0.5, 0)",
      (songfile,))
    data = (songfile, 0, 0, 0.5, 0)
  return data

def karma(songdata, which=0):
  """Returns karma for a song"""
  listened = float(songdata[1])
  added = float(songdata[2])

  if which == 1:
    listened += 1
  elif which == 2:
    added += 1

  if listened == 0:
    listened = 0.1
  if added == 0:
    added = 0.1
  return listened/added

def listened(songdata):
  newkarma = karma(songdata, 1)
  cursor.execute(
    "update songs set listened=?, karma=?, time=? where file=?",
    (songdata[1]+1, newkarma, int(time.time()), songdata[0])
  )
  log(("Listened to "+songdata[0]+" - Karma = "+
    str(newkarma)+" - Listens = "+str(songdata[1]+1)).encode(enc))
  db.commit()
## /Functions

random.seed()
client = mpd.MPDClient()

logio = io.open(logfile, "at", buffering=1, encoding=enc)
log("Connecting...")
try:
  client.connect(server, port)
except socketerror:
  reconnect()

if password:
  try:
    log("Using password")
    client.password(password)
  except mpd.CommandError:
    log("Wrong password?", stdout=True)
    exit(2)

log("Connected")

allsongs = []
def updateone():
  if allsongs == []:
    cursor.execute("create table if not exists songs(\
      file text, listened int, added int, karma real, time int\
      );")
    db.commit()
    for song in client.list("file"):
      allsongs.append(unicode(song, enc))
    for song in cursor.execute("select file from songs;"):
      allsongs.append(song[0])
    random.shuffle(allsongs)

  song = allsongs.pop()
  #for j in range(i) : allsongs.pop() #Remove duplicates
  # Verify in DB
  cursor.execute("select * from songs where file=?", (song,))
  if cursor.fetchone() == None:
    cursor.execute("insert into songs values (?, 0, 0, 5, 0)",
      (song,))
    db.commit()

  # Verify in fs
  if not os.path.isfile((os.path.expanduser(musicdir) +
    song).encode(enc)):
    cursor.execute("delete from songs where file=?", (song,))


db = sqlite3.connect(os.path.expanduser((musicdir+".autodb").encode(enc)))
cursor = db.cursor()

for arg in sys.argv:
  if arg == "-u":
    log("Starting complete update", True)
    updateone()
    while allsongs != []:
      if len(allsongs) % 200 == 0:
        log(str(len(allsongs)) + " left", True)
      updateone()
    log("Done", True)

if len(sys.argv)==1:
  for i in range(30):
    updateone()

  armed = 1
  delay = mindelay

  log("Ready")


  while __name__ == "__main__":
    updateone()

    try:
      if client.status()["consume"] == "0":
        cursongid = client.status()["songid"]
        for song in client.playlistid():
          if song["id"] == cursongid:
            plistlength = int(song["pos"]) + trigger

      else:
        plistlength = trigger

      if len(client.playlist()) < plistlength:
        addsong()
        delay = mindelay
      if client.status()['state'] == "play":
        times = client.status()['time'].split(":")
        pos = int(times[0])
        end = int(times[1])
        currentsong = client.currentsong()
        if armed == 0 and "id" in currentsong and not songid == currentsong["id"]:
          armed = 1
        elif armed == 1 and (end > mintime) and (pos > playtime*end/100):
          armed = 0 # Disarm until the next song
          listened(getsong(unicode(currentsong["file"], enc)))
          songid = (currentsong["id"])

    except KeyError:
      pass

    time.sleep(delay)
    delay = min((delay*1.5, maxdelay))

# vim: tw=70 ts=2 sw=2
