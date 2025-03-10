#!/bin/bash
#
# autoclick.sh
# Copyright (C) 2024 fred <github-fred@hidzz.com>
#
# Distributed under terms of the BSD 3-Clause license.
#
# Don't forget to install xdotool

# On ubuntu based os run the following commands:
# apt update && apt upgrade -y
# apt install xdotool
#


find_wsjtx() {
    local -a wids
    local windowid=0
    while [[ $windowid == 0 ]]; do
        wids=$(xdotool search --name "WSJT-X")
        for id in $wids; do
            # echo "${id} = $(xdotool getwindowname ${id})"
            xdotool getwindowname ${id} | grep -q "^WSJT-X.*QSO$"
            if [[ $? == 0 ]]; then
                windowid=${id}
                break
            fi
        done
        [[ ${windowid} == 0 ]] &&  sleep 15
    done
    echo $windowid
}

windowid=$(find_wsjtx)
echo "Logging window ID: ${windowid}"

while true; do
    while xdotool windowactivate ${windowid} 2>&1 | grep -q "failed"; do
        sleep 2
    done
    sleep .8
    xdotool key Return
    echo "Key pressed on ${windowid}"
    sleep 10
done
