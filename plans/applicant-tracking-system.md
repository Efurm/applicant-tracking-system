# Plan: Applicant Tracking System

> Source PRD: `prd/applicant-tracking-system.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Stack**: Python, Django, SQLite, managed by uv. Tailwind CSS + DaisyUI via django-tailwind-cli. HTMX for partial updates. Ruff for lint/format. pytest + pytest-django for tests.
- **Owning apps**:
  - `accounts` — only the custom `User` model. Present in the very first migration; `AUTH_USER_MODEL` points to it.
  - `tracker` — all hiring models, views, forms, templates, and a **services module** holding every business rule. Views stay thin; services raise validation errors that views turn into user-facing messages.
- **Models**:
  - `User(AbstractUser)` + `role` choice (Admin, Staff). Admins also get `is_staff` (Django admin access); Staff do not. Deactivation uses `is_active`; users are never deleted.
  - `Candidate` — first/last name, email (unique, case-insensitive), phone, LinkedIn/portfolio URL, resume URL, notes, archived flag, timestamps.
  - `Skill` — name (unique, case-insensitive).
  - `JobOpening` — title, department, location, employment type (Full-time/Part-time/Contract/Internship), description, status (Open/Closed), M2M to `Skill`, timestamps.
  - `Application` — FK `Candidate` (PROTECT), FK `JobOpening`, DB unique constraint on (candidate, job opening), source (Company Website/Job Board/Referral/Other), source details, current stage (default Applied), applied date, timestamps.
  - `StageChange` — FK `Application`, from-stage, to-stage, FK `User` (PROTECT), timestamp, optional note; ordered by time.
- **Stages**: pipeline Applied → Screening → Interview → Final Review → Offer → Hired. In-progress: Applied–Offer. Final: Hired, Rejected, Withdrawn. One "allowed next stages (stage, user)" function drives both UI and validation; one "move application" service performs every stage change transactionally and writes a `StageChange`.
- **URLs** (app-namespaced `tracker:`, integer pks):
  - `/candidates/`, `/candidates/new/`, `/candidates/<pk>/`, `/candidates/<pk>/edit/`, plus apply/archive/unarchive/delete actions under `/candidates/<pk>/`
  - `/jobs/`, `/jobs/new/`, `/jobs/<pk>/`, `/jobs/<pk>/edit/`, plus close/reopen actions under `/jobs/<pk>/`
  - `/skills/` (Admin only) with create/edit/delete beneath it
  - `/applications/` — the workspace; filters in the query string (`job`, `stage`, `q`, selected application)
  - `/applications/<pk>/move/` — HTMX stage-move endpoint (POST)
  - Django built-in auth views for login/logout; `/admin/` for user management
- **Auth**: every app page requires login. Shared mixins/helpers guard Admin-only views (by `role`); templates hide Admin-only controls from Staff. The server always re-checks.

---

## Phase 1: Project skeleton and authentication

**User stories**: 1, 2, 3, 4, 5, 6

### What to build

A runnable Django project managed by uv with Ruff and pytest configured, the `accounts` app with the custom `User` (role field) in its initial migration, and the `tracker` app. A shared DaisyUI page shell with navigation (Workspace, Candidates, Job Openings, Skills for Admins, current user, logout). Styled login and logout pages. A login-required placeholder home page. The `User` model registered in the Django admin with its role editable, so Admins can create and deactivate accounts. The first Admin is created via `createsuperuser`.

### Acceptance criteria

- [ ] `uv run` starts the dev server; `uv run pytest` and `uv run ruff check` pass
- [ ] Initial migration of `accounts` creates the custom `User` with a `role` field
- [ ] Anonymous requests to any app page redirect to the login page
- [ ] A user can log in and log out; the nav shows the current user
- [ ] The Skills nav link is visible only to Admins
- [ ] Users (with role) can be created and deactivated in the Django admin; a deactivated user cannot log in
- [ ] Shared test fixtures exist for an Admin user and a Staff user

---

## Phase 2: Candidates — create, view, edit, list, search

**User stories**: 8, 9, 10, 11, 13

### What to build

The `Candidate` model and pages to create, view, edit, and list candidates, with a search box on the list. Email uniqueness is case-insensitive at the database level; a duplicate produces a form error linking to the existing candidate. Creating a candidate redirects to their detail page. Both roles can do all of this.

### Acceptance criteria

- [ ] A candidate can be created with all PRD fields; only first name, last name, and email are required
- [ ] Creating redirects to the candidate's detail page
- [ ] A duplicate email in any capitalization is refused with a link to the existing record; the DB constraint also blocks it
- [ ] Candidates can be edited at any time
- [ ] The candidate list supports search by name/email
- [ ] Tests cover the case-insensitive constraint, the duplicate form error, and login-required access

---

## Phase 3: Skills (Admin-only)

**User stories**: 7, 34, 35

### What to build

The `Skill` model and Admin-only pages to list, create, and rename skills. Names are unique case-insensitively. This phase establishes the reusable Admin-only guard and the pattern for hiding Admin controls in templates.

### Acceptance criteria

- [ ] Admins can list, create, and rename skills
- [ ] "Python" and "python" cannot both exist (form error + DB constraint)
- [ ] Staff are refused (403 or redirect) on every skill view, and see no skill controls
- [ ] Tests cover the Admin guard for both roles and the uniqueness constraint

---

## Phase 4: Job openings with skills

**User stories**: 22, 23, 24, 25, 36, 37, 38, 39

### What to build

The `JobOpening` model with its M2M to `Skill`. Admin-only create and edit pages with a multi-select of shared skills. A job list (all users) filterable by Open/Closed, and a job detail page showing details and skills. Skill deletion is added and refused while any job uses the skill.

### Acceptance criteria

- [ ] Admins can create and edit jobs with all PRD fields and multiple skills
- [ ] The same skill can be attached to many jobs
- [ ] Staff can view the list and detail pages but are refused on create/edit and see no such controls
- [ ] The job list filters by Open/Closed
- [ ] Deleting a skill in use is refused with a clear message; an unused skill can be deleted (Admin only)
- [ ] Tests cover the skill-delete service rule and the job view permissions

---

## Phase 5: Closing and reopening jobs

**User stories**: 26, 27, 30, 31

### What to build

Admin-only close and reopen actions on the job detail page, backed by services. Closing is always allowed. A closed job is clearly labeled "Closed to new applicants" on its list and detail pages.

### Acceptance criteria

- [ ] Admins can close an open job and reopen a closed one
- [ ] Staff do not see the actions and are refused if they POST directly
- [ ] Closed jobs display "Closed to new applicants"
- [ ] Tests cover the close/reopen services and permissions; shared fixtures exist for an open job and a closed job

---

## Phase 6: Recording applications

**User stories**: 15, 29, 40, 41, 42, 43, 44, 45

### What to build

The `Application` model and a create-application service. An "Apply to a job" action on the candidate page opens a form whose job choices are limited to open jobs the candidate hasn't applied to, with source and source details. New applications start at Applied with the applied date set automatically. The service refuses closed jobs and duplicates (also enforced by the DB unique constraint). The candidate page lists all of the candidate's applications with job and current stage.

### Acceptance criteria

- [ ] An application can be recorded from the candidate page; it starts at Applied with today's date
- [ ] The form offers only open, not-yet-applied jobs
- [ ] The service refuses a closed job and a duplicate even when the form is bypassed; the DB constraint blocks duplicates
- [ ] A candidate can apply to several different jobs
- [ ] The candidate page lists all their applications
- [ ] Tests cover the service rules, the form's job choices, and the DB constraint; a fixture creates an application at a given stage

---

## Phase 7: Applications workspace (read-only)

**User stories**: 46, 47, 48, 49, 50

### What to build

The `/applications/` workspace using the prototype's list + detail layout. On the left, a list of applications across all jobs, filterable by job and stage (defaulting to in-progress), with candidate-name search, all driven by URL query parameters. Selecting an application shows a detail panel: candidate contact info, job, job status, source, applied date, a stage progress tracker, and links to the candidate's other applications. No move controls yet.

### Acceptance criteria

- [ ] With no parameters the list shows only in-progress applications across all jobs
- [ ] Job, stage, and name-search filters work and are reflected in, and restored from, the URL
- [ ] Selecting an application shows the detail panel with all listed fields and a progress tracker
- [ ] The panel lists the candidate's other applications, each linking to that application in the workspace
- [ ] Tests cover each filter, the in-progress default, and search

---

## Phase 8: HTMX forward stage moves

**User stories**: 28, 51, 52, 53, 54, 56, 62, 64

### What to build

The `StageChange` model, the "allowed next stages" function (forward moves only for now), and the "move application" service, which validates, updates the stage, and writes a `StageChange` (from, to, user, timestamp) in one transaction. The detail panel shows one button per allowed forward stage. Clicking it sends an HTMX POST to the move endpoint. The endpoint returns the re-rendered panel plus an out-of-band update of that application's list row, with no full page reload. Invalid moves (backward, same stage, not allowed) are refused server-side with an error rendered in place and no data changed. Moves work the same on closed jobs.

### Acceptance criteria

- [ ] From an in-progress stage, only later pipeline stages are offered; skipping is allowed
- [ ] A move updates the stage and writes a `StageChange` with the correct from, to, and user
- [ ] The HTMX response is a partial (not a full page) containing the panel and an out-of-band list row
- [ ] Backward or otherwise disallowed moves POSTed directly are refused with a message and leave data unchanged
- [ ] Applications on closed jobs can be moved normally
- [ ] Tests cover allowed-next-stages for every in-progress stage, the move service, and the HTMX endpoint (success and refusal)

---

## Phase 9: Ending applications — Rejected, Withdrawn, and final lock

**User stories**: 55, 57

### What to build

Extend the allowed-next-stages function so every in-progress stage also offers Rejected and Withdrawn, and so final stages (Hired, Rejected, Withdrawn) offer no moves. The detail panel shows Reject/Withdraw controls for in-progress applications and "final" messaging (no move buttons) for final applications. The server refuses any move out of a final stage.

### Acceptance criteria

- [ ] Rejected and Withdrawn are offered and accepted from every in-progress stage
- [ ] Hired, Rejected, and Withdrawn offer no moves; the panel shows final messaging
- [ ] A direct POST to move out of a final stage is refused with a message, data unchanged
- [ ] Tests cover allowed-next-stages for every stage (Staff role) and refusal of moves from final stages

---

## Phase 10: Move notes and stage-history timeline

**User stories**: 61, 63

### What to build

An optional note field alongside the move controls, saved on the `StageChange`. The detail panel shows the application's stage history as a chronological timeline (from → to, who, when, note), starting with the application date. The timeline refreshes as part of the HTMX move response.

### Acceptance criteria

- [ ] A move can include an optional note, stored on the `StageChange`
- [ ] The panel shows a timeline beginning with the application date and listing every stage change with user, time, and note
- [ ] After an HTMX move, the timeline includes the new entry without a full reload
- [ ] Tests cover the note being saved and the timeline appearing in the panel partial

---

## Phase 11: Admin reopen of final applications

**User stories**: 58, 59, 60

### What to build

Extend the allowed-next-stages function so that for an Admin, a final application can move back to any in-progress stage. It goes through the same move service and writes a `StageChange`. Admins see "Reopen" options on final applications; Staff still see final messaging. Reopening is refused if the candidate is archived and allowed on closed jobs. Reopens appear in the timeline.

### Acceptance criteria

- [ ] Admins see and can use reopen options to any in-progress stage on a final application
- [ ] Staff do not see reopen options and are refused on a direct POST
- [ ] Reopen is refused for an archived candidate (testable by setting the archived flag directly until Phase 12)
- [ ] Reopen works on closed jobs
- [ ] The reopen is recorded as a `StageChange` and shown in the timeline
- [ ] Tests cover allowed-next-stages for every stage under both roles, plus the reopen rules

---

## Phase 12: Archiving and deleting candidates

**User stories**: 12, 14, 16, 17, 18, 19, 20, 21

### What to build

Admin-only archive, unarchive, and delete actions on the candidate page, backed by services. Archive is refused while the candidate has any in-progress application. Delete is refused if the candidate has any applications, with a suggestion to archive instead (also blocked at the DB level by PROTECT). The candidate list hides archived candidates by default and has a "show archived" toggle. The create-application service and the apply action refuse archived candidates.

### Acceptance criteria

- [ ] Admins can archive (when no applications are in progress), unarchive, and delete (when there are no applications)
- [ ] Refusals show clear messages; the delete refusal suggests archiving
- [ ] Staff do not see these actions and are refused on direct POSTs
- [ ] The candidate list hides archived candidates by default; the toggle shows them
- [ ] Archived candidates cannot receive new applications
- [ ] Tests cover each service rule, the list toggle, and the permissions; a fixture exists for an archived candidate

---

## Phase 13: Job stage counts

**User stories**: 32, 33

### What to build

On the job detail page, a DaisyUI stats summary showing how many of the job's applications are in each of the eight stages. Each count links to the workspace filtered to that job and stage.

### Acceptance criteria

- [ ] Counts are correct for all eight stages, including zeros
- [ ] Each count links to `/applications/` with the matching job and stage query parameters, and the workspace honors them
- [ ] Tests cover the counts and the generated URLs

---

## Phase 14: Demo data command and README

**User stories**: 65, 66, 67, 68

### What to build

A management command that loads realistic demo data through the service functions: demo Admin and Staff logins, about 5 jobs (one closed), about 15 skills, about 20 candidates (one archived), and about 30 applications across every stage with realistic history, including at least one Admin reopen. It is safe to re-run (it removes its own previous demo data, or refuses if non-demo data is present). The README documents setup, the command, and the demo credentials, marked as local-development only.

### Acceptance criteria

- [ ] One command populates the database with the data described above
- [ ] All stage changes are created through the move service, so every `StageChange` is valid
- [ ] Running the command twice succeeds without duplicating or corrupting data
- [ ] The README lists setup steps and demo credentials with a local-only warning
- [ ] Tests run the command, check that the data obeys the rules, and run it twice
