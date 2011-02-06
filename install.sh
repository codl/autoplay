#!/bin/bash

if [[ $UID -ne 0 ]]
then
  echo "This must be run as root"
  echo "sudo $0 or su -c '$0'"
  exit
fi

[[ -e /etc/rc.d/autoplay ]] && /etc/rc.d/autoplay stop
[[ -e /etc/init.d/autoplay ]] && /etc/init.d/autoplay stop

cp autoplay.py /tmp/autoplay
cp rc /tmp/rc

printf "Where to install?\n(Default : /usr/bin) > "
read BIN
[[ $BIN != "" ]] && [[ -d $BIN ]] && sed -i "s|/usr/bin|$BIN|" /tmp/rc
[[ $BIN == "" ]] || [[ ! -d $BIN ]] && BIN="/usr/bin"

printf "What user should run it?\n(Default : mpd) > "
read USER
[[ $USER != "" ]] && sed -i "s/mpd/$USER/" /tmp/rc

sed -i "s|~|$(su $USER -c 'printf $HOME')|" /tmp/rc

if [[ $(sed -n "/localhost/p" /tmp/autoplay) != '' ]]; then
  printf "MPD server?\n(Default : localhost) > "
  read SERVER
  [[ $SERVER != "" ]] && sed -i "s/localhost/$SERVER/" /tmp/autoplay
fi

if [[ $(sed -n "/port.*6600/p" /tmp/autoplay) != '' ]]; then
  printf "MPD port?\n(Default : 6600) > "
  read PORT
  [[ $PORT != "" ]] && sed -i "/port/s/6600/$PORT/" /tmp/autoplay
fi

if [[ $(sed -n "/pass.*False.*#/p" /tmp/autoplay) != '' ]]; then
  printf "MPD password?\n(Default : None) > "
  read PASS
  [[ $PASS != "" ]] && sed -i "/pass/s/False/$PASS/1" /tmp/autoplay
fi

if [[ $(sed -n "/\~\/music/p" /tmp/autoplay) != '' ]]; then
  printf "Where is your music located?\n(Default : ~/music) > "
  read DB
  [[ $DB != "" ]] && sed -i "s|~/music|$DB|" /tmp/autoplay
fi

mv /tmp/autoplay $BIN/autoplay

printf "Where is your rc.d or init.d directory?\n(Default : /etc/rc.d, /etc/init.d, or none) > "
read DOTD
[[ $DOTD == "" ]] && [[ -d /etc/rc.d ]] && DOTD="/etc/rc.d"
[[ $DOTD == "" ]] && [[ -d /etc/init.d ]] && DOTD="/etc/init.d"
[[ $DOTD == "" ]] || [[ ! -d $DOTD ]] && printf "Could not find rc.d or init.d directory. rc script will not be installed\n" && DOTD=""

echo "Done! Autoplay has been installed to $BIN/autoplay :)"
echo "You might want to run 'autoplay -u' before running autoplay if this is your first time using autoplay to build the database"

if [[ $DOTD != "" ]]; then
  mv /tmp/rc $DOTD/autoplay
  printf "Do you want to start autoplay right now?\ny/N > "
  read
  [[ $REPLY == "y" ]] || [[ $REPLY == "yes" ]] || [[ $REPLY == "Y" ]] || [[ $REPLY == "Yes" ]] || [[ $REPLY == "YES" ]] && $DOTD/autoplay start
fi

