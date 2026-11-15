"""Запускается внутри notes; выводит готовую копию в stdout."""
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

with tempfile.TemporaryDirectory() as folder:
    copy = Path(folder) / "notes.db"
    with closing(sqlite3.connect(os.environ["NOTES_DB"])) as source:
        with closing(sqlite3.connect(copy)) as target:
            source.backup(target)
    sys.stdout.buffer.write(copy.read_bytes())
