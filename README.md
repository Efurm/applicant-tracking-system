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

## Checks

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
