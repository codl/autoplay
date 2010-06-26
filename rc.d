#!/bin/bash

# general config
. /etc/rc.conf
. /etc/rc.d/functions

case "$1" in
    start)
	stat_busy "Starting Autoplay"
  su codl -c "/home/codl/bin/autoplay" > /dev/null &
  stat_done
        ;;
    stop)
	stat_busy "Stopping Autoplay"
  for i in $(ps -Ao pid,args | grep autoplay | grep python | cut -d' ' -f1); do kill $i; done
	stat_done
	;;
    restart)
        $0 stop
        $0 start
        ;;
    *)
        echo "usage: $0 {start|stop|restart}"
	;;
esac
exit 0
