# Applicant Tracking System

An internal Django web app where hiring-team employees manage job openings and candidates, and move applications through the hiring pipeline. Candidates never log in.

## Stack and architecture (from the PRD)

- Python 3.13, Django, SQLite, managed with **uv**; Tailwind CSS + DaisyUI via **django-tailwind-cli**; **HTMX** for partial updates; **Ruff**; **pytest + pytest-django**.
- Two Django apps: `accounts` (custom User model only) and `tracker` (all hiring functionality). The project package is `config`.
- Business rules live in `tracker/services.py`, not in views or forms. Views stay thin: they call services and turn service validation errors into user-facing messages.
- Authorization is role-based (Admin and Staff) and always enforced server-side, regardless of what the UI shows.

## Commands

Run everything through `uv run` (on Windows, bare `python` isn't on PATH).

- `uv sync`: install dependencies
- `uv run python manage.py migrate`: create/update the SQLite database
- `uv run python manage.py createsuperuser`: create an account with the Admin role
- `uv run python manage.py tailwind runserver`: dev server (http://127.0.0.1:8000/) plus Tailwind watcher. Use it after adding templates, so new classes get CSS
- `uv run python manage.py tailwind build`: one-off build of `assets/css/tailwind.css` from `frontend/source.css`
- `uv run pytest`: run the tests
- `uv run ruff format .` then `uv run ruff check .`: format and lint

## Status

Phases 1–4 of the plan are done (auth, candidates, skills, job openings). Next is **Phase 5: closing and reopening jobs**.

## What exists

- **`accounts`**: `User` (`AUTH_USER_MODEL = "accounts.User"`) with `role` (`Role.ADMIN`/`Role.STAFF`, default Staff) and an `is_admin` property. Saving syncs `is_staff` and `is_superuser` to the role, so only Admins can manage users at `/admin/`. Users can't be deleted there; deactivate them instead. Tests: `accounts/tests/`.
- **`tracker`** (namespace `tracker:`, mounted at `/`):
  - home (`tracker:home`)
  - `Candidate` list (`?q=` search), create, detail, and edit under `/candidates/`
  - `JobOpening` (M2M `skills`, `status` Open/Closed via `JobStatus`, `employment_type` via `EmploymentType`) list (`?status=open|closed`) and detail for everyone; Admin-only create and edit under `/jobs/`
  - Admin-only `Skill` list, create, rename, and delete (POST; refused with `SkillInUse` while a job uses it) under `/skills/`
  - Tests: `tracker/tests/test_<area>.py`
- **Shared templates**: `templates/base.html` (HTML shell that loads Tailwind), `templates/app_base.html` (logged-in nav shell; pages fill `{% block content %}`), `templates/registration/` (login and logged-out pages for Django's auth views at `/accounts/`), and `templates/403.html` (shown when a view raises `PermissionDenied`).
- `LoginRequiredMiddleware` requires login on every page.
- `conftest.py` provides the `admin_user`, `staff_user`, `admin_client`, and `staff_client` fixtures and `TEST_PASSWORD`. Area-specific fixtures (e.g. `candidate`, `skill`) live in their test module until a second module needs them.

## Conventions and gotchas

- Services raise `ValidationError` subclasses that carry context (e.g. `DuplicateCandidateEmail.existing`, `DuplicateSkillName.existing`).
- `ModelForm.is_valid()` checks model constraints before the view can call a service. So a uniqueness rule that needs a friendly error goes in the form's `clean_<field>`, which calls the service check (see `CandidateForm.clean_email`, `SkillForm.clean_name`).
- Bind forms with `_form_data(request)` in `tracker/views.py`, not `request.POST or None`, which leaves an empty POST unbound with no errors.
- Admin-only views use `@admin_required` from `tracker/permissions.py` (403 for Staff). Also hide their controls with `{% if user.is_admin %}`. Test both roles, GET and POST.
- Case-insensitive uniqueness uses `UniqueConstraint(Lower(...))` plus a service check that uses `__iexact`. Candidate emails are lowercased before saving; skill names keep the Admin's capitalization (whitespace is collapsed).
- URL names are `<model>_<action>` (e.g. `candidate_edit`). Templates go in `tracker/templates/tracker/<area>/{list,detail,form}.html`.
- After a successful POST, redirect; show flash messages with `{% include "tracker/_messages.html" %}`.
- Nav links for pages that don't exist yet point to `#` (currently Workspace). Wire them up when the page lands.
- Flash messages are auto-escaped, so tests that look for message text compare against `django.utils.html.escape(...)` (quotes and apostrophes are escaped).
- Ruff's `DJ` rules enforce Django model member order: `Meta`, `__str__`, `get_absolute_url`, then custom methods.
- Edit files with the Edit tool or a shell heredoc. Python's `write_text` on Windows writes CRLF and the locale encoding, which has broken files here. If you must use it, pass `encoding="utf-8", newline="\n"`.
- Workflow: one plan phase per `/implement` session (TDD for up to 3 behaviors, stopping for approval at each step), then update `PROMPTS.md`, commit, and push.

## References

- PRD: `prd/applicant-tracking-system.md`; plan (phases): `plans/applicant-tracking-system.md`
- Prototypes (throwaway, don't promote): `prototypes/`; original brief: `project-idea.md`
