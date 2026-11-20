#!/bin/sh
# Запускать из корня проекта. Нужны Docker Compose и Python 3.
set -eu
lab() { docker compose -p notes-swarm-demo -f lab.compose.yaml "$@"; }
lab up -d --force-recreate
manager=$(lab ps -q manager)
worker=$(lab ps -q worker)
for node in "$manager" "$worker"; do
    ready=false
    for attempt in $(seq 1 60); do
        if docker exec "$node" docker info >/dev/null 2>&1; then ready=true; break; fi
        sleep 1
    done
    if [ "$ready" != true ]; then echo "Docker Engine не запустился"; exit 1; fi
done
# Стенд запускается заново; том с заметками при этом не удаляется.
state=$(docker exec "$manager" docker info --format '{{.Swarm.LocalNodeState}}')
if [ "$state" != inactive ]; then
    docker exec "$manager" docker stack rm noteslab >/dev/null
    removed=false
    for attempt in $(seq 1 60); do
        if ! docker exec "$manager" docker network inspect noteslab_app >/dev/null 2>&1; then
            removed=true
            break
        fi
        sleep 1
    done
    if [ "$removed" != true ]; then echo "Старая сеть ещё используется"; exit 1; fi
    docker exec "$worker" docker swarm leave >/dev/null
    docker exec "$manager" docker swarm leave --force >/dev/null
fi
manager_ip=$(docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$manager")
docker exec "$manager" docker swarm init --advertise-addr "$manager_ip" >/dev/null
token=$(docker exec "$manager" docker swarm join-token -q worker)
docker exec "$worker" docker swarm join --token "$token" "$manager_ip:2377"
manager_id=$(docker exec "$manager" docker info --format '{{.Swarm.NodeID}}')
docker exec "$manager" docker node update --label-add notes_data=true "$manager_id" >/dev/null
# Образы передаются обоим Engine; внешний реестр для двух локальных узлов не нужен.
for node in "$manager" "$worker"; do
    docker save notes-lab-web:local notes-lab-notes:local notes-lab-labels:local |
        docker exec -i "$node" docker load
done
docker exec -i "$manager" sh -c 'cat > /tmp/notes-stack.yaml' < stack.yaml
docker exec "$manager" docker stack deploy -c /tmp/notes-stack.yaml --resolve-image never noteslab
SWARM_CONTAINER="$manager" MIN_SWARM_NODES=2 python3 scripts/check_swarm.py
BASE_URL=http://127.0.0.1:18081 python3 scripts/check.py
BASE_URL=http://127.0.0.1:18082 python3 scripts/check.py
