#!/bin/sh

_term() {
    kill -TERM "$child"
}

trap _term SIGTERM  # Forward SIGTERM to bot

python3 upgrade_db.py

python3 run_cardinal.py &

child=$!
wait "$child"
