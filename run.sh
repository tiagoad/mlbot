#!/bin/bash

EXIT=0
trap 'int' SIGHUP SIGINT SIGTERM

# waits for python to exit properly before quitting
function int {
    if kill -0 $PID >& /dev/null; then
        echo "Waiting for PID $PID ($(ps -p $PID -o command=))"
        wait $PID;
    fi

    exit
}

while :
do
    python bot.py &
    PID=$!
    wait

    sleep $RUN_INTERVAL
done
