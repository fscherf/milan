#!/bin/bash
# usage: pass-fds.sh $FD $FIFO_PATH -- $COMMAND
# example: pass_fds.sh 3 /tmp/debugging-pipe-in 4 /tmp-debugging-pipe-out -- /usr/bin/chromium --debugging-pipe

set -e

while true; do
    if [ "$1" == "--" ]; then
        shift

        break
    fi

    eval "exec $1<>$2"

    shift
    shift
done

exec $@
