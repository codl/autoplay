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
import socket
import signal

## Config
playtime = 70 # Percentage of a song that must be played before
              #  play count is incremented
mintime = 25 # Minimum length of a track for it
             #  to be considered a song (in seconds)
flood_delay = 12*60 # Minutes to wait before adding the same song again
tries = 10 # Retry connecting this many times
## /Config

version = "2.0 DEV"
helpstring = """Syntax : autoplay [command]
command can be one of :
  radio [on|off|toggle]
  trigger [number]

  kill
  loglevel [debug|notice|warning|error]
  help
  version"""

enc = sys.getfilesystemencoding()
#enc = "UTF-8"

## Functions
def log(msg, stdout=False):
  """Logs to file, and optionally to stdout. Obvious enough"""
  alllevels = "DNWE" # Debug, Notice, Warning, Error
  loglevels = alllevels[alllevels.find(logLevel):]
  if stdout:
    print msg[2:]
  if msg[0] in loglevels:
    logio.write(unicode(msg, enc)+"\n")

def connect(i=1):
  log("N Connecting...")
  if i == tries:
    log("E Could not connect to server D:", stdout=True)
    exit(1)
  try:
    client.connect(host, port)
  except socket.error:
    log("N Try n°"+str(i)+" failed")
    time.sleep(i*3)
    connect(i+1)
    return
  if password:
    try:
      log("D Using password")
      client.password(password)
    except mpd.CommandError:
      log("E Couldn't connect. Wrong password?", stdout=True)
      exit(2)
  log("N Connected")


def addsong():
  """Adds a semi-random song to the playlist"""
  rand = random.uniform(-0.5, 2)
  cursor.execute("select * from songs where karma>? and time < ?\
      ORDER BY random() LIMIT 1;",
      (rand, int(time.time()-(60*(flood_delay-trigger*3)))))
  data = cursor.fetchall()
  if data == []:
    updateone()
    addsong()
  else:
    songdata = data[0]
    newkarma = karma(songdata, 2)
    cursor.execute(
        "update songs set added=?, karma=?, time=? where file=?",
        (songdata[2]+1, newkarma, int(time.time()), songdata[0],)
        )
    db.commit()
    try:
      client.add(songdata[0].encode(enc))
      log("D Added " + songdata[0].encode(enc))
    except mpd.CommandError:
      update(songdata[0])
      addsong()

def getsong(songfile):
  """Retrieve song data from DB"""
  cursor.execute("select * from songs where file=?", (songfile,))
  data = cursor.fetchone()
  if data == None:
    update(songfile)
    data = (songfile, 0, 0, 5, 0)
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
  log("D Listened to " + songdata[0].encode(enc))
  db.commit()
## /Functions

allsongs = []
def updateone():
  if allsongs == []:
    for song in client.list("file"):
      allsongs.append(unicode(song, enc))
    for song in cursor.execute("select file from songs;"):
      allsongs.append(song[0])
    random.shuffle(allsongs)

  song = allsongs.pop()
  update(song)

def update(song):
  # Check if the file is in mpd
  records = client.search("filename", song.encode(enc))
  if not any(unicode(r['file'], enc) == song for r in records):
    log("N Update : Removing " + song.encode(enc))
    cursor.execute("delete from songs where file=?", (song,))
    db.commit()
    return

  inode = dev = None
  if musicdir:
    # Check for duplicate in FS
    try:
      s = os.stat(musicdir + "/" + song.encode(enc))
      inode = s.st_ino
      dev = s.st_dev
      cursor.execute("SELECT 1 FROM songs WHERE file!=? AND inode=?" +
          "AND dev=?", (song, inode, dev))
      if cursor.fetchone():
        log("D " + song.encode(enc) +
            " (Inode : " + str(inode) + ", Device : " + str(dev) +
            ") already exists in DB")
        cursor.execute("DELETE FROM songs WHERE file=?", (song,))
        return
      else:
        cursor.execute("UPDATE songs SET inode=?, dev=? WHERE file=?",
            (inode, dev, song))
    except OSError:
      pass

  # Check if the file is in DB
  cursor.execute("select * from songs where file=?", (song,))
  if cursor.fetchone() == None:
    log("N Update : Adding " + song.encode(enc))
    cursor.execute("INSERT INTO songs"+
        "(file, listened, added, karma, time, inode, dev)"+
        "VALUES (?, 0, 0, 5, 0, ?, ?);",
        (song, inode, dev))
    db.commit()
    return



