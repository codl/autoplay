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

mv /tmp/autoplay $BIN/autoplay

printf "Where is your rc.d or init.d directory?\n(Default : /etc/rc.d, /etc/init.d, or none) > "
read DOTD
[[ $DOTD == "" ]] && [[ -d /etc/rc.d ]] && DOTD="/etc/rc.d"
[[ $DOTD == "" ]] && [[ -d /etc/init.d ]] && DOTD="/etc/init.d"
[[ $DOTD == "" ]] || [[ ! -d $DOTD ]] && printf "Could not find rc.d or init.d directory. rc script will not be installed\n" && DOTD=""

echo "Done! Autoplay has been installed to $BIN/autoplay :)"
echo "It will connect to the server specified in \$MPD_HOST and \$MPD_PORT, or localhost:6600 by default"

if [[ $DOTD != "" ]]; then
  mv /tmp/rc $DOTD/autoplay
  printf "Do you want to start autoplay right now?\ny/N > "
  read
  [[ $REPLY == "y" ]] || [[ $REPLY == "yes" ]] || [[ $REPLY == "Y" ]] || [[ $REPLY == "Yes" ]] || [[ $REPLY == "YES" ]] && $DOTD/autoplay start
fi

