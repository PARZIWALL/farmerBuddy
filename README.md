# farmerBuddy

A minimal Flask backend scaffold with a clean separation between controllers (HTTP layer) and services (business logic).

## Project structure

```
app/
  __init__.py            # App factory, blueprint registration
  controllers/           # HTTP handlers
    health_controller.py
    user_controller.py
  services/              # Business logic
    user_service.py
config.py                # App configuration
run.py                   # Local dev entrypoint
requirements.txt
tests/
  test_health.py
  test_user.py
```

## Getting started (Windows PowerShell)

1. Create and activate a virtual environment
   - Python 3: `py -3 -m venv .venv`
   - Activate: `.\.venv\Scripts\Activate.ps1`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the server: `python run.py`
4. Open:
   - Health: `http://127.0.0.1:5000/health`
   - Users list: `http://127.0.0.1:5000/api/users/`

## Running tests

```
pytest -q
```

## Where to put code

- Controllers: add new blueprints in `app/controllers/` and register them in `app/__init__.py`.
- Services: business logic goes in `app/services/` and is imported by controllers.

