#!/usr/bin/env python3

'''
Keeps your MPD playlist filled with music you like

Dependencies : python-mpd2
'''

import os
import mpd
import random
import sqlite3
import time
import io
import sys
import socket

## Config
playtime = 70 # Percentage of a song that must be played before
              #  play count is incremented
mintime = 25 # Minimum length of a track for it
             #  to be considered a song (in seconds)
flood_delay = 12*60 # Minutes to wait before adding the same song again
tries = 10 # Retry connecting this many times
## /Config

version = "2.0 DEV"
helpstring = """Syntax : """ + sys.argv[0] + """ [command]
command can be one of :
  radio [on|off|toggle]
  trigger [number]
  info [path]

  start
  stop (synonym: kill)
  loglevel [debug|notice|warning|error]
  help
  version"""

def log(msg, stdout=False):
  """Logs to file, and optionally to stdout. Obvious enough"""
  alllevels = "DINWE" # Debug, Info, Notice, Warning, Error
  loglevels = alllevels[alllevels.find(logLevel):]
  if stdout:
    print(msg[2:])
  if msg[0] in loglevels:
    logio.write(msg+"\n")

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
  cursor.execute("SELECT file, listened, added FROM songs "
      "WHERE karma>? AND time < ? "
      "AND NOT duplicate ORDER BY random() LIMIT 1;",
      (rand, int(time.time()-(60*(flood_delay-trigger*3)))))
  songdata = cursor.fetchone()
  if not songdata:
    updateone()
    addsong()
  else:
    newkarma = karma(songdata[1], songdata[2]+1)
    cursor.execute(
        "UPDATE songs SET added=?, karma=?, time=? WHERE file=?",
        (songdata[2]+1, newkarma, int(time.time()), songdata[0],)
        )
    cursor.execute(
        "SELECT inode, dev FROM songs WHERE file=?;",
        (songdata[0],)
        )
    one = cursor.fetchone()
    if one and one[0]:
      cursor.execute(
          """UPDATE SONGS SET added=?, karma=?, time=? WHERE inode=?
          AND dev=?""", (songdata[2]+1, newkarma, int(time.time()),
            one[0], one[1])
          )
    db.commit()
    try:
      client.add(songdata[0])
      log("I Added " + songdata[0])
      log("D A:" + str(songdata[2]+1) + ", K:" +
          str(newkarma))
    except mpd.CommandError:
      log("W Couldn't add " + songdata[0])
      update(songdata[0])
      addsong()

def karma(listened, added):
  if listened == 0: listened = 0.1
  if added == 0: added = 0.1
  return float(listened)/added

def listened(file):
  update(file);
  try:
    cursor.execute("SELECT listened, added FROM songs WHERE file = ?",
        (file,))
    songdata = cursor.fetchone()
    newkarma = karma(songdata[0]+1, songdata[1])
    cursor.execute(
        "UPDATE songs SET listened=?, karma=?, time=? WHERE file=?",
        (songdata[0]+1, newkarma, int(time.time()), file)
        )
    cursor.execute(
        "SELECT inode, dev FROM songs WHERE file=?;",
        (file,)
        )
    one = cursor.fetchone()
    if one and one[0]:
      cursor.execute(
          """UPDATE SONGS SET listened=?, karma=?, time=? WHERE inode=?
          AND dev=?""", (songdata[0]+1, newkarma, int(time.time()),
            one[0], one[1])
          )
    db.commit()
    log("I Listened to " + file)
    log("D L:" + str(songdata[0]+1) + ", K:" +str(newkarma))
  except (KeyError, TypeError): # on songdata[n]
    pass

allsongs = []
def updateone():
  if allsongs == []:
    cursor.execute("VACUUM;")
    for song in client.list("file"):
      allsongs.append(song)
    for song in cursor.execute("SELECT file FROM songs;"):
      allsongs.append(song[0])
    random.shuffle(allsongs)

  song = allsongs.pop()
  update(song)

