# Applicant Tracking System

An internal Django web app where hiring-team employees manage job openings and
candidates, and move applications through the hiring pipeline.

## Local setup

Requires [uv](https://docs.astral.sh/uv/). uv installs the right Python version for you.

```sh
uv sync                                    # install dependencies
uv run python manage.py migrate            # create the SQLite database
uv run python manage.py createsuperuser    # create the first Admin account
uv run python manage.py tailwind build     # build the Tailwind/DaisyUI stylesheet
uv run python manage.py runserver          # http://127.0.0.1:8000/
```

During template work, `uv run python manage.py tailwind runserver` rebuilds the
stylesheet on change while serving the app.

Accounts created with `createsuperuser` get the **Admin** role. Admins add
further users (Admin or Staff) and deactivate departed employees at `/admin/`.

## Demo data (local development only)

```sh
uv run python manage.py seed_demo
```

This loads a ready-made demo: 15 skills, 5 job openings (one closed), 20
candidates (one archived), and 30 applications spread across every stage, with
stage history that includes notes and Admin reopens. All of it is created
through the app's own business rules.

| Role  | Username     | Password            |
|-------|--------------|---------------------|
| Admin | `demo-admin` | `demo-password-123` |
| Staff | `demo-staff` | `demo-password-123` |

> **Warning:** these credentials are public. Use them only on a local
> development database, never on a server anyone else can reach.

Running the command again deletes the previous demo data and loads it fresh.
It refuses (changing nothing) if the database holds any candidate, job opening,
or skill it didn't create, so it never touches real records. Your own user
accounts, such as the one from `createsuperuser`, are left alone.

## Checks

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
