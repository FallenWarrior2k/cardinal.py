#!/usr/bin/env python3

import json
import sys
from pathlib import Path

from alembic.config import main as alembic

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) >= 2 else "config.json"

    with open(path) as f:
        config = json.load(f)

    url = config["db"]["connect_string"]

    alembic_opts = [
        "-c",
        str(
            Path(__file__).resolve().parent
            / "src"
            / "cardinal"
            / "db"
            / "migrations"
            / "alembic.ini"
        ),
        "-x",
        "url=" + url,
        "upgrade",
        "head",
    ]
    alembic(alembic_opts)
