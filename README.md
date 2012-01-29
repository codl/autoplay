autoplay
========

a daemon that keeps your [MPD][] playlist filled with the music you actually listen to

[MPD]: http://mpd.wikia.com (Music Player Daemon)

Dependencies
------------

* [python 2.6][python]
* [python-mpd][pympd]

[python]: http://python.org/
[pympd]: http://jatreuman.indefero.net/p/python-mpd/

Usage
-----

```
autoplay [kill]
```

Configuration
-------------

Autoplay will connect to the server according to environment variables `MPD_HOST` and `MPD_PORT`.
The defaults are :

```sh
MPD_HOST="127.0.0.1"""
MPD_PORT="6600"
```

A password can be used by setting `MPD_HOST="password@host"`.

How it works
------------

Autoplay gives each song a *karma* rating based on how often it adds that song, and how often that song is played.

Usually, bad songs have karma under 0.25, *meh* songs have karma between 0.25 and 0.60, and good songs are over 0.60. A song that is often added by the user to the playlist will have a karma over 1.

When a song is played, there is a *cooldown time* (default 12h) when autoplay cannot add it. This way, the same songs cannot be spammed over and over.