def getSetting(name, default=None):
  cursor.execute("""SELECT value FROM setting
      WHERE name = ?;""", (name,))
  one = cursor.fetchone()
  if not one: return default
  return one[0]

def setSetting(name, val):
  if getSetting(name) == None:
    cursor.execute("""INSERT INTO setting (name, value)
      VALUES (?, ?);""", (name, val))
  else:
    cursor.execute("""UPDATE setting SET value = ?
      WHERE name = ?;""", (val, name))
  db.commit()

def initDB():
    cursor.execute("""CREATE TABLE IF NOT EXISTS setting(
        name text not null,
        value text
        );""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS songs(
        file text,
        listened int,
        added int,
        karma real,
        time int,
        inode int,
        dev int
        );""")
    db.commit()
    dbversion = getSetting("dbversion")
    cursor.execute("""SELECT 1 FROM songs LIMIT 1;""")
    if cursor.fetchone() and not dbversion: # old db
      setSetting("dbversion", "1")
    elif not dbversion:
      setSetting("dbversion", "2")
    elif int(dbversion) < 2:
      cursor.execute("""ALTER TABLE songs ADD COLUMN inode int;""");
      cursor.execute("""ALTER TABLE songs ADD COLUMN dev int;""");
      setSetting("dbversion", "2")
    db.commit()

def shutdown():
  s.shutdown(socket.SHUT_RDWR)
  s.close()
  os.unlink(datahome + "/socket")
  client.disconnect()
  os.unlink(datahome + "/pid")
  log("N Shutdown")

def triggerStatus():
  return "Trigger : " + str(trigger) + "\n"

def radioStatus():
  return "Radio mode : " +\
    ("Enabled" if radioMode else "Disabled") + "\n"

