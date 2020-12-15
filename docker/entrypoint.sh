#!/bin/sh

python3 upgrade_db.py

exec python3 run_cardinal.py
