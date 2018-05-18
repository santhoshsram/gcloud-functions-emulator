#!/bin/bash

functions start --bindHost 0.0.0.0 --restPort 8008 --supervisorPort 8010 > /dev/null
functions status | grep RUNNING > /dev/null
until [ $? -ne 0 ]; do
        echo "functions emulator is running"
        sleep 7
        functions status | grep RUNNING > /dev/null
done
echo "functions emulator is not running"
exit 1
