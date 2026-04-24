# rasa_project/

Rasa CALM project used by Ex6. Runs inside a Docker container (see
`docs/rasa-docker.md`) on port 5005; the custom-action server runs on 5055.

## Layout

```
rasa_project/
├── config.yml            Pipeline and policies
├── credentials.yml       Channels (REST enabled for our use)
├── endpoints.yml         Action server URL
├── domain.yml            Intents, slots, responses
├── data/
│   ├── flows.yml         Three flows (TODO for student)
│   └── nlu.yml           NLU examples (TODO for student)
└── actions/
    ├── __init__.py
    └── actions.py        ActionValidateBooking (TODO for student)
```

## Running

Build and start:

```
make ex6-real         # will spin the container up on first run
```

Manual: see `docs/rasa-docker.md` for the full docker-compose flow.

## What to implement

- **flows.yml**: three flows — `confirm_booking`, `resume_from_loop`, `request_research`.
- **nlu.yml**: at least two examples per intent referenced by the flows.
- **actions.py**: `ActionValidateBooking` custom action.

The grader tests each flow individually via REST, so you can partial-credit
even if not all three flows are complete.
