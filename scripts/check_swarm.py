"""Ждёт все пять задач и проверяет распределение по узлам Swarm."""
import json
import os
import subprocess
import time

command = ["docker"]
if os.getenv("SWARM_CONTAINER"):
    command += ["exec", os.environ["SWARM_CONTAINER"], "docker"]
stack = "noteslab"
expected = {"noteslab_web": 2, "noteslab_labels": 2, "noteslab_notes": 1}
minimum_nodes = int(os.getenv("MIN_SWARM_NODES", "1"))


def docker(*args):
    return subprocess.check_output(command + list(args), text=True).strip()


def ready():
    rows = docker("stack", "services", stack, "--format", "{{json .}}")
    services = [json.loads(row) for row in rows.splitlines() if row]
    replicas = {row["Name"]: row["Replicas"] for row in services}
    if replicas != {name: f"{count}/{count}" for name, count in expected.items()}:
        return False
    ids = docker("node", "ls", "-q").splitlines()
    nodes = json.loads(docker("node", "inspect", *ids))
    active = [n for n in nodes if n["Status"]["State"] == "ready"
              and n["Spec"]["Availability"] == "active"]
    if len(active) < minimum_nodes:
        return False
    tasks = docker("stack", "ps", stack, "--filter", "desired-state=running",
                   "--format", "{{json .}}")
    rows = [json.loads(row) for row in tasks.splitlines() if row]
    running = [row for row in rows if row["CurrentState"].startswith("Running ")]
    return len(running) == 5 and len({row["Node"] for row in running}) >= minimum_nodes


for attempt in range(90):
    if ready():
        print(docker("node", "ls"))
        print(docker("stack", "services", stack))
        print(docker("stack", "ps", "--no-trunc", stack))
        print("Swarm: все 5 задач работают; узлов с задачами не меньше", minimum_nodes)
        break
    time.sleep(2)
else:
    print(docker("node", "ls"))
    print(docker("stack", "services", stack))
    print(docker("stack", "ps", "--no-trunc", stack))
    raise SystemExit("Swarm не достиг ожидаемого состояния за 180 секунд")
