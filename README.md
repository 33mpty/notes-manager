# Менеджер заметок

Курсовой проект по настройке и администрированию сервисного ПО. Два небольших HTTP-сервиса на Python и входной контейнер Nginx. Приложение рассчитано на локальный учебный стенд без учётных записей.

## Быстрый запуск

Открой Docker Desktop (либо запусти Docker Engine с Compose v2), распакуй архив и перейди в папку проекта. Выполни:

```sh
docker compose up --build -d --wait
docker compose ps
```

Открой http://127.0.0.1:8080. Добавь заметку, выбери метку, измени текст. Для автоматической проверки нужен Python 3, отдельные библиотеки ему не нужны:

```sh
python3 scripts/check.py
docker compose logs --tail=30 web notes labels
docker compose restart notes
```

После возврата notes в состояние healthy обнови страницу. Заметка останется в томе. Команда `docker compose down` удаляет контейнеры, но сохраняет данные. Не добавляй `-v`, если заметки нужны.

## Кто за что отвечает

- `web/` — страница, скрипт интерфейса и Nginx. Единственный опубликованный порт — 8080.
- `notes/` — список, создание, правка и удаление. База `/data/notes.db` в томе `notes_data`.
- `labels/` — справочник из `labels.json`. У него нет доступа к файлу SQLite.
- `compose.yaml` — локальный запуск; `stack.yaml` — запуск в Swarm.

Чтобы обновить список меток, измени `labels/labels.json` и выполни `docker compose up -d --build labels`. Старые заметки хранят название метки строкой. Они по-прежнему отображаются, даже если название убрали из справочника.

## Резервная копия и восстановление в Compose

```sh
mkdir -p backups
docker compose exec -T notes python backup.py > backups/notes.db.tmp &&
  mv backups/notes.db.tmp backups/notes.db
```

Копирование выполняет SQLite Backup API. Для восстановления на том же стенде, где контейнер notes уже создан, сначала сохрани актуальную копию отдельно. Затем останови веб-вход и сервис заметок, замени файл в томе, запусти сервисы:

```sh
docker compose stop web notes
docker compose run --rm -T --no-deps notes sh -c 'cat > /data/notes.new && mv /data/notes.new /data/notes.db' < backups/notes.db
docker compose up -d --wait
```

## Один узел Swarm

Эти команды рассчитаны на отдельный учебный Docker Engine. Если Swarm уже работает, не инициализируй его повторно. Сначала освободи порт 8080. Compose и Swarm используют разные тома.

```sh
docker compose down
docker compose build
docker swarm init
docker node update --label-add notes_data=true "$(docker info --format '{{.Swarm.NodeID}}')"
docker stack deploy -c stack.yaml --resolve-image never noteslab
docker stack services noteslab
docker stack ps noteslab
```

Когда все реплики запустятся, открой http://localhost:8080 и выполни `python3 scripts/check.py`. Для диагностики: `docker service logs noteslab_notes`. Пример масштабирования: `docker service scale noteslab_labels=3`. При повторном деплое `stack.yaml` вернёт две реплики. Остановка: `docker stack rm noteslab`.

Для нескольких узлов используй отдельные машины или ВМ с Docker Engine в одной доверенной сети. На менеджере получи команду добавления worker: `docker swarm join-token worker`. Метку `notes_data=true` устанавливай только на одном узле. Собери и опубликуй три образа в доступном узлам реестре командой `IMAGE_PREFIX=registry.example.org/student/notes IMAGE_TAG=v1 docker compose build --push` после входа в свой реестр. На менеджере укажи те же переменные при `docker stack deploy -c stack.yaml --with-registry-auth noteslab` (подставь адрес реального реестра). Локальный том SQLite не переедет на другой узел. Порт Swarm 8080 доступен через сеть кластера; ограничь доступ к стенду средствами хоста.

## CI/CD

После загрузки проекта в GitHub файл `.github/workflows/ci-cd.yml` автоматически собирает образы, запускает API-проверки в Compose и разворачивает временный Swarm из одного узла на runner. После успешных проверок в основной ветке доступен артефакт `notes-images-amd64`. Он содержит архив, который можно загрузить на совместимый хост командой `docker load -i notes-images.tar.gz`. Постоянный сервер в этой схеме обновляется вручную. Для ARM проще собрать образы на месте.

Если порт 8080 занят, задай другой: `WEB_PORT=18080 docker compose up --build -d --wait`. Открой http://127.0.0.1:18080 и запусти проверку так: `BASE_URL=http://127.0.0.1:18080 python3 scripts/check.py`.


## Два локальных узла Swarm

В проект включены `lab.compose.yaml`, `scripts/start_lab.sh` и `scripts/check_swarm.py`. Они запускают два отдельных Docker Engine в контейнерах `docker:27-dind` на одном компьютере. Это демонстрационный кластер, а не два физических сервера. Контейнерам Engine нужен режим `privileged`; внешние входы приложения привязаны к 127.0.0.1.

Перед первым запуском собери образы и выполни:

```sh
docker compose build
sh scripts/start_lab.sh
```

Внутри отдельной сети менеджер имеет адрес 172.30.77.2, рабочий узел — 172.30.77.3. Сеть 172.30.77.0/24 должна быть свободна. Постоянные адреса сохраняют соединение узлов при пересоздании контейнеров. Имена проекта и контейнеров: `notes-swarm-demo`, `notes-swarm-demo-manager-1`, `notes-swarm-demo-worker-1`.

Скрипт передаёт три образа обоим Engine, создаёт Swarm, метку узла SQLite и стек из пяти задач. Затем проверяет размещение задач и CRUD через оба входа: http://127.0.0.1:18081 и http://127.0.0.1:18082.

Повторный запуск выполняется той же командой:

```sh
sh scripts/start_lab.sh
```

Скрипт пересоздаёт служебные контейнеры, очищая временное состояние containerd, затем заново создаёт локальный Swarm, стек и его overlay-сеть. Это устраняет старые сетевые записи после остановки Docker Desktop. Именованные тома с образами и SQLite сохраняются; управляющее состояние Swarm создаётся заново; команда не удаляет данные заметок. На время перезапуска приложение недоступно.

Отдельная проверка уже работающего стенда:

```sh
SWARM_CONTAINER=notes-swarm-demo-manager-1 MIN_SWARM_NODES=2 python3 scripts/check_swarm.py
BASE_URL=http://127.0.0.1:18081 python3 scripts/check.py
BASE_URL=http://127.0.0.1:18082 python3 scripts/check.py
```

Остановка с сохранением данных:

```sh
docker compose -p notes-swarm-demo -f lab.compose.yaml stop
```
