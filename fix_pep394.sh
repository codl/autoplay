#!/bin/bash

if [[ ! -f /usr/bin/python2 ]]; then
    if [[ $(python -V 2>&1 | sed "s/^Python \([23]\).*$/\1/") == 2 ]]; then
        echo "Your distro doesn't respect PEP 394. Fixing..."
        sed "s/python2/python/g" < autoplay.py > autoplay.py_
        mv autoplay.py_ autoplay.py
    else
        echo "Couldn't find python 2.x in any of the standard places."
        exit 1
    fi
else
    echo "Your distro is sane, nothing to do here."
fi
