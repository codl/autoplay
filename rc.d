#!/bin/bash

# general config
. /etc/rc.conf
. /etc/rc.d/functions

case "$1" in
    start)
  su codl -c "/home/codl/bin/autoplay"
	if [ $? -gt 0 ]; then
		stat_fail
	else
		stat_done
	fi
        ;;
    stop)
	stat_busy "Stopping Hardware Abstraction Layer"
  for i in $(ps -Ao pid,args | grep autoplay | cut -d' ' -f1); do kill $i; done
	stat_done
	;;
    restart)
        $0 stop
	sleep 1
        $0 start
        ;;
    *)
        echo "usage: $0 {start|stop|restart}"
	;;
esac
exit 0