def update(song):
  # Check if the file is in mpd
  records = client.search("filename", song)
  if not any(r['file'] == song for r in records):
    log("N Update : Removing " + song)
    cursor.execute("delete from songs where file=?", (song,))
    db.commit()
    return

  inode = dev = None
  duplicate = False
  listened, added, karma = 0, 0, 5
  if musicdir:
    # Check for duplicate in FS
    try:
      s = os.stat(musicdir + "/" + song)
      inode = s.st_ino
      dev = s.st_dev
      cursor.execute("SELECT listened, added, karma FROM songs WHERE file!=? AND inode=?" +
          "AND dev=? AND NOT duplicate;", (song, inode, dev))
      one = cursor.fetchone();
      if one:
        duplicate=True
        listened, added, karma = one
        cursor.execute("""UPDATE songs SET listened=?, added=?, karma=?,
          inode=?, dev=?, duplicate=? WHERE file=?""",
            (listened, added, karma, inode, dev, duplicate, song))
      else:
        cursor.execute("""UPDATE songs SET inode=?, dev=?, duplicate=? WHERE file=?""",
            (inode, dev, duplicate, song))
    except OSError:
      log("E Couldn't stat " + musicdir + "/" + song)
      pass

  # Check if the file is in DB
  cursor.execute("SELECT 1 FROM songs WHERE file=?", (song,))
  if cursor.fetchone() == None:
    log("N Update : Adding " + song)
    cursor.execute("INSERT INTO songs"+
        "(file, listened, added, karma, time, inode, dev, duplicate)"+
        "VALUES (?, ?, ?, ?, 0, ?, ?, ?);",
        (song, listened, added, karma, inode, dev, duplicate))
    db.commit()


def getSetting(name, default=None):
  cursor.execute("""SELECT value FROM setting
      WHERE name = ?;""", (name,))
  one = cursor.fetchone()
  if not one and default:
    setSetting(name, default)
    return default
  if not one: return None
  return one[0]

def setSetting(name, val):
  val = str(val)
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
        file text not null,
        listened int not null default 0,
        added int not null default 0,
        karma real not null default 5,
        time int not null default 0,
        inode int,
        dev int,
        duplicate boolean not null default 0
        );""")
    db.commit()
    dbversion = getSetting("dbversion")
    cursor.execute("""SELECT 1 FROM songs LIMIT 1;""")
    if cursor.fetchone() and not dbversion: # old db
      setSetting("dbversion", "1")
    elif not dbversion:
      setSetting("dbversion", "3")
    else:
      if int(dbversion) < 2:
        cursor.execute("""ALTER TABLE songs ADD COLUMN inode int;""")
        cursor.execute("""ALTER TABLE songs ADD COLUMN dev int;""")
        setSetting("dbversion", "2")
      if int(dbversion) < 3:
        cursor.execute("""ALTER TABLE songs ADD COLUMN duplicate boolean
            not null default 0;""")
        setSetting("dbversion", "3")
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

def pprintSong(file=None):
  try:
    if not file:
      song = client.currentsong()
    else:
      song = client.find("file", file)[0]
    cursor.execute("""SELECT listened, added, karma FROM songs
      WHERE file = ?""", (song['file'],))
    one = cursor.fetchone()
    if not one:
      return "\n"
    prettysong = song['file']
    try:
      prettysong = song['title']
      prettysong = song['artist'] + " - " + prettysong
    except (KeyError, TypeError): pass
    return prettysong + """
