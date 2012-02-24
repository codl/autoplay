autoplay
========

a daemon that keeps your [MPD][] playlist filled with the music you actually listen to.

[MPD]: http://mpd.wikia.com (Music Player Daemon)

Dependencies
------------

* [python 2.x][python]
* [python-mpd][pympd]

[python]: http://python.org/
[pympd]: http://jatreuman.indefero.net/p/python-mpd/

Usage
-----

```
autoplay.py [command]
command can be one of :
  radio [on|off|toggle]     : switches between radio mode and stat collection only
  trigger [number]          : sets how many tracks must be in the playlist at all times
  info [filename]           : gives some info on the specified track, or the currently playing track

  start
  kill
  loglevel [debug|notice|warning|error]
  help
  version
```

To have autoplay start automatically, you may add `autoplay.py start > /dev/null &` to your `.profile` or `.bash_profile`.

Installation
------------

Make sure you have all dependencies installed, then put `autoplay.py` anywhere in your `$PATH`.

Configuration
-------------

Autoplay will connect to the server according to environment variables `MPD_HOST` and `MPD_PORT`.
The defaults are :

```sh
MPD_HOST="127.0.0.1"
MPD_PORT="6600"
```

A password can be used by using the syntax `MPD_HOST="password@host"`.

If the variable `MPD_MUSIC_DIR` is set, Autoplay will use it to flag symlinks or hardlinks as duplicates.

How it works
------------

Autoplay gives each song a *karma* rating based on how often it adds that song, and how often that song is played.

Usually, bad songs have karma under 0.25, *meh* songs have karma between 0.25 and 0.60, and good songs are over 0.60. A song that is often added by the user to the playlist will have a karma over 1.

When a song is played, there is a *cooldown time* (default 12h) during which autoplay cannot add it. This way, the same songs cannot be spammed over and over.

Notice for v1.X users
---------------------

The database has moved. It was `your/music/dir/.autodb`, it is now `$XDG_DATA_HOME/autoplay/db.sqlite` (usually `~/.local/share/autoplay/db.sqlite`). Move your database to the new location if you want to keep your stats.
