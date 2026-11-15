"""Проверка HTTP API. По умолчанию запросы идут через Nginx."""
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

base = os.getenv("BASE_URL", "http://127.0.0.1:8080")
notes = os.getenv("NOTES_URL", base)
labels = os.getenv("LABELS_URL", base)


def call(base_url, method, path, status, data=None):
    body = json.dumps(data).encode() if data is not None else None
    request = Request(base_url + path, data=body, method=method,
                      headers={"Content-Type": "application/json"})
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        assert response.code == status, (method, path, response.code, status)
        raw = response.read()
        return json.loads(raw) if raw else None


def check():
    assert "Учёба" in call(labels, "GET", "/api/labels", 200)
    print("Справочник меток: OK")
    call(notes, "POST", "/api/notes", 400, {"title": "", "body": "", "label": "Учёба"})
    print("Пустой заголовок: HTTP 400")
    data = {"title": "Проверка", "body": "Первая версия", "label": "Учёба"}
    note = call(notes, "POST", "/api/notes", 201, data)
    url = "/api/notes/" + str(note["id"])
    try:
        assert note in call(notes, "GET", "/api/notes", 200)
        data["body"] = "Новая версия"
        updated = call(notes, "PUT", url, 200, data)
        assert updated["body"] == "Новая версия"
        assert updated in call(notes, "GET", "/api/notes", 200)
        print("Создание, чтение и редактирование: OK")
    finally:
        call(notes, "DELETE", url, 204)
    assert all(row["id"] != note["id"] for row in call(notes, "GET", "/api/notes", 200))
    call(notes, "DELETE", url, 404)
    print("Удаление и повторное удаление: HTTP 204, затем HTTP 404")


if __name__ == "__main__":
    check()
