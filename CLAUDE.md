# Applicant Tracking System

An internal Django web app where hiring-team employees manage job openings and candidates, and move applications through the hiring pipeline. Candidates never log in.

## Stack and architecture (from the PRD)

- Python 3.13, Django, SQLite, managed with **uv**; Tailwind CSS + DaisyUI via **django-tailwind-cli**; **HTMX** for partial updates; **Ruff**; **pytest + pytest-django**. Two apps: `accounts` (custom User only) and `tracker` (everything else); the project package is `config`.
- Business rules live in `tracker/services.py`, not in views or forms. Views stay thin: they call services and turn service validation errors into user-facing messages.
- Authorization is role-based (Admin and Staff) and always enforced server-side, regardless of what the UI shows.

## Commands

Run everything through `uv run` (on Windows, bare `python` isn't on PATH).

- `uv sync`; `uv run python manage.py migrate`; `uv run python manage.py createsuperuser` (an Admin account)
- `uv run python manage.py tailwind runserver`: dev server (http://127.0.0.1:8000/) plus Tailwind watcher. Use it after adding templates, so new classes get CSS (`tailwind build` does a one-off build of `assets/css/tailwind.css`, which is gitignored)
- `uv run pytest`: the full suite takes ~4 minutes, so run it in the background; during TDD cycles run one module (e.g. `uv run pytest tracker/tests/test_moves.py`)
- `uv run ruff format .` then `uv run ruff check .`; `uv run python manage.py makemigrations --check --dry-run`

## Status

Phases 1–10 are done (auth, candidates, skills, jobs, close/reopen, recording applications, read-only workspace, HTMX stage moves, Reject/Withdraw and the final lock, move notes and the stage-history timeline); 157 tests.
Next is **Phase 11: Admin reopen of final applications** (below).

Later phases:
- **11 (Admin reopen):** reopens go through `move_application`, so they get a note and a timeline entry with no extra work. Use `allowed_next_stages`'s `user` argument to give Admins the in-progress stages from a final stage. Update the Staff-only table test and extend the Admin guard test (in-progress only today). In the panel, Admins need reopen buttons where final applications show `data-final-message` and no form; `_panel_context` puts any non-ending stage in `forward_moves`, so split out reopen moves too. The ending buttons' `confirm()` says "Staff can't undo this."
- **12:** the archived-candidate refusals in `create_application` and reopen (`Candidate.archived` exists).

## What exists

- **`accounts`**: `User` (`AUTH_USER_MODEL = "accounts.User"`) with `role` (`Role.ADMIN`/`Role.STAFF`, default Staff) and `is_admin`. Saving syncs `is_staff`/`is_superuser` to the role, so only Admins reach `/admin/`, where `User` is the only model (`tracker/admin.py` is empty on purpose). Users are deactivated, never deleted.
- **`tracker`** (namespace `tracker:`, mounted at `/`; home is `tracker:home`):
  - `Candidate` list (`?q=`), create, detail (lists its applications), edit, and `candidate_apply` (`/candidates/<pk>/apply/`), whose `ApplicationForm(candidate=...)` offers only `services.jobs_open_to(candidate)`
  - `JobOpening` (M2M `skills`, reverse `job_openings`; `status` via `JobStatus`; `employment_type`; `is_open`). List (`?status=open|closed`) and detail for everyone; Admin-only create/edit and POST `job_close`/`job_reopen` (the only way to change `status`). Closed jobs show "Closed to new applicants"
  - Admin-only `Skill` list, create, rename, and POST delete (refused with `SkillInUse` while a job uses it) under `/skills/`
  - `Application` (`candidate`/`job` FKs `PROTECT`, reverse `applications`, unique together; `source`, `source_details`, `stage` default Applied, `applied_on`; newest first; `is_final`, `pipeline_progress()`). `PIPELINE_STAGES`, `IN_PROGRESS_STAGES`, `FINAL_STAGES` are module-level in `tracker/models.py`; `services.ENDING_STAGES` is Rejected and Withdrawn
  - `StageChange` (`application` FK, reverse `stage_changes`; `from_stage`, `to_stage`, `changed_by` user `PROTECT`, `changed_at`, optional `note`; ordered by time). Every stage change goes through `services.move_application(application, to_stage, user, note="")` (the note is stripped): it re-reads the stage with `select_for_update`, checks it against `allowed_next_stages(stage, user)` (the same rule that draws the buttons: later pipeline stages then `ENDING_STAGES` from in-progress, nothing from final), and raises `InvalidStageMove` or saves and writes a `StageChange` in one transaction. Job status is ignored
  - Workspace `application_workspace` at `/applications/`: `?job=`, `?stage=<Stage value>|all` (blank/unknown = in-progress), `?q=` (every word matches first or last name), `?selected=<pk>`. Templates `applications/workspace.html`, `_row.html`, `_panel.html`, `_move.html`. View helpers `_workspace_filters(request)` and `_panel_context(request, application, filter_query, move_error)` are shared with the move endpoint, so the panel renders the same in both. `_panel_context` splits the allowed moves into `forward_moves` ("Move to" buttons) and `ending_moves` (Reject/Withdraw buttons with `confirm()`, in the same form); final applications get a `data-final-message` alert and no form. The form's one `note` textarea posts with whichever button is clicked. `_panel_context` also passes `stage_changes`, which the panel draws as a "Stage history" timeline: an `applied` entry with `applied_on`, then each change (from → to, the mover's full name or username, date and time, note)
  - POST `application_move` (`/applications/<pk>/move/`, both roles, fields `stage` and optional `note`, filters in its query string): see the HTMX convention below
  - Test hooks: `data-application-row`, `data-panel`, `data-panel-field="..."`, `data-step`/`data-step-state`, `data-other-application`, `data-move-form`, `data-move-note`, `data-move-to`, `data-end-to`, `data-final-message`, `data-move-error`, `data-timeline-entry` (`applied` or the `StageChange` pk), `data-timeline-note`
- **Shared templates**: `templates/base.html` (loads Tailwind and HTMX 2.0.4, vendored at `assets/js/htmx.min.js`; vendor JS, no CDNs), `app_base.html` (nav shell; pages fill `{% block content %}`), `registration/`, `403.html`. `LoginRequiredMiddleware` guards every page.
- **Tests**: `tracker/tests/test_<area>.py`; stage moves in `test_moves.py`. `tracker/tests/html.py`'s `marked(response, attr)` returns `(value, attrs, text)` per element carrying `attr` (filter on the value when an attribute like `aria-current` repeats). `conftest.py` fixtures: `admin_user`, `staff_user`, `admin_client`, `staff_client`, `candidate`, `open_job`, `closed_job`, `TEST_PASSWORD`, and `make_application(stage=..., candidate=..., job=...)`. That one calls `create_application` (so record applications before closing a job), then one `move_application` by `staff_user`, so its applications already have `StageChange` rows. Module-only fixtures stay put until a second module needs them (`skill` in test_skills).

## Conventions and gotchas

- Status-only services (`close_job`, `reopen_job`) set the field and `save(update_fields=[..., "updated_at"])`, leaving other fields and M2M untouched. Use the same shape for archive/unarchive.
- Services raise `ValidationError` subclasses that carry context (e.g. `DuplicateCandidateEmail.existing`, `SkillInUse.job_count`, `InvalidStageMove.to_stage`).
- Editable fields are tuples in `services.py` (`CANDIDATE_FIELDS`, `JOB_FIELDS`, `APPLICATION_FIELDS`) used as `ModelForm.Meta.fields`, so views call `services.create_x(**form.cleaned_data)`. M2M values are `.set(...)` inside the service's `@transaction.atomic`; `update_job(skills=None)` leaves skills alone.
- `ModelForm.is_valid()` checks model constraints first, so a uniqueness rule needing a friendly error goes in the form's `clean_<field>`, calling the service check (`CandidateForm.clean_email`). When the view supplies a related object (e.g. `ApplicationForm`'s candidate), limit choices with a service queryset and catch refusals with `form.add_error(None, error)`.
- Bind forms with `_form_data(request)` in `tracker/views.py`, not `request.POST or None`, which leaves an empty POST unbound with no errors.
- Admin-only views use `@admin_required` (`tracker/permissions.py`, 403 for Staff); hide their controls with `{% if user.is_admin %}`. Test both roles, GET and POST.
- Actions without a form page (skill delete, job close/reopen; later archive) are `@require_POST` views (under `@admin_required`) triggered by an inline `<form method="post">`, with `confirm()` for destructive ones. They flash a message and redirect.
- HTMX actions (stage moves, including Reject/Withdraw; later reopen): the form has both `action` and `hx-post` plus `{% csrf_token %}`. With `HX-Request` the view renders a partial (panel + `_row.html` with `oob=True`, `id="application-row-<pk>"`); refusals render in place at status 200, since HTMX skips 4xx swaps by default. Without HTMX it flashes and redirects. Partial links use the full `{% url %}` path plus `filter_query`, never a bare `?…`. Tests pass `headers={"HX-Request": "true"}`.
- List filters come from the query string. Unknown values fall back to the default, and the view passes the cleaned value back so the active tab or `<option selected>` matches.
- Case-insensitive uniqueness uses `UniqueConstraint(Lower(...))` plus an `__iexact` service check. Candidate emails are lowercased; skill names keep their capitalization (whitespace collapsed).
- URL names are `<model>_<action>` (jobs use `job_`); templates go in `tracker/templates/tracker/<area>/{list,detail,form}.html`, partials start with `_`.
- Form templates render fields by hand with DaisyUI classes (see `jobs/form.html`), with errors in `<span data-field-error="...">`. Mark values tests need with `data-` attributes rather than loose text matches. After a successful POST, redirect; pages receiving messages include `tracker/_messages.html`.
- Tests: flash messages are auto-escaped, so compare against `django.utils.html.escape(...)`. Keep wording a test asserts is *absent* out of other UI text (e.g. `confirm()` prompts). Compare dates with `dateformat.format(d, "M j, Y")` (`strftime("%-d")` fails on Windows). For "no data changed", compare `StageChange` pks before and after rather than asserting none exist, since fixtures write some.
- Ruff's `DJ` rules enforce model member order: `Meta`, `__str__`, `get_absolute_url`, then custom methods. After a migration, run `migrate` before checking pages by hand.
- File editing: use Edit/Write, or one shell heredoc per command; never chain two heredocs, and never run a command that reads stdin (a bare `cat > file`), which hangs the shell. For scripted edits, save a script to the scratchpad and run it with `uv run python`, passing `encoding="utf-8", newline="\n"`. `sed` mangles quotes inside Python strings.
- Workflow: one plan phase per `/implement` session (TDD for up to 3 behaviors, stopping for approval at each step), then `PROMPTS.md`, commit, push. For RED to fail on an assertion, first add the URL, a placeholder view/service, and any new exception classes. Skip TDD for behaviors an existing pattern settles or the current code already passes (they can't start RED); test those normally.

## References

- PRD: `prd/applicant-tracking-system.md`; plan (phases): `plans/applicant-tracking-system.md`. Prototypes (throwaway, don't promote): `prototypes/`; original brief: `project-idea.md`
