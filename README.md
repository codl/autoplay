autoplay
========

... is a simple daemon for auto-filling your [MPD][] playlist with the music you like the most.

[MPD]: http://mpd.wikia.com (Music Player Daemon)

Dependencies
------------

* [python][py]
* [python-mpd][pympd]
* [pysqlite][]

[py]: http://python.org/
[pympd]: http://jatreuman.indefero.net/p/python-mpd/
[pysqlite]: http://code.google.com/p/pysqlite/

Usage
-----

Just start autoplay either by calling autoplay.py directly or using the rc.d script. It will start building statistics and continuously fill your playlist.

How it works
------------

Autoplay gives each song a *karma* rating based on how often it adds that song, and how often that song is played.

Usually, bad songs have karma under 0.25, *meh* songs have karma between 0.25 and 0.60, and good songs are over 0.60. A song that is often added by the user to the playlist will have a karma over 1.

When a song is played, there is a *cooldown time* (default 6h) when autoplay cannot add it. This way, the same songs cannot be spammed over and over.
