import json
import os
from pathlib import Path

from aiohttp import web

labels = json.loads(Path(__file__).with_name("labels.json").read_text(encoding="utf-8"))


async def list_labels(request):
    return web.json_response(labels)


async def health(request):
    return web.json_response({"status": "ok"})


app = web.Application()
app.add_routes([web.get("/api/labels", list_labels), web.get("/health", health)])

if __name__ == "__main__":
    web.run_app(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))
