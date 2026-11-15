import os
import sqlite3
from contextlib import closing
from pathlib import Path

from aiohttp import web

DB = Path(os.getenv("NOTES_DB", "data/notes.db"))
DB.parent.mkdir(parents=True, exist_ok=True)

with closing(sqlite3.connect(DB)) as conn:
    conn.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        label TEXT NOT NULL
    )""")
    conn.commit()

routes = web.RouteTableDef()


@routes.get("/health")
async def health(request):
    with closing(sqlite3.connect(DB)) as conn:
        conn.execute("SELECT id FROM notes LIMIT 1").fetchone()
    return web.json_response({"status": "ok"})


@routes.get("/api/notes")
async def list_notes(request):
    with closing(sqlite3.connect(DB)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM notes ORDER BY id DESC").fetchall()
    return web.json_response([dict(row) for row in rows])


@routes.post("/api/notes")
@routes.put(r"/api/notes/{id:[0-9]{1,18}}")
async def save_note(request):
    try:
        data = await request.json()
        title, body, label = [data[key].strip() for key in ("title", "body", "label")]
    except (ValueError, TypeError, KeyError, AttributeError):
        return web.json_response({"error": "Нужны строки title, body и label"}, status=400)

    if not (1 <= len(title) <= 80 and len(body) <= 2000 and 1 <= len(label) <= 32):
        return web.json_response({"error": "Проверьте длину полей"}, status=400)

    with closing(sqlite3.connect(DB)) as conn, conn:
        if request.method == "POST":
            result = conn.execute(
                "INSERT INTO notes (title, body, label) VALUES (?, ?, ?)", (title, body, label)
            )
            note_id = result.lastrowid
        else:
            note_id = int(request.match_info["id"])
            result = conn.execute(
                "UPDATE notes SET title=?, body=?, label=? WHERE id=?",
                (title, body, label, note_id),
            )
            if result.rowcount == 0:
                return web.json_response({"error": "Заметка не найдена"}, status=404)

    return web.json_response(
        {"id": note_id, "title": title, "body": body, "label": label},
        status=201 if request.method == "POST" else 200,
    )


@routes.delete(r"/api/notes/{id:[0-9]{1,18}}")
async def delete_note(request):
    with closing(sqlite3.connect(DB)) as conn, conn:
        result = conn.execute("DELETE FROM notes WHERE id=?", (int(request.match_info["id"]),))
        if result.rowcount == 0:
            return web.json_response({"error": "Заметка не найдена"}, status=404)
    return web.Response(status=204)


app = web.Application(client_max_size=32 * 1024)
app.add_routes(routes)

if __name__ == "__main__":
    web.run_app(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))
