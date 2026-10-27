# Flask + PostgreSQL Tasks API – Phase 2

![CI/CD](https://github.com/shayedry-prog/flask-docker-app/actions/workflows/ci.yml/badge.svg)

A small containerized REST API for managing to-do tasks. It runs as two containers with Docker Compose: a **Flask** app served by Gunicorn and a **PostgreSQL** database. GitHub Actions tests it, runs the full stack, and publishes the image to GitHub Container Registry.

```
┌─────────────┐   HTTP :8000   ┌──────────────────┐   SQL :5432   ┌──────────────┐
│  you / curl │ ─────────────▶ │  web (Flask +    │ ────────────▶ │  db          │
│             │                │  Gunicorn)       │               │  (Postgres)  │
└─────────────┘                └──────────────────┘               └──────┬───────┘
                                                                         │
                                                                  volume: db-data
```

## Quick start

Requirements: Docker with the Compose plugin (`docker compose version`).

```bash
git clone https://github.com/shayedry-prog/flask-docker-app.git
cd flask-docker-app
cp .env.example .env          # then edit POSTGRES_PASSWORD
docker compose up -d --build
```

Check it's running:

```bash
docker compose ps             # both services should be "healthy"
curl http://localhost:8000/health
```

Stop it:

```bash
docker compose down           # keeps the database data
docker compose down -v        # also deletes the data volume
```

## API

| Method | Path | Body | Description |
|---|---|---|---|
| `GET` | `/` | | App info, version and container ID |
| `GET` | `/health` | | `200` if the app can reach the database, else `503` |
| `GET` | `/tasks` | | List all tasks |
| `POST` | `/tasks` | `{"title": "..."}` | Create a task |
| `GET` | `/tasks/<id>` | | Get one task |
| `PATCH` | `/tasks/<id>` | `{"done": true}` | Mark a task done or not done |
| `DELETE` | `/tasks/<id>` | | Delete a task |

Examples:

```bash
curl -X POST localhost:8000/tasks -H 'Content-Type: application/json' -d '{"title":"Learn Docker"}'
curl localhost:8000/tasks
curl -X PATCH localhost:8000/tasks/1 -H 'Content-Type: application/json' -d '{"done":true}'
curl -X DELETE localhost:8000/tasks/1
```

## Configuration

Set in `.env` (copied from `.env.example`). `.env` is git-ignored, so passwords stay off GitHub.

| Variable | Default | Purpose |
|---|---|---|
| `POSTGRES_USER` | `tasks` | Database user |
| `POSTGRES_PASSWORD` | `change-me` | Database password |
| `POSTGRES_DB` | `tasks` | Database name |
| `WEB_PORT` | `8000` | Port on your machine for the app |

## Testing

**Unit tests** (fast, use SQLite, no Docker needed):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v
```

**Smoke test** against the running Compose stack (real PostgreSQL):

```bash
docker compose up -d --build --wait
./scripts/smoke_test.sh
```

## CI/CD

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs three jobs in order:

1. **Unit tests** – `pytest` on every push and pull request
2. **Docker Compose smoke test** – builds the image, starts the full stack, and runs `scripts/smoke_test.sh`
3. **Build and push image** – on pushes to `main` and `v*` tags only, pushes to GitHub Container Registry

Image tags:

| Trigger | Tags |
|---|---|
| Push to `main` | `latest`, `sha-<short-sha>` |
| Tag `v1.2.0` | `1.2.0`, `sha-<short-sha>` |

Pull the published image:

```bash
docker pull ghcr.io/shayedry-prog/flask-docker-app:latest
```

No secrets need to be configured. The workflow uses the built-in `GITHUB_TOKEN`.

## Project structure

```
.
├── .github/workflows/ci.yml   # Test → smoke test → build and push
├── app/
│   ├── __init__.py            # Flask app and routes
│   └── db.py                  # PostgreSQL / SQLite helpers
├── scripts/smoke_test.sh      # End-to-end test of the running stack
├── tests/test_app.py          # Unit tests
├── Dockerfile                 # Production image (non-root, health check)
├── docker-compose.yml         # web + db services
├── .env.example               # Config template
├── requirements.txt           # App dependencies
├── requirements-dev.txt       # + test dependencies
└── wsgi.py                    # Gunicorn entry point
```
