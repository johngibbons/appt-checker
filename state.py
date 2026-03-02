from __future__ import annotations

import json
import os
import tempfile
from datetime import date

import config


def load_earliest_date() -> date | None:
    try:
        with open(config.STATE_FILE) as f:
            data = json.load(f)
        return date.fromisoformat(data["earliest_date"])
    except (FileNotFoundError, KeyError, ValueError):
        return None


def save_earliest_date(d: date) -> None:
    data = {"earliest_date": d.isoformat()}
    dir_name = os.path.dirname(config.STATE_FILE)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, config.STATE_FILE)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