def serve():
  global client, db, cursor, s
  global trigger, radioMode, logLevel
  global allsongs

  s = socket.socket(socket.AF_UNIX)
  s.bind(datahome + "/socket")
  s.listen(2)
  s.setblocking(0)

  db = sqlite3.connect((datahome+"/db.sqlite").encode(enc))
  cursor = db.cursor()
  initDB()
  cursor.execute("VACUUM;")

  logLevel = getSetting("logLevel", "W")
  radioMode = getSetting("radioMode", "True") == "True"
  trigger = int(getSetting("trigger", 6))

  random.seed()
  client = mpd.MPDClient()
  connect()

  armed = True

  lastUpdate = 0
  lastMpd = time.time()

  log("D Music dir is located at " + str(musicdir))

  log("N Ready")

  while True:

    try: #KeyboardInterrupt
      try: #Socket error
        c, _ = s.accept()
        c.settimeout(0.2)
        comm = ""
        try:
          while True: comm += c.recv(1024)
        except socket.error:
          pass
        c.setblocking(1)
        if len(comm) != 0:
          if comm == "kill":
            c.send("Shutting down server...\n")
            c.shutdown(socket.SHUT_RD)
            c.close()
            shutdown()
            exit(0)
          elif comm[:5] == "radio":
            if comm[6:] in ("off", "no", "stop"): radioMode = False
            elif comm[6:] in ("on", "yes", "start"): radioMode = True
            elif comm[6:] == "toggle": radioMode = not radioMode
            elif comm[5:6] == " ": c.send("Syntax: autoplay radio [on|off|toggle]\n")
            c.send(radioStatus())
            setSetting("radioMode", str(radioMode))
          elif comm[:7] == "trigger":
            try:
              trigger = int(comm[8:])
              setSetting("trigger", str(trigger))
            except ValueError:
              if comm[7:8] == " ":
                c.send("\"" + comm[8:] + "\" is not a valid number")
            c.send(triggerStatus())

          elif comm[:8] == "loglevel":
            if comm[9:].lower() in ("d", "debug"): logLevel = "D"
            elif comm[9:].lower() in ("n", "notice"): logLevel = "N"
            elif comm[9:].lower() in ("w", "warning"): logLevel = "W"
            elif comm[9:].lower() in ("e", "error"): logLevel = "E"
            elif comm[9:].lower() in ("on", "yes", "start"): radioMode = True
            elif comm[8:9] == " ":
              c.send("Syntax: autoplay loglevel [debug|notice|warning|error]\n")
            c.send("Log level : " + logLevel + "\n")
            setSetting("logLevel", logLevel)

          elif comm[:6] == "update":
            if comm[7:] == "all":
              c.send("This may be *very* long, depending on the size of your"
                  + " library.\n")
              allsongs = []
              updateone()
              c.send(str(len(allsongs) + 1) + " songs to update\n\n" )
              while allsongs != []:
                if len(allsongs) % 200 == 0:
                  c.send(str(len(allsongs)) + " remaining...\n")
                updateone()
              c.send("Done")
            else:
              update(unicode(comm[7:],enc))

          elif comm in ("help","-h","--help"):
            c.send(helpstring + "\n\n")
          elif comm in ("version", "-V"):
            c.send("Autoplay v" + version + "\n")
          else:
            log("W Unknown command : " + comm)
            c.send("Unknown command : " + comm + "\n")
            c.send(helpstring + "\n")
        else:
          c.send(radioStatus())
          if radioMode: c.send(triggerStatus())
        c.shutdown(socket.SHUT_RD)
        c.close()
      except socket.error:
        pass

      try: #MPD or socket error
        clock = time.time()
        if clock - lastUpdate >= 5:
          lastUpdate = clock
          updateone()
        if clock - lastMpd >= .5:
          lastMpd = clock
          if radioMode:
            if client.status()["consume"] == "0":
              cursongid = client.status()["songid"]
              for song in client.playlistid():
                if song["id"] == cursongid:
                  neededlength = int(song["pos"]) + trigger
            else:
              neededlength = trigger
            if len(client.playlist()) < neededlength:
              addsong()
              lastMpd = 0

          if client.status()['state'] == "play":
            times = client.status()['time'].split(":")
            pos = int(times[0])
            end = int(times[1])
            currentsong = client.currentsong()
            if not armed and "id" in currentsong and not songid == currentsong["id"]:
              armed = True
            elif armed and (end > mintime) and (pos > playtime*end/100):
              armed = False # Disarm until the next song
              listened(getsong(unicode(currentsong["file"], enc)))
              songid = (currentsong["id"])

      except KeyError:
        pass

      except (socket.error, mpd.ConnectionError):
        log("W Connection to MPD lost")
        client.disconnect()
        connect()

      time.sleep(0.2)

    except KeyboardInterrupt:
      s.shutdown(socket.SHUT_RDWR)


def getServSock():
  try:
    pidf = open(datahome + "/pid") #IOError
    pid = pidf.read()
    pidf.close()
    os.kill(int(pid), 0) #OSError on kill, ValueError on int
  except (IOError, OSError, ValueError):
    print("Starting server...")
    try:
      os.unlink(datahome + "/socket")
    except OSError:
      pass
    pid = os.fork()
    if pid == 0:
      serve()
    pidf = open(datahome + "/pid", "w")
    pidf.write(str(pid))
    pidf.close()
    time.sleep(1)

  s = socket.socket(socket.AF_UNIX)
  s.connect(datahome + "/socket")
  return s



datahome = (os.getenv("XDG_DATA_HOME") or os.getenv("HOME") +
            "/.local/share") + "/autoplay"
if not os.access(datahome, os.W_OK):
  try:
    os.makedirs(datahome)
  except os.error:
    log("E Couldn't access nor create" + datahome + ", quitting", True)
    exit(2)

password = None

host = os.getenv("MPD_HOST", "127.0.0.1")
atloc = host.find("@")
if(atloc != -1):
  password = host[:atloc]
  host = host[atloc+1:]

port = os.getenv("MPD_PORT", "6600")
musicdir = os.getenv("MPD_MUSIC_DIR") or os.getenv("mpd_music_dir")


logio = io.open(datahome + "/log", "at", buffering=1, encoding=enc)



s = getServSock()
if len(sys.argv) > 1:
  s.send(" ".join(sys.argv[1:]))

data = s.recv(1024)
while data != "":
  print data,
  data = s.recv(1024)


s.shutdown(socket.SHUT_RDWR)

# vim: tw=70 ts=2 sw=2