Listened : """ + str(one[0]) + """
Added    : """ + str(one[1]) + """
Karma    : """ + str(one[2]) + "\n"
  except (IndexError, KeyError, mpd.ConnectionError):
    return "\n";

def sockAccept():
  global client, db, cursor, s
  global trigger, radioMode, logLevel
  global allsongs

  try: #Socket error
    c, _ = s.accept()
    c.settimeout(1)
    comm = b""
    try:
      while comm[-1:] != b"\n":
        comm += c.recv(1024)
    except socket.error:
      comm=b""
    c.settimeout(0)
    comm = comm[:-1]
    if len(comm) != 0:
      if comm == b"kill" or comm == b"stop":
        c.send(b"Shutting down server...\n")
        c.shutdown(socket.SHUT_RD)
        c.close()
        shutdown()
        exit(0)
      elif comm[:5] == b"radio":
        if comm[6:] in (b"off", b"no", b"stop"): radioMode = False
        elif comm[6:] in (b"on", b"yes", b"start"): radioMode = True
        elif comm[6:] == b"toggle": radioMode = not radioMode
        elif comm[5:6] == b" ": c.send(b"Syntax: autoplay radio [on|off|toggle]\n")
        c.send(radioStatus().encode())
        setSetting("radioMode", str(radioMode))
      elif comm[:7] == b"trigger":
        try:
          trigger = int(comm[8:])
          setSetting("trigger", str(trigger))
        except ValueError:
          if comm[7:8] == b" ":
            c.send(b"\"" + comm[8:] + b"\" is not a valid number\n")
        c.send(triggerStatus().encode())

      elif comm[:8] == b"loglevel":
        if comm[9:].lower() in (b"d", b"debug"): logLevel = "D"
        elif comm[9:].lower() in (b"n", b"notice"): logLevel = "N"
        elif comm[9:].lower() in (b"w", b"warning"): logLevel = "W"
        elif comm[9:].lower() in (b"e", b"error"): logLevel = "E"
        elif comm[8:9] == b" ":
          c.send(b"Syntax: autoplay loglevel [debug|notice|warning|error]\n")
        c.send(b"Log level : " + logLevel.encode() + b"\n")
        setSetting("logLevel", logLevel)

      elif comm[:4] == b"info":
        if comm[4:] != b"": c.send(pprintSong(comm[5:].decode()).encode())
        else: c.send(pprintSong().encode())

      elif comm[:6] == b"update":
        if comm[7:] == b"all":
          c.send(b"This may be *very* long, depending on the size of your"
              + b" library.\n")
          allsongs = []
          updateone()
          c.send(("%s songs to update\n\n" % (len(allsongs) + 1,))
            .encode())
          while allsongs != []:
            if len(allsongs) % 200 == 0:
              c.send(("%s remaining...\n" % (len(allsongs),))
                .encode())
            updateone()
          c.send(b"Done")
        else:
          update(comm[7:].decode())

      elif comm in (b"help",b"-h",b"--help"):
        c.send(helpstring.encode() + b"\n\n")
      elif comm in (b"version", b"-V"):
        c.send(b"Autoplay v" + version.encode() + b"\n")
      else:
        log("W Unknown command : " + comm.decode())
        c.send(b"Unknown command : " + comm + b"\n")
        c.send(helpstring.encode() + b"\n")
    else:
      c.send(radioStatus().encode())
      if radioMode: c.send(triggerStatus().encode())
    c.shutdown(socket.SHUT_RDWR)
    c.close()
    return True;
  except socket.error:
    return False;

def serve():
  global client, db, cursor, s
  global trigger, radioMode, logLevel
  global allsongs

  s = socket.socket(socket.AF_UNIX)
  s.bind(datahome + "/socket")
  s.settimeout(.3)
  s.listen(2)

  db = sqlite3.connect(datahome+"/db.sqlite")
  cursor = db.cursor()
  initDB()

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
      if sockAccept():
        lastUpdate = lastMpd = time.time()
        next

      try: #MPD or socket error
        clock = time.time()
        if clock - lastUpdate >= 5:
          lastUpdate = clock
          updateone()
        if clock - lastMpd >= .6:
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
              listened(currentsong["file"])
              songid = (currentsong["id"])

      except (KeyError, TypeError):
        pass

      except (socket.error, mpd.ConnectionError):
        log("W Connection to MPD lost")
        client.disconnect()
        connect()

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

  s = socket.socket(socket.AF_UNIX)
  try:
    s.connect(datahome + "/socket")
  except socket.error:
    try:
      s = getServSock()
    except RuntimeError: # recursion
      log("E Couldn't connect to socket", True)
      exit(1)
  return s


logLevel = "D"

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


logio = io.open(datahome + "/log", "at", buffering=1)


if __name__ == "__main__":
  silent = False
  s = getServSock()
  try:
    if len(sys.argv) <= 1 or sys.argv[1] != "start":
      s.sendall(b" ".join(map(lambda s: s.encode(), sys.argv[1:])) + b"\n")

      data = s.recv(1024)
      while data != b"":
        print(data.decode(), end="")
        data = s.recv(1024)

  except KeyboardInterrupt:
    pass

  s.shutdown(socket.SHUT_RDWR)
  s.close()

# vim: tw=70 ts=2 sw=2
