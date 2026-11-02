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

Phases 1–8 are done (auth, candidates, skills, jobs, close/reopen, recording applications, read-only workspace, HTMX forward stage moves); 118 tests.
Next is **Phase 9: Rejected, Withdrawn, and the final lock**:
- Extend `services.allowed_next_stages` so every in-progress stage also offers Rejected and Withdrawn, and final stages offer nothing (they already offer nothing). Update `test_allowed_next_stages_...` in `test_moves.py` to the new lists.
- Panel: Reject/Withdraw controls for in-progress applications, "final" messaging and no move form for final ones.
- Then drop the direct-`stage` fallback in `make_application`, so every fixture stage goes through `move_application`.

`Candidate.archived` exists, but the archived-candidate refusal in `create_application` is Phase 12.

## What exists

- **`accounts`**: `User` (`AUTH_USER_MODEL = "accounts.User"`) with `role` (`Role.ADMIN`/`Role.STAFF`, default Staff) and an `is_admin` property. Saving syncs `is_staff` and `is_superuser` to the role, so only Admins can manage users at `/admin/`. Users can't be deleted there; deactivate them instead. `User` is the only model in the Django admin (`tracker/admin.py` is empty on purpose). Tests: `accounts/tests/`.
- **`tracker`** (namespace `tracker:`, mounted at `/`; home is `tracker:home`):
  - `Candidate` list (`?q=` search), create, detail, and edit under `/candidates/`. The detail page lists the candidate's applications and links to `candidate_apply` (`/candidates/<pk>/apply/`, both roles). There, `ApplicationForm(candidate=...)` offers only `services.jobs_open_to(candidate)`
  - `JobOpening` (M2M `skills` with reverse name `job_openings`, `status` via `JobStatus`, `employment_type` via `EmploymentType`, `is_open` property, ordered by title). List (`?status=open|closed`) and detail for everyone; Admin-only create and edit, plus Admin-only POST close (`job_close`) and reopen (`job_reopen`) under `/jobs/<pk>/`. Closed jobs show "Closed to new applicants" on the list and detail pages. Editing a job leaves `status` alone, so close/reopen are the only way to change it
  - Admin-only `Skill` list, create, rename, and delete (POST; refused with `SkillInUse` while a job uses it) under `/skills/`
  - `Application`: FKs `candidate` and `job` (both `PROTECT`, reverse name `applications`, unique together), `source` (`ApplicationSource`), `source_details`, `stage` (`Stage`, default Applied), `applied_on` (defaults to `timezone.localdate`); ordered newest first. `is_final` property and `pipeline_progress()` (the six pipeline steps, each `done`/`current`/`todo`; all `todo` for Rejected/Withdrawn). Module-level `PIPELINE_STAGES` (Applied→Hired), `IN_PROGRESS_STAGES` (Applied–Offer), and `FINAL_STAGES` (Hired, Rejected, Withdrawn) in `tracker/models.py`.
  - `StageChange` (`application` FK `CASCADE`, reverse `stage_changes`; `from_stage`, `to_stage`; `changed_by` FK user `PROTECT`; `changed_at` default now; ordered by `changed_at`, `pk`). No `note` yet (Phase 10)
  - Stage moves: `services.allowed_next_stages(stage, user)` (forward only: later `PIPELINE_STAGES`; `user` unused until Phase 11) drives both the panel's buttons and `services.move_application(application, to_stage, user)`, which re-reads the stage with `select_for_update`, raises `InvalidStageMove` (message "Can't move this application from X to Y.") or saves the stage and writes a `StageChange`, all in one transaction. Moves ignore job status. POST `application_move` (`/applications/<pk>/move/`, both roles, form field `stage`, filters in its query string): with `HX-Request` it renders `_move.html` (`_panel.html` + `_row.html` with `oob=True` → `hx-swap-oob="true"`), with refusals in `data-move-error` at status 200 (HTMX skips 4xx swaps by default); without HTMX it flashes and redirects to the workspace with `selected`
  - Workspace `application_workspace` at `/applications/` (both roles): `?job=<pk>`, `?stage=<Stage value>|all` (blank or unknown = in-progress), `?q=` (every word must match first or last name), and `?selected=<pk>` for the detail panel (no selection, or an unknown one, shows "Select an application"). Templates `applications/workspace.html`, `_row.html` (`data-application-row`), `_panel.html` (`data-panel`, `data-panel-field="..."`, `data-step` + `data-step-state`, `data-other-application`, `data-move-form` with `data-move-to` buttons, `data-move-error`). The view helpers `_workspace_filters(request)` and `_panel_context(request, application, filter_query, move_error)` are shared by the workspace and the move endpoint, so the panel renders the same in both. Row and other-application links keep the current filters via the view's `filter_query` and use the full `{% url %}` path (not a bare `?…`), since HTMX responses come from other endpoints. The nav's Workspace link points here
  - Services so far: `create_candidate`, `update_candidate`, `search_candidates`, `create_skill`, `rename_skill`, `delete_skill`, `create_job`, `update_job`, `filter_jobs`, `close_job`, `reopen_job`, `jobs_open_to`, `create_application`, `filter_applications(job, stage, query)` (with `ALL_STAGES = "all"`), `allowed_next_stages`, `move_application`
  - Tests: `tracker/tests/test_<area>.py`. `tracker/tests/html.py`'s `marked(response, attr)` (stdlib `HTMLParser`) returns `(value, attrs, text)` for each element carrying `attr`; use it for panel/row assertions. Stage-move tests are in `test_moves.py`; HTMX requests pass `headers={"HX-Request": "true"}`. Filter on the value when an attribute like `aria-current` appears in more than one place
