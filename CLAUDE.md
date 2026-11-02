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
- `uv run pytest`: run the tests (the full suite takes ~2.5 minutes, so run it in the background; during TDD cycles run one module, e.g. `uv run pytest tracker/tests/test_jobs.py`)
- `uv run ruff format .` then `uv run ruff check .`: format and lint
- `uv run python manage.py makemigrations --check --dry-run`: confirm no model change is missing a migration

## Status

Phases 1–6 of the plan are done (auth, candidates, skills, job openings, closing/reopening jobs, recording applications). Next is **Phase 7: the read-only applications workspace** at `/applications/`: a list across all jobs filtered by `job`, `stage` (default in-progress), and `q` (candidate name) from the query string, plus a detail panel for the selected application with candidate contact info, job, job status, source, applied date, a stage progress tracker, and links to the candidate's other applications. Wire up the Workspace nav link then. Move the `make_application` fixture to `conftest.py` when a second module needs it. `Candidate.archived` already exists, but the plan adds the archived-candidate refusal to `create_application` in Phase 12.

## What exists

- **`accounts`**: `User` (`AUTH_USER_MODEL = "accounts.User"`) with `role` (`Role.ADMIN`/`Role.STAFF`, default Staff) and an `is_admin` property. Saving syncs `is_staff` and `is_superuser` to the role, so only Admins can manage users at `/admin/`. Users can't be deleted there; deactivate them instead. `User` is the only model in the Django admin (`tracker/admin.py` is empty on purpose). Tests: `accounts/tests/`.
- **`tracker`** (namespace `tracker:`, mounted at `/`):
  - home (`tracker:home`)
  - `Candidate` list (`?q=` search), create, detail, and edit under `/candidates/`. The detail page lists the candidate's applications (job, stage, source, applied date) and links to `candidate_apply` (`/candidates/<pk>/apply/`, both roles), whose `ApplicationForm(candidate=...)` offers only `services.jobs_open_to(candidate)`
  - `JobOpening` (M2M `skills` with reverse name `job_openings`, `status` via `JobStatus`, `employment_type` via `EmploymentType`, `is_open` property, ordered by title). List (`?status=open|closed`) and detail for everyone; Admin-only create and edit, plus Admin-only POST close (`job_close`) and reopen (`job_reopen`) under `/jobs/<pk>/`. Closed jobs show "Closed to new applicants" on the list and detail pages. Editing a job leaves `status` alone, so close/reopen are the only way to change it
  - Admin-only `Skill` list, create, rename, and delete (POST; refused with `SkillInUse` while a job uses it) under `/skills/`
  - `Application` (FK `candidate` and `job`, both `PROTECT`, reverse name `applications`; unique (candidate, job); `source` via `ApplicationSource`; `source_details`; `stage` via `Stage`, default Applied; `applied_on` defaults to today). `create_application` refuses with `JobClosedToApplicants` and `DuplicateApplication`
  - Services so far: `create_candidate`, `update_candidate`, `search_candidates`, `create_skill`, `rename_skill`, `delete_skill`, `create_job`, `update_job`, `filter_jobs`, `close_job`, `reopen_job`, `jobs_open_to`, `create_application`
  - Tests: `tracker/tests/test_<area>.py`
