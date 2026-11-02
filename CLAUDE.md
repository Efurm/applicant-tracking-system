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
- `uv run pytest`: run the tests (the full suite takes ~2 minutes; during TDD cycles run one module, e.g. `uv run pytest tracker/tests/test_jobs.py`)
- `uv run ruff format .` then `uv run ruff check .`: format and lint
- `uv run python manage.py makemigrations --check --dry-run`: confirm no model change is missing a migration

## Status

Phases 1–5 of the plan are done (auth, candidates, skills, job openings, closing/reopening jobs). Next is **Phase 6: recording applications**: the `Application` model, a `create_application` service (refuses closed jobs and duplicates), and an "Apply to a job" form on the candidate page. Move the `open_job`/`closed_job` fixtures to `conftest.py` then.

## What exists

- **`accounts`**: `User` (`AUTH_USER_MODEL = "accounts.User"`) with `role` (`Role.ADMIN`/`Role.STAFF`, default Staff) and an `is_admin` property. Saving syncs `is_staff` and `is_superuser` to the role, so only Admins can manage users at `/admin/`. Users can't be deleted there; deactivate them instead. `User` is the only model in the Django admin (`tracker/admin.py` is empty on purpose). Tests: `accounts/tests/`.
- **`tracker`** (namespace `tracker:`, mounted at `/`):
  - home (`tracker:home`)
  - `Candidate` list (`?q=` search), create, detail, and edit under `/candidates/`
  - `JobOpening` (M2M `skills` with reverse name `job_openings`, `status` via `JobStatus`, `employment_type` via `EmploymentType`, `is_open` property, ordered by title). List (`?status=open|closed`) and detail for everyone; Admin-only create and edit, plus Admin-only POST close (`job_close`) and reopen (`job_reopen`) under `/jobs/<pk>/`. Closed jobs show "Closed to new applicants" on the list and detail pages. Editing a job leaves `status` alone, so close/reopen are the only way to change it
  - Admin-only `Skill` list, create, rename, and delete (POST; refused with `SkillInUse` while a job uses it) under `/skills/`
  - Services so far: `create_candidate`, `update_candidate`, `search_candidates`, `create_skill`, `rename_skill`, `delete_skill`, `create_job`, `update_job`, `filter_jobs`, `close_job`, `reopen_job`
  - Tests: `tracker/tests/test_<area>.py`
- **Shared templates**: `templates/base.html` (HTML shell that loads Tailwind), `templates/app_base.html` (logged-in nav shell; pages fill `{% block content %}`), `templates/registration/` (login and logged-out pages for Django's auth views at `/accounts/`), and `templates/403.html` (shown when a view raises `PermissionDenied`).
- `LoginRequiredMiddleware` requires login on every page.
- `conftest.py` provides the `admin_user`, `staff_user`, `admin_client`, and `staff_client` fixtures and `TEST_PASSWORD`. Area-specific fixtures live in their test module until a second module needs them, then move to `conftest.py`: `candidate` (test_candidates), `skill` (test_skills), `open_job` and `closed_job` (test_jobs; Phase 6 will need them too).

## Conventions and gotchas

- Services raise `ValidationError` subclasses that carry context (e.g. `DuplicateCandidateEmail.existing`, `DuplicateSkillName.existing`, `SkillInUse.job_count`).
- Each model's editable fields are a tuple in `services.py` (`CANDIDATE_FIELDS`, `JOB_FIELDS`) that its `ModelForm` uses as `Meta.fields`, so views can call `services.create_x(**form.cleaned_data)`.
- Many-to-many values (e.g. job `skills`) are set inside the service with `.set(...)`, in the same `@transaction.atomic` as the save. `update_job(skills=None)` leaves skills alone; an empty list clears them.
- `ModelForm.is_valid()` checks model constraints before the view can call a service. So a uniqueness rule that needs a friendly error goes in the form's `clean_<field>`, which calls the service check (see `CandidateForm.clean_email`, `SkillForm.clean_name`).
- Bind forms with `_form_data(request)` in `tracker/views.py`, not `request.POST or None`, which leaves an empty POST unbound with no errors.
- Admin-only views use `@admin_required` from `tracker/permissions.py` (403 for Staff). Also hide their controls with `{% if user.is_admin %}`. Test both roles, GET and POST.
- State-changing actions without a form page (skill delete, job close/reopen; later archive) are `@require_POST` views (stack under `@admin_required`) triggered by a small inline `<form method="post">`, with a JS `confirm()` for destructive ones. They flash a success or error message and redirect.
- List filters come from the query string. Unknown values are ignored (treated as "all"), and the view passes the cleaned value back so the right tab shows as active (see `job_list`).
- Case-insensitive uniqueness uses `UniqueConstraint(Lower(...))` plus a service check that uses `__iexact`. Candidate emails are lowercased before saving; skill names keep the Admin's capitalization (whitespace is collapsed).
- URL names are `<model>_<action>` (e.g. `candidate_edit`); jobs use the short prefix `job_` under `/jobs/`. Templates go in `tracker/templates/tracker/<area>/{list,detail,form}.html`.
- Form templates render fields by hand with DaisyUI classes (see `jobs/form.html` for text, textarea, select, and checkbox-group patterns), with errors in `<span data-field-error="...">`.
- After a successful POST, redirect; show flash messages with `{% include "tracker/_messages.html" %}`.
- Flash messages are auto-escaped, so tests that look for message text compare against `django.utils.html.escape(...)` (quotes and apostrophes are escaped).
- Nav links for pages that don't exist yet point to `#` (currently Workspace). Wire them up when the page lands.
- Ruff's `DJ` rules enforce Django model member order: `Meta`, `__str__`, `get_absolute_url`, then custom methods.
- Edit files with the Edit tool or a shell heredoc. Python's `write_text` on Windows writes CRLF and the locale encoding, which has broken files here (if you must use it, pass `encoding="utf-8", newline="\n"`). `sed` replacements that contain quotes or apostrophes inside Python strings get mangled easily; use the Edit tool for those.
- Workflow: one plan phase per `/implement` session (TDD for up to 3 behaviors, stopping for approval at each step), then update `PROMPTS.md`, commit, and push.

## References

- PRD: `prd/applicant-tracking-system.md`; plan (phases): `plans/applicant-tracking-system.md`
- Prototypes (throwaway, don't promote): `prototypes/`; original brief: `project-idea.md`