- **Shared templates**: `templates/base.html` (HTML shell that loads Tailwind and HTMX 2.0.4, vendored at `assets/js/htmx.min.js`), `templates/app_base.html` (logged-in nav shell; pages fill `{% block content %}`), `templates/registration/` (Django auth views at `/accounts/`), `templates/403.html` (for `PermissionDenied`). `LoginRequiredMiddleware` requires login on every page.
- **Fixtures**: `conftest.py` has `admin_user`, `staff_user`, `admin_client`, `staff_client`, `candidate`, `open_job`, `closed_job`, `make_application(stage=..., candidate=..., job=...)` (goes through `create_application`, so record applications before closing a job; then one `move_application` by `staff_user` for a pipeline stage, so those applications already have a `StageChange`. Rejected/Withdrawn are still set directly until Phase 9), and `TEST_PASSWORD`. Area-specific ones stay in their test module until a second module needs them: `skill` (test_skills).

## Conventions and gotchas

- Status-only services (`close_job`, `reopen_job`) set the field and `save(update_fields=[..., "updated_at"])`, leaving other fields and M2M untouched. Use the same shape for later archive/unarchive.
- Services raise `ValidationError` subclasses that carry context (e.g. `DuplicateCandidateEmail.existing`, `SkillInUse.job_count`, `JobClosedToApplicants.job`, `DuplicateApplication.existing`).
- Each model's editable fields are a tuple in `services.py` (`CANDIDATE_FIELDS`, `JOB_FIELDS`, `APPLICATION_FIELDS`) that its `ModelForm` uses as `Meta.fields`, so views can call `services.create_x(**form.cleaned_data)`.
- Many-to-many values (e.g. job `skills`) are set inside the service with `.set(...)`, in the same `@transaction.atomic` as the save. `update_job(skills=None)` leaves skills alone; an empty list clears them.
- `ModelForm.is_valid()` checks model constraints before the view can call a service. So a uniqueness rule that needs a friendly error goes in the form's `clean_<field>`, which calls the service check (see `CandidateForm.clean_email`, `SkillForm.clean_name`).
- When the view supplies a related object instead of the form (e.g. `ApplicationForm`'s candidate), the form doesn't check constraints on that field. Limit the choices with a queryset from a service, and have the view catch the service's refusals with `form.add_error(None, error)` (see `candidate_apply`).
- Bind forms with `_form_data(request)` in `tracker/views.py`, not `request.POST or None`, which leaves an empty POST unbound with no errors.
- Admin-only views use `@admin_required` from `tracker/permissions.py` (403 for Staff). Also hide their controls with `{% if user.is_admin %}`. Test both roles, GET and POST.
- State-changing actions without a form page (skill delete, job close/reopen; later archive) are `@require_POST` views (stack under `@admin_required`) triggered by a small inline `<form method="post">`, with a JS `confirm()` for destructive ones. They flash a success or error message and redirect.
- List filters come from the query string. Unknown values fall back to the default ("all" for `job_list`; in-progress for the workspace `stage`), and the view passes the cleaned value back so the active tab or `<option selected>` matches.
- Case-insensitive uniqueness uses `UniqueConstraint(Lower(...))` plus a service check that uses `__iexact`. Candidate emails are lowercased before saving; skill names keep the Admin's capitalization (whitespace is collapsed).
- URL names are `<model>_<action>` (e.g. `candidate_edit`, `candidate_apply`); jobs use the short prefix `job_` under `/jobs/`. Templates go in `tracker/templates/tracker/<area>/{list,detail,form}.html` (plus action pages like `candidates/apply.html`).
- Form templates render fields by hand with DaisyUI classes (see `jobs/form.html` for text, textarea, select, and checkbox-group patterns), with errors in `<span data-field-error="...">`. Pages that show a value tests need to find mark it with a `data-` attribute (e.g. `data-application-stage`), so tests don't rely on loose text matches like `"Applied" in page`.
- After a successful POST, redirect; every page that receives a redirect with a message needs `{% include "tracker/_messages.html" %}`.
- Flash messages are auto-escaped, so tests that look for message text compare against `django.utils.html.escape(...)` (quotes and apostrophes are escaped). When a test asserts some text is *absent* (e.g. the "Closed to new applicants" label on open jobs), keep that wording out of other UI text such as `confirm()` prompts. Compare displayed dates with `django.utils.dateformat.format(d, "M j, Y")`; `strftime("%-d")` fails on Windows.
- Ruff's `DJ` rules enforce Django model member order: `Meta`, `__str__`, `get_absolute_url`, then custom methods. After adding a migration, run `migrate` before checking pages by hand (tests don't touch `db.sqlite3`).
- File editing: use the Edit or Write tool, or one shell heredoc per command. Never chain two heredocs (one gets fed the other's input), and don't heredoc text that mentions heredoc syntax. For scripted edits, save a script to the scratchpad, run it with `uv run python`, and pass `encoding="utf-8", newline="\n"` (Windows `write_text` otherwise writes CRLF and the locale encoding). `sed` mangles quotes and apostrophes inside Python strings; use the Edit tool for those.
- Workflow: one plan phase per `/implement` session (TDD for up to 3 behaviors, stopping for approval at each step), then update `PROMPTS.md`, commit, and push. For RED to fail on an assertion, first add the URL, a placeholder view, and any new exception classes, never leaving it at `NoReverseMatch` or `AttributeError`. Skip TDD for behaviors an existing pattern already settles (e.g. `@admin_required` refusals); test those normally.

## References

- PRD: `prd/applicant-tracking-system.md`; plan (phases): `plans/applicant-tracking-system.md`. Prototypes (throwaway, don't promote): `prototypes/`; original brief: `project-idea.md`
