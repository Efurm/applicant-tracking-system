# Applicant Tracking System

An internal Django web app where hiring-team employees manage job openings and candidates, and move applications through the hiring pipeline. Candidates never log in.

## Stack

- Python, Django, SQLite; project and dependencies managed with **uv**
- Tailwind CSS + DaisyUI via **django-tailwind-cli**
- **HTMX** for partial page updates
- **Ruff** for linting and formatting
- **pytest + pytest-django** for tests

## Architecture decisions (from the PRD)

- Two Django apps: `accounts` (custom User model only, present from the first migration) and `tracker` (all hiring functionality).
- Business rules live in a services layer, not in views or forms. Views stay thin: they call services and turn service validation errors into user-facing messages.
- Authorization is role-based (Admin and Staff) on the custom User model and is always enforced server-side, regardless of what the UI shows.

## Commands

Run everything through `uv run` (uv manages Python 3.13 and the `.venv`).

- `uv sync`: install dependencies
- `uv run python manage.py migrate`: create/update the SQLite database
- `uv run python manage.py createsuperuser`: create an account with the Admin role
- `uv run python manage.py runserver`: dev server at http://127.0.0.1:8000/
- `uv run python manage.py tailwind build`: build `assets/css/tailwind.css` from `frontend/source.css` (the first run downloads the Tailwind CLI with DaisyUI into `.django_tailwind_cli/`)
- `uv run python manage.py tailwind runserver`: dev server plus Tailwind watcher, for template work
- `uv run pytest`: run the tests
- `uv run ruff check .` and `uv run ruff format .`: lint and format

## Django apps

The project package is `config` (settings, root URLs).

- **`accounts`** owns only the custom `User` model (`AUTH_USER_MODEL = "accounts.User"`), with a `role` field (`Role.ADMIN` or `Role.STAFF`, default Staff) and an `is_admin` property. Saving a user syncs `is_staff` and `is_superuser` to the role, so Admins can manage users at `/admin/` and Staff cannot. `createsuperuser` creates an Admin. Its Django admin registration exposes role and `is_active` and blocks deleting users; deactivate them instead. Tests are in `accounts/tests/`.
- **`tracker`** owns all hiring functionality (namespace `tracker:`, mounted at `/`). Done so far: home (`tracker:home`) `Candidate` list (`?q=` search), create, detail, and edit under `/candidates/`; and Admin-only `Skill` list, create, and rename under `/skills/`. Tests are in `tracker/tests/test_<area>.py`.

Shared pieces outside the apps:
- `templates/base.html` is the HTML shell that loads Tailwind.
- `templates/app_base.html` is the logged-in nav shell. App pages extend it and fill `{% block content %}`, and Admin-only controls are wrapped in `{% if user.is_admin %}`.
- `templates/registration/` holds the login and logged-out pages, which use Django's built-in auth views at `/accounts/`.
- `LoginRequiredMiddleware` requires login on every page by default.
- `templates/403.html` is the styled page shown when a view raises `PermissionDenied`.
- `conftest.py` provides the `admin_user`, `staff_user`, `admin_client`, and `staff_client` fixtures and `TEST_PASSWORD`.

## Conventions and gotchas

- `tracker/services.py` holds every rule. Services raise `ValidationError` subclasses that carry context (e.g. `DuplicateCandidateEmail.existing`).
- `ModelForm.is_valid()` checks model constraints before the view can call a service. So a uniqueness rule that needs a friendly error goes in the form's `clean_<field>`, which calls the service check (see `CandidateForm.clean_email`).
- Bind forms with `_form_data(request)` in `tracker/views.py`, not `request.POST or None`, which leaves an empty POST unbound with no errors.
- Admin-only views use `@admin_required` from `tracker/permissions.py` (403 for Staff). Hide their controls in templates with `{% if user.is_admin %}` too.
- Case-insensitive uniqueness uses a `UniqueConstraint(Lower(...))`. Candidate emails are lowercased before saving; skill names keep the Admin's capitalization (whitespace is collapsed).
- URL names are `<model>_<action>` (e.g. `candidate_edit`). Templates go in `tracker/templates/tracker/<area>/{list,detail,form}.html`.
- Flash messages render via `{% include "tracker/_messages.html" %}`.
- Nav links for pages that don't exist yet point to `#`. Wire them up when the page lands.
- Ruff's `DJ` rules enforce Django model member order: `Meta`, `__str__`, `get_absolute_url`, then custom methods.
- On Windows, bare `python` isn't on PATH, so always use `uv run python`.
- Workflow: one plan phase per `/implement` session (TDD for up to 3 behaviors), then update `PROMPTS.md`, commit, and push.

## References

- PRD (requirements and decisions): `prd/applicant-tracking-system.md`
- Implementation plan (phases): `plans/applicant-tracking-system.md`
- Prototypes: `prototypes/`
- Original assignment brief: `project-idea.md`
