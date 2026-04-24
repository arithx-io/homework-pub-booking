# Rasa in Docker (for Ex6)

You run Rasa in a Docker container rather than installing it into your
Python venv. Rasa's version pins conflict with several of sovereign-agent's
optional extras — keeping it in a container keeps the venvs clean.

## Prerequisites

- Docker installed (see SETUP.md §8 or your OS-specific setup doc).
- `NEBIUS_KEY` in `.env` (Rasa CALM uses it for the LLM command generator).

## Two containers: server + actions

Rasa CALM is two processes:

1. **Rasa server** (port 5005): the dialog manager.
2. **Action server** (port 5055): runs your custom actions (`actions.py`).

Both share the `rasa_project/` directory via a bind mount.

## Pull the images

```
docker pull rasa/rasa-pro:latest
docker pull rasa/rasa-pro-actions:latest
```

These are ~2 GB together. First pull takes 5-15 minutes depending on
your connection.

## Start with docker-compose (recommended)

The homework ships with a working compose file; `make ex6-real` invokes it.

```
# From the repo root:
cd rasa_project
docker-compose up     # starts both server and actions
```

In another terminal:

```
# Verify the server is responsive:
curl http://localhost:5005/status
# Expect: {"model_file":"<path>","num_active_training_jobs":0,...}
```

## Train the model

```
docker-compose run --rm rasa-server train
```

This compiles `domain.yml`, `flows.yml`, and `nlu.yml` into a model
artifact in `rasa_project/models/`. Takes 1-3 minutes.

Train each time you change the flows or domain.

## Talk to it

Send a REST message:

```
curl -X POST http://localhost:5005/webhooks/rest/webhook \
  -H "Content-Type: application/json" \
  -d '{"sender":"test-user","message":"/confirm_booking{\"venue_id\":\"haymarket_tap\",\"date\":\"2026-04-25\",\"time\":\"19:30\",\"party_size\":6,\"deposit_gbp\":200}"}'
```

Expected response: a list of `{recipient_id, text}` dicts.

## Stopping

```
docker-compose down
```

## Known issues

- **Apple Silicon**: pulling without `--platform linux/amd64` sometimes
  grabs the wrong image. Explicit platform:
  ```
  docker pull --platform linux/amd64 rasa/rasa-pro:latest
  ```
- **Action server can't reach localhost**: inside a container, `localhost`
  is the container itself. The action server in our compose file uses
  the service name `action-server` (Docker network DNS), not `localhost`.
- **Training fails with "Invalid flow step"**: your `flows.yml` has a
  syntax issue. Run `docker-compose run rasa-server train --debug` for
  a full stack trace.

## If Rasa is just too heavy for your machine

You can still earn partial credit on Ex6 by completing the Python-side
(`structured_half.py`, `validator.py`) without a live Rasa container.
`make ex6` (offline) tests the validator in isolation. You lose the
points for "live Rasa round trip" but keep the Python marks.