- **Shared templates**: `templates/base.html` (HTML shell that loads Tailwind), `templates/app_base.html` (logged-in nav shell; pages fill `{% block content %}`), `templates/registration/` (login and logged-out pages for Django's auth views at `/accounts/`), and `templates/403.html` (shown when a view raises `PermissionDenied`).
- `LoginRequiredMiddleware` requires login on every page.
- `conftest.py` provides the `admin_user`, `staff_user`, `admin_client`, `staff_client`, `candidate`, `open_job`, and `closed_job` fixtures and `TEST_PASSWORD`. Area-specific fixtures live in their test module until a second module needs them, then move to `conftest.py`: `skill` (test_skills), `make_application(stage=..., candidate=..., job=...)` (test_applications; sets the stage directly until the move service exists in Phase 8).

## Conventions and gotchas

- Status-only services (`close_job`, `reopen_job`) set the field and `save(update_fields=[..., "updated_at"])`, leaving other fields and M2M untouched. Use the same shape for later archive/unarchive.
- Services raise `ValidationError` subclasses that carry context (e.g. `DuplicateCandidateEmail.existing`, `DuplicateSkillName.existing`, `SkillInUse.job_count`).
- Each model's editable fields are a tuple in `services.py` (`CANDIDATE_FIELDS`, `JOB_FIELDS`) that its `ModelForm` uses as `Meta.fields`, so views can call `services.create_x(**form.cleaned_data)`.
- Many-to-many values (e.g. job `skills`) are set inside the service with `.set(...)`, in the same `@transaction.atomic` as the save. `update_job(skills=None)` leaves skills alone; an empty list clears them.
- `ModelForm.is_valid()` checks model constraints before the view can call a service. So a uniqueness rule that needs a friendly error goes in the form's `clean_<field>`, which calls the service check (see `CandidateForm.clean_email`, `SkillForm.clean_name`).
- When the view supplies a related object instead of the form (e.g. `ApplicationForm`'s candidate), the form doesn't check constraints on that field. Limit the choices with a queryset from a service, and have the view catch the service's refusals with `form.add_error(None, error)`.
- Bind forms with `_form_data(request)` in `tracker/views.py`, not `request.POST or None`, which leaves an empty POST unbound with no errors.
- Admin-only views use `@admin_required` from `tracker/permissions.py` (403 for Staff). Also hide their controls with `{% if user.is_admin %}`. Test both roles, GET and POST.
- State-changing actions without a form page (skill delete, job close/reopen; later archive) are `@require_POST` views (stack under `@admin_required`) triggered by a small inline `<form method="post">`, with a JS `confirm()` for destructive ones. They flash a success or error message and redirect.
- List filters come from the query string. Unknown values are ignored (treated as "all"), and the view passes the cleaned value back so the right tab shows as active (see `job_list`).
- Case-insensitive uniqueness uses `UniqueConstraint(Lower(...))` plus a service check that uses `__iexact`. Candidate emails are lowercased before saving; skill names keep the Admin's capitalization (whitespace is collapsed).
- URL names are `<model>_<action>` (e.g. `candidate_edit`); jobs use the short prefix `job_` under `/jobs/`. Templates go in `tracker/templates/tracker/<area>/{list,detail,form}.html`.
- Form templates render fields by hand with DaisyUI classes (see `jobs/form.html` for text, textarea, select, and checkbox-group patterns), with errors in `<span data-field-error="...">`.
- After a successful POST, redirect; show flash messages with `{% include "tracker/_messages.html" %}`.
- Flash messages are auto-escaped, so tests that look for message text compare against `django.utils.html.escape(...)` (quotes and apostrophes are escaped). When a test asserts some text is *absent* (e.g. the "Closed to new applicants" label on open jobs), keep that wording out of other UI text such as `confirm()` prompts.
- Nav links for pages that don't exist yet point to `#` (currently Workspace). Wire them up when the page lands.
- Ruff's `DJ` rules enforce Django model member order: `Meta`, `__str__`, `get_absolute_url`, then custom methods.
- Edit files with the Edit tool or a shell heredoc. Python's `write_text` on Windows writes CRLF and the locale encoding, which has broken files here (if you must use it, pass `encoding="utf-8", newline="\n"`). `sed` replacements that contain quotes or apostrophes inside Python strings get mangled easily; use the Edit tool for those.
- Workflow: one plan phase per `/implement` session (TDD for up to 3 behaviors, stopping for approval at each step), then update `PROMPTS.md`, commit, and push. For RED to fail on an assertion, first add the URL and a placeholder view (e.g. one that only redirects), never leaving it at `NoReverseMatch`. Skip TDD for behaviors an existing pattern already settles (e.g. `@admin_required` refusals); test those normally.

## References

- PRD: `prd/applicant-tracking-system.md`; plan (phases): `plans/applicant-tracking-system.md`
- Prototypes (throwaway, don't promote): `prototypes/`; original brief: `project-idea.md`
