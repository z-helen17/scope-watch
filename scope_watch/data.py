"""Load the matter: engagement terms, client requests and time entries."""
import csv
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def load_engagement(path=DATA / "engagement.json"):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_requests(path=DATA / "requests.json"):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_timesheets(path=DATA / "timesheets.csv"):
    rows = []
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            row["hours"] = float(row["hours"])
            rows.append(row)
    return rows
