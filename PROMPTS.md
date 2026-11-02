# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

---

## 2026-11-02 — Implemented Phase 14: the seed_demo command and README (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 14`
2. `yes, go ahead` (the re-run policy and the three TDD behaviors: a fresh run follows the rules, running twice doesn't duplicate, refusal when non-demo data exists)
3. `yes, implement it to pass` (behavior 1)
4. `yes move on to behavior 2`
5. `yes implement it to pass` (behavior 2, accepting an IntegrityError crash as its RED)
6. `yes move on to behavior 3`
7. `yes implement it to pass` (behavior 3)
8. `yes go ahead with the rest of the phase`

### Summary
- **Outcome:** `uv run python manage.py seed_demo` loads a demo through the services: logins `demo-admin` and `demo-staff`, 15 skills, 5 jobs (Customer Support Intern closed, with applications still in progress), 20 candidates (Quinn Foster archived), and 30 applications covering all eight stages, with 49 stage changes that include notes and two Admin reopens.
  - **Command:** data tables (`USERS`, `SKILLS`, `JOBS`, `CANDIDATES`, `APPLICATIONS` with `(stage, mover, note)` moves) are played through `create_skill`, `create_job`, `create_candidate`, `create_application`, and `move_application` in one transaction, then `close_job` and `archive_candidate` last, since the services refuse those earlier. Users are the only rows made without a service (`create_user`).
  - **Re-run policy:** a mix of the PRD's two options. If any candidate, job, or skill isn't one of the command's own (`@demo.example.com` emails, the `JOBS` titles, the `SKILLS` names), it raises `CommandError` and changes nothing. Otherwise it deletes the old demo data in `PROTECT` order (applications with their stage changes, candidates, jobs, skills, demo users) and loads it fresh. Real users are never touched.
  - **Docs:** the README has a "Demo data (local development only)" section with the command, the credentials table, a warning, and the re-run policy. CLAUDE.md marks all 14 phases done.
  - **Tests:** 207 pass (up from 202): a fresh run's counts, roles, logins, all eight stages, a valid stage-history chain for every application (each step allowed for its mover), an Admin reopen, and a note; two runs giving identical counts while keeping a real user; and a refusal, with nothing changed, for a non-demo candidate, job, or skill. The command was also run twice on the empty dev database (backed up first), and its refusal was checked by hand on a scratch copy.
- **Deviations:** None. The user approved the proposed re-run policy and each TDD step as proposed.
- **Sideways:**
  - Behavior 2's first failure was an `IntegrityError` (duplicate `demo-admin`), not an assertion. The crash was the missing behavior itself, and making it fail on an assertion would have meant writing the reset first or weakening the test. The agent said so, and the user accepted it as RED.
  - Known limits: every application is dated the day the command runs (the services take no dates), and a hand-made job with exactly a demo title would be treated as demo data.

---

## 2026-11-02 — Implemented Phase 13: job stage counts (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 13`
2. `approved,go ahead` (the two TDD behaviors: `services.stage_counts(job)`, and the job page's linked counts)
3. `go ahead` (approved the RED test for behavior 1)
4. `go ahead` (move on to behavior 2)
5. `go ahead` (approved the RED test for behavior 2)
6. `go ahead` (round-trip test, feedback loops, and finishing the phase)

### Summary
- **Outcome:** Each job opening's page now has an "Applications by stage" DaisyUI stats grid. It shows one count per stage in pipeline order (zeros included and dimmed), and each count links to the workspace filtered to that job and stage.
  - **Service:** `services.stage_counts(job)` groups the job's applications with `values("stage").annotate(Count("pk"))`, clearing the model's default ordering so the grouping works, then fills in every `Stage` in order.
  - **View and template:** `job_detail` passes `stage_counts`. `jobs/detail.html` renders `<a data-stage-count="<value>" class="stat">` links to `tracker:application_workspace?job=<pk>&stage=<value>`, laid out in a 2-column/4-column grid so all eight fit the page width.
  - **Tests:** 202 pass (up from 199): the service counts (every stage, zeros, other jobs excluded), the page's labels, counts, and URLs for all eight stages, and a round-trip test that follows the Hired link and gets only that job's hired application. CLAUDE.md was updated, with Phase 14 listed as next.
- **Deviations:** None. The user approved each TDD step as proposed. The agent picked two behaviors instead of three, because the workspace already honored both filters and had tests.
- **Sideways:**
  - The first draft of the service test applied to `closed_job` for the "other job" case. `create_application` refused that, so the test errored instead of failing on an assertion. It was switched to a second open job before the RED step was shown.
  - Ruff flagged the import order after the `marked` import was added with `sed`. `ruff check --fix` sorted it.

---

## 2026-11-02 — Implemented Phase 12: archiving and deleting candidates (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 12`
2. `yes, go ahead` (the three TDD behaviors: archive refused while in progress, delete refused with applications, `create_application` refuses archived candidates)
3. `yes implement it to pass` (behavior 1)
4. `yes, move on to cycle 2`
5. `yes implement it to pass` (behavior 2)
6. `yes move on to cycle 3`
7. `yes impmlement it to pass` (behavior 3, including the "they can't receive new applications" wording)
8. `yes, go ahead with the rest of the phase`

### Summary
- **Outcome:** Admins can archive, unarchive, and delete candidates. Archived candidates are hidden from the list by default and can't receive new applications.
  - **Services:** `archive_candidate` raises `CandidateHasApplicationsInProgress` while any application is in progress. `unarchive_candidate` clears the flag. Both save only `archived` and `updated_at`. `delete_candidate` raises `CandidateHasApplications` (its message ends "Archive them instead.") whenever any application exists. `create_application` raises `CandidateArchived` first. The class now takes an optional `consequence`, so it reads "…so they can't receive new applications" here and keeps the reopen wording by default. `jobs_open_to` returns nothing for an archived candidate, and `search_candidates` takes `include_archived`.
  - **Views and templates:**
    - Admin-only `@require_POST` actions `candidate_archive`, `candidate_unarchive`, and `candidate_delete`, triggered by inline forms on the candidate page (Archive and Delete have `confirm()` prompts). A successful delete redirects to the list.
    - The candidate page shows an Archived badge and message and hides "Apply to a job" while archived. The apply view flashes and redirects an archived candidate.
    - The list has a "Show archived" checkbox (`?archived=1`) with badges, and it now includes the messages partial.
    - The workspace panel hides Admin reopen buttons for an archived candidate and says why.
  - **Tests:** 199 pass (up from 168). They cover each service rule, Staff refusals (403 on GET and POST) and POST-only actions, button visibility for both roles, the Admin flows with their messages, the list toggle with search, the apply page and form for archived candidates, and the panel. A new `archived_candidate` fixture was added, and the two Phase 11 tests in `test_moves.py` now archive through the service. CLAUDE.md was updated, with Phase 13 listed as next.
- **Deviations:** None. The user approved each TDD step as proposed, including the apply-refusal wording.
- **Sideways:**
  - The agent twice left a stray `... if False else None` line in a test it was writing. Both were removed before the tests were run or shown.
  - The first version of the `confirm()` prompts contained a bare apostrophe inside a JavaScript string, which would have broken the prompt. They were reworded to "cannot".
  - The Admin delete test failed at first because the candidate list didn't include `_messages.html`, so the "Deleted" flash never showed. This was a real gap, fixed in the template.

---

## 2026-11-02 — Implemented Phase 11: Admin reopen of final applications (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 11`
2. `approved, do the archival refusal in phase 11` (the three TDD behaviors, plus where the archived-candidate reopen refusal belongs)
3. `go ahead` (RED test for behavior 1)
4. `go ahead` (move on to behavior 2)
5. `go ahead` (RED test for behavior 2)
6. `go ahead` (move on to behavior 3)
7. `go ahead` (RED test for behavior 3, including the Admin final-message wording)
8. `go ahed` (implement behavior 3)
9. `go ahead` (end-to-end reopen test, then finish the phase)

### Summary
- **Outcome:** Admins can reopen Hired, Rejected, and Withdrawn applications to any in-progress stage. Staff still can't.
  - **Service:** `allowed_next_stages(stage, user)` returns `IN_PROGRESS_STAGES` from a final stage when `user.is_admin`, and nothing for Staff. `move_application` raises the new `CandidateArchived` (which carries `.candidate`) when a move out of a final stage meets an archived candidate. It re-reads `archived` from the database and changes nothing. Reopens on closed jobs work like any other move.
  - **View:** `application_move` catches `CandidateArchived` as well as `InvalidStageMove`, so the refusal renders in place (HTMX) or is flashed (no HTMX). `_panel_context` adds `reopen_moves` (every allowed move from a final stage). For final applications, `forward_moves` and `ending_moves` stay empty.
  - **Panel:** for Admins, final applications render the move form with its note field and a "Reopen to" group of `data-reopen-to` buttons. The final message there reads "As an Admin, you can reopen it to an in-progress stage." Staff keep "It is final, so it can't be moved." and get no form. Reopens get a timeline entry through the existing `StageChange` path.
  - **Tests:** 168 pass (up from 157). New tests cover:
    - Admin allowed-next-stages for every stage
    - the archived-candidate refusal in the service (all final stages) and over HTMX
    - Admin reopen buttons versus Staff final messaging (all final stages)
    - an Admin HTMX reopen with a note on a closed job, recorded as a `StageChange` and shown in the timeline and list row
  - CLAUDE.md's status, inventory, and test hooks were updated, and Phase 12 is listed as next.
- **Deviations:** The plan put the archived-candidate reopen refusal in Phase 11, but CLAUDE.md's notes deferred it to Phase 12. The agent recommended doing it now, and the user agreed. The user accepted the proposed Admin final-message wording without changes.
- **Sideways:**
  - Behavior 3's test first asked for both `admin_client` and `staff_client`. They share pytest-django's single `client`, so both were logged in as Staff, and the test stayed red after the code was written. The fix was a mechanical repair: one `client` is logged in as each role in turn. The original RED was still a real failure, since no `data-reopen-to` markup existed yet, though for a slightly different reason than first reported.
  - The first view test for the archived refusal compared against `escape(...)`, but `marked()` already unescapes text. It was a one-line mechanical fix.
  - A `sed` attempt to add an import didn't match across lines and changed nothing. The import was added with Edit instead.

---

## 2026-11-02 — Implemented Phase 10: move notes and the stage-history timeline (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 10`
2. `go ahead` (the three TDD behaviors: the service stores a note, the panel shows a timeline, an HTMX move with a note returns the new timeline entry)
3. `go ahead` (RED test for behavior 1)
4. `go ahead` (move on to behavior 2)
5. `go ahead` (RED test for behavior 2, showing the mover's full name with a username fallback)
6. `go ahead` (move on to behavior 3)
7. `go ahead` (RED test for behavior 3)
8. `go ahead` (feedback loops, then finish the phase)

### Summary
- **Outcome:** Stage moves can carry an optional note, and the detail panel shows the application's stage history.
  - **Model:** `StageChange.note` (blank allowed), migration `0006_stagechange_note`.
  - **Service:** `move_application(application, to_stage, user, note="")` stores the note, stripped of surrounding whitespace.
  - **View:** `application_move` passes `request.POST.get("note", "")` to the service. `_panel_context` adds `stage_changes`, so both the workspace page and the HTMX move response render the timeline.
  - **Panel:** the move form has one optional "Note" textarea (`data-move-note`) shared by the forward, Reject, and Withdraw buttons. A "Stage history" section uses DaisyUI's vertical timeline. It starts with an `applied` entry showing the application date, then lists each change: from → to, who made it (full name, or username if they have none), the date and time, and the note if there is one. Hooks are `data-timeline-entry` and `data-timeline-note`.
  - **Tests:** 157 pass (up from 152). New tests cover:
    - the note being stored, and blank by default
    - the timeline's order and contents on a workspace GET
    - an HTMX move with a note saving it and returning the new entry
    - the form having a single optional note field
    - a non-HTMX move saving its note
  - CLAUDE.md's status, inventory, and test hooks were updated, and Phase 11 is listed as next.
- **Deviations:** None. The user approved every proposal as offered. The agent flagged two extras that go beyond the tests (stripping notes, and showing the time of each move as well as the date), and the user kept both.
- **Sideways:**
  - A foreground run of `test_moves.py` hit the 2-minute tool timeout and moved to the background, where it passed. Later module runs were started in the background from the outset.
  - `ruff format` reflowed `test_moves.py` while the full suite was running. It was a formatting-only change, and Ruff then passed.

## 2026-11-02 — Implemented Phase 9: Rejected, Withdrawn, and the final lock (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 9`
2. `yes` (the two TDD behaviors: `allowed_next_stages` for every stage as Staff, and the panel's Reject/Withdraw controls vs. final messaging)
3. `yes` (RED test for behavior 1)
4. `yes` (move on to behavior 2)
5. `yes` (RED test for behavior 2, including dropping one assertion from an existing workspace test)
6. `yes` (finish the rest of the phase normally)

### Summary
- **Outcome:** In-progress applications can now be ended as Rejected or Withdrawn, and final applications are locked.
  - **Service:** `services.ENDING_STAGES = (Rejected, Withdrawn)`. `allowed_next_stages` returns the later pipeline stages plus `ENDING_STAGES` from any in-progress stage, and nothing from Hired, Rejected, or Withdrawn. `move_application` validates against it, so the server accepts endings and refuses every move out of a final stage with `InvalidStageMove`.
  - **Panel:** `_panel_context` splits the allowed moves into `forward_moves` and `ending_moves`. In-progress applications show the "Move to" buttons plus an "End this application" group with Reject (red) and Withdraw (amber) buttons. Each asks for `confirm()` and shares the existing HTMX move form. Final applications (now including Hired) show "This application ended as X. It is final, so it can't be moved." (`data-final-message`) and no move form.
  - **Fixture:** `make_application` no longer sets Rejected/Withdrawn directly. Every non-Applied stage is reached with one `move_application` by `staff_user`.
  - **Tests:** 152 pass (up from 118). New tests cover:
    - `allowed_next_stages` for all eight stages as Staff, plus an Admin-matches-Staff guard for in-progress stages
    - the panel's ending controls and final message for each final stage
    - rejecting or withdrawing from every in-progress stage, with a `StageChange` written
    - an HTMX reject that returns the final panel and row
    - direct POSTs out of each final stage refused with a message and no data change
  - CLAUDE.md's status, inventory, and test hooks were updated, and Phase 10 is listed as next.
- **Deviations:**
  - The agent proposed two TDD behaviors instead of three. "A direct POST out of a final stage is refused" already passed before this phase, so it couldn't start RED; it was tested normally instead.
  - Behavior 2's approved test meant dropping one assertion from the Phase 7 test `test_the_tracker_for_final_stages`, which had said Hired shows no "ended as" message. The agent flagged this before the user approved.
- **Sideways:**
  - After behavior 1 went GREEN, `test_the_panel_offers_one_move_button_per_allowed_stage` failed, because Rejected and Withdrawn appeared as extra forward buttons. The agent reported this as expected, and behavior 2's separate `data-end-to` controls fixed it without changing that test.
  - The full suite now takes about 4 minutes (it was about 3.5). CLAUDE.md was updated to match.
  - CLAUDE.md already had uncommitted edits from the user (a tighter Commands and Status section) when the session started. They were kept and committed with this phase's updates.

## 2026-11-02 — Implemented Phase 8: HTMX forward stage moves (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 8`
2. `yes` (the three TDD behaviors: `allowed_next_stages` offers only later pipeline stages, `move_application` updates the stage and writes a `StageChange` or refuses with no change, and the HTMX endpoint returns the panel plus an out-of-band row or refuses in place)
3. `yes` (RED test for behavior 1)
4. `yes` (move on to behavior 2)
5. `yes` (RED tests for behavior 2)
6. `yes` (move on to behavior 3)
7. `yes` (RED tests for behavior 3)
8. `yes` (finish the rest of the phase normally)

### Summary
- **Outcome:** Applications can now move forward through the pipeline from the workspace's detail panel, without a full page reload.
  - **Model:** a new `StageChange` (migration `0005`) records the application, `from_stage`, `to_stage`, `changed_by` (`PROTECT`), and `changed_at`, ordered by time.
  - **Services:**
    - `allowed_next_stages(stage, user)` returns the later `PIPELINE_STAGES`, so skipping ahead is allowed. It drives both the panel's buttons and validation.
    - `move_application(application, to_stage, user)` re-reads the stage with `select_for_update`. It either raises `InvalidStageMove` or saves the stage and writes a `StageChange`, in one transaction. Moves on closed jobs work the same.
  - **Endpoint:** POST `application_move` at `/applications/<pk>/move/`, for both roles.
    - With HTMX, it returns `_move.html`: the panel plus the list row with `hx-swap-oob="true"`. Refusals show in `data-move-error` at status 200.
    - Without HTMX, it flashes a message and redirects back to the workspace.
    - The move form's URL carries the current filters.
  - **Other changes:**
    - HTMX 2.0.4 is vendored at `assets/js/htmx.min.js` and loaded in `base.html`.
    - `_workspace_filters` and `_panel_context` view helpers are shared by the workspace and the move endpoint.
    - The HTML test helper moved to `tracker/tests/html.py` (as `marked`).
    - `make_application` now reaches pipeline stages through `move_application`. Rejected and Withdrawn are still set directly until Phase 9.
    - CLAUDE.md's status and inventory were updated.
  - **Tests:** 118 pass, 21 of them new in `test_moves.py`. 3 behaviors were driven by TDD.
- **Deviations:** None. All three behaviors and their RED tests were approved unchanged. The agent stated these design choices before approval:
  - The `note` field is left out until Phase 10.
  - Refusals return 200 so HTMX swaps them in.
  - The move form posts a `stage` field.
- **Sideways:**
  - Before the behavior 2 RED run, the agent changed the refusal test to compare `StageChange` rows before and after the move instead of asserting the table is empty. Otherwise the test would have broken once `make_application` started writing `StageChange` rows.
  - A scaffolding command for behavior 3 hung because a stray `cat` waited on input. The agent stopped it, confirmed nothing had changed, and re-ran the edit as a script saved in the scratchpad.
  - One command chained two heredocs, which CLAUDE.md warns against. The agent checked the resulting test file and found it intact.

## 2026-11-02 — Implemented Phase 7: read-only applications workspace (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 7`
2. `yes` (the three TDD behaviors: the in-progress default across all jobs, the `job`/`stage`/`q` filters restored from the URL, and the detail panel for `?selected=<pk>` with the candidate's other applications)
3. `i approve` (RED test for behavior 1)
4. `yes` (move on to behavior 2)
5. `i approve` (RED test for behavior 2)
6. `yes` (move on to behavior 3)
7. `i approve` (RED test for behavior 3)
8. `yes` (finish the rest of the phase normally)

### Summary
- **Outcome:** The workspace is live at `/applications/` (`tracker:application_workspace`, both roles), laid out as the prototype's variant C list + detail.
  - **Filters:**
    - `filter_applications(job, stage, query)` is a new service. `stage` is a `Stage` value or `all`; blank or unknown means in-progress. Every word of `q` must match the first or last name.
    - The view drops unknown job and stage values and passes the cleaned values back, so the filter controls show them.
  - **Detail panel:**
    - `?selected=<pk>` opens it. It shows contact info, the job and its status, the source and details, the applied date, and the current stage.
    - The DaisyUI `steps` tracker comes from the new `Application.pipeline_progress()`.
    - It links to the candidate's other applications, keeping the current filters.
  - **New in `tracker/models.py`:** the module-level `PIPELINE_STAGES`, `IN_PROGRESS_STAGES`, and `FINAL_STAGES`, plus `Application.is_final`.
  - **Templates:** the panel and the list row are partials (`_panel.html`, `_row.html`, with `id`s ready for Phase 8's HTMX swaps).
  - **Other changes:** the Workspace nav link now points to the workspace, `make_application` moved to `conftest.py`, and CLAUDE.md's status and inventory were updated.
  - **Tests:** 97 pass, 11 of them new. 3 behaviors were driven by TDD.
- **Deviations:** None. All three behaviors and RED tests were approved unchanged. The agent made two design choices, both stated with the behavior 3 RED test before approval:
  - Nothing is auto-selected when `selected` is absent. The prototype picked the first row instead.
  - The other-application links keep the current filters, so the selected application may be missing from the list on the left.
- **Sideways:**
  - The first draft of test 1 used `make_application` on a closed job, which `create_application` refuses. The agent caught this before running it and recorded the applications before closing the job.
  - The first draft of test 3 used `strftime("%-d")`, which doesn't work on Windows. It was replaced with Django's `dateformat` before the RED run.
  - The panel links first used a bare `?…`. They were switched to the full `{% url %}` path the test expected.
  - Two of the follow-up (non-TDD) tests failed at first because of mistakes in the tests. One picked up the tracker's `aria-current="step"`. The other expected a `selected` attribute on the default "All jobs" option. Both tests were corrected; the app code didn't change.

## 2026-11-02 — Implemented Phase 6: recording applications (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 6`
2. `yes` (the three TDD behaviors: `create_application` refuses a closed job and a duplicate, the apply form offers only open not-yet-applied jobs, Staff apply from the candidate page and see the application listed)
3. `i approve` (RED test for behavior 1)
4. `yes` (move on to behavior 2)
5. `i approve` (RED test for behavior 2)
6. `yes` (move on to behavior 3)
7. `i approve` (RED test for behavior 3)
8. `yes` (finish the rest of the phase normally)

### Summary
- **Outcome:** A new `Application` model (migration `0004`). It has `candidate` and `job` foreign keys, both `PROTECT`, plus a unique (candidate, job) constraint, `ApplicationSource` and `Stage` choices, `source_details`, a `stage` that defaults to Applied, and an `applied_on` date that defaults to today. New services: `jobs_open_to(candidate)`, and `create_application`, which raises `JobClosedToApplicants` or `DuplicateApplication`. There is a new `ApplicationForm` and a `candidate_apply` view at `/candidates/<pk>/apply/` for both roles. If the service refuses, the view shows the refusal as a form error. The candidate page now has an "Apply to a job" button, a table of applications (job with a Closed badge where it applies, stage, source and details, applied date), and flash messages. The `candidate`, `open_job`, and `closed_job` fixtures moved to `conftest.py`. A `make_application(stage=...)` factory fixture lives in `test_applications.py`. There are 86 passing tests, 12 of them new; 3 behaviors were driven by TDD. CLAUDE.md's status, inventory, and gotchas were updated.
- **Deviations:** None from the recommendations; all three behaviors and RED tests were approved unchanged. The agent pointed out that test 3's `"Applied"` check is a loose text match and offered a tighter marker; the user approved it as written. The agent made the job foreign key `PROTECT` too, which the PRD doesn't require. Following the CLAUDE.md fixture convention, `make_application` stays in its test module for now rather than going in `conftest.py`, even though the plan calls for a shared fixture. The CLAUDE.md edits that were already uncommitted at the start of the session were committed along with this phase.
- **Sideways:** The first attempt to move the fixtures chained two heredocs with `||`. It sent the wrong input to Python and added only the import line to `conftest.py`. The agent noticed this in the diff stat and redid the move with a temporary script. The first run of test 1 failed with `AttributeError` (the exception classes didn't exist yet), not on an assertion. The agent added the classes without any checks to get a proper RED. Moving the fixtures left an unused `pytest` import in `test_jobs.py`, which Ruff caught and fixed.

## 2026-11-02 — Implemented Phase 5: closing and reopening jobs (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 5`
2. `yes` (the two TDD behaviors: an Admin closes and reopens a job from its page, and closed jobs are labeled "Closed to new applicants")
3. `i approve` (RED test for behavior 1)
4. `yes` (move on to behavior 2)
5. `i approve` (RED test for behavior 2)
6. `yes` (finish the rest of the phase normally)

### Summary
- **Outcome:** New services `close_job` and `reopen_job` set a job's status and save only `status` and `updated_at`. Closing is always allowed, and neither service touches other fields or skills. Admin-only, POST-only `job_close` and `job_reopen` views at `/jobs/<pk>/close/` and `/jobs/<pk>/reopen/` flash a message and redirect to the job page. The job page shows Admins a "Close job" button with a confirmation on open jobs, and a "Reopen job" button on closed jobs. Closed jobs read "Closed to new applicants" under their status badge on the list, and in an alert on the detail page that also says applicants in progress keep moving. There are 74 passing tests, 10 of them new; 2 behaviors were driven by TDD. CLAUDE.md's status and inventory were updated.
- **Deviations:** The agent proposed only two TDD behaviors instead of three, because Staff refusal is handled by the existing `@admin_required` pattern; it was tested normally instead. Both behaviors and both RED tests were approved unchanged. The `open_job` and `closed_job` fixtures already existed in `test_jobs.py` from Phase 4, and, per CLAUDE.md, they stay there until Phase 6 needs them in a second module. The CLAUDE.md edits that were already uncommitted at the start of the session were committed along with this phase.
- **Sideways:** Nothing broke. To make test 1 fail on an assertion rather than `NoReverseMatch`, the agent first added the URLs and placeholder views that redirected without changing anything. The open-job confirmation text was worded so that it doesn't contain "Closed to new applicants", which would have broken test 2's check that open jobs lack the label.

## 2026-11-02 — Implemented Phase 4: job openings with skills (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 4`
2. `yes` (the three TDD behaviors: skill delete refused while a job uses it, job list status filter, Admin creates a job with several shared skills)
3. `i approve` (RED test for behavior 1)
4. `yes` (move on to behavior 2)
5. `i approve` (RED test for behavior 2)
6. `yes` (move on to behavior 3)
7. `i approve` (RED test for behavior 3)
8. `yes` (finish the rest of the phase normally)

### Summary
- **Outcome:** A `JobOpening` model (migration `0003_jobopening`) with title, department, optional location, `EmploymentType` (Full-time/Part-time/Contract/Internship), description, `JobStatus` (Open/Closed, default Open), a many-to-many `skills` field (`Skill.job_openings`), and timestamps, ordered by title. New services: `create_job` and `update_job` save the job and its skills in one transaction; `filter_jobs` narrows by a valid status and otherwise returns all jobs; `delete_skill` raises `SkillInUse` (carrying the job count) while any job uses the skill. Pages: a job list for everyone with All/Open/Closed tabs driven by `?status=`; a job detail page showing details and skill badges; Admin-only create and edit forms with skills as checkboxes; and a POST-only, Admin-only Delete button with a confirmation on the skills list. The Job Openings nav link now works. There are 64 passing tests: 19 new, of which 3 behaviors were driven by TDD. CLAUDE.md's status, inventory, and gotchas were updated.
- **Deviations:** All three proposed TDD behaviors were approved unchanged. Before asking for approval of RED test 2, the agent added an assertion of its own that an unknown `?status=` value shows all jobs; the user approved it. Without asking, the agent made the job description required, made editing a job leave its status alone (close/reopen is Phase 5), and left job openings out of the Django admin to match Candidate and Skill, which aren't registered either. The CLAUDE.md edits that were already uncommitted at the start of the session were committed along with this phase.
- **Sideways:**
  - The first GREEN run of behavior 1 still failed: Django escapes the double quotes in flash messages as well as the apostrophe, so the literal `&#x27;` string in the approved test didn't match. As a mechanical repair, both message assertions now compare against `escape(...)`. A first `sed` attempt at that repair dropped the backslash before the apostrophe and caused a syntax error, which was fixed with the Edit tool. CLAUDE.md now notes the escaping gotcha.
  - The full test suite now takes about 110 seconds, mostly because each logged-in fixture hashes a password. It hasn't been sped up yet.

## 2026-11-02 — Implemented Phase 3: Admin-only skills (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 3`
2. `yes` (the single TDD behavior: only Admins can use the skill pages)
3. `i approve` (RED test for the Admin guard)
4. `yes` (finish the rest of the phase normally)

### Summary
- **Outcome:** A `Skill` model (migration `0002_skill`) with a unique constraint on `Lower("name")`, ordered by name without regard to case. New services `create_skill`, `rename_skill`, and `check_skill_name_is_free` raise `DuplicateSkillName`, and `SkillForm.clean_name` turns that into a field error such as `A skill named "Python" already exists.` A new `tracker/permissions.py` adds the reusable `@admin_required` decorator, which raises `PermissionDenied` (403) for non-Admins, and a styled `templates/403.html` shows the refusal. Admin-only DaisyUI pages list, create, and rename skills under `/skills/`, with success flash messages from a shared `tracker/_messages.html` include. The Admin-only Skills nav link now works. There are 45 passing tests: 13 new, of which 1 behavior (the Admin guard for both roles, GET and POST) was driven by TDD. CLAUDE.md was updated with the guard, the 403 page, and the messages include.
- **Deviations:** The agent proposed only one TDD behavior instead of three. Its reason was that case-insensitive uniqueness and renaming follow the pattern `Candidate` already set up and tested. The user approved this unchanged. Without asking, the agent chose to keep skill names in the capitalization the Admin typed (collapsing extra whitespace) instead of lowercasing them as candidate emails are, because a list of lowercase skill names would read badly. It also allowed renaming a skill to change only its own capitalization. The CLAUDE.md edits that were already uncommitted at the start of the session were committed along with this phase.
- **Sideways:**
  - A combined shell command that used a nested Python heredoc to edit `services.py` failed: Python on Windows wrote the file with CRLF line endings and a non-UTF-8 byte, which broke `makemigrations` with a `UnicodeDecodeError`. The file was restored with `git checkout` and the change redone with the Edit tool and a plain `cat >>` append.
  - One normal test first looked for an HTML-escaped apostrophe (`don&#x27;t`) on the 403 page. The template text isn't escaped, so the assertion was fixed to look for `don't`.

## 2026-11-02 — Implemented Phase 2: candidates create, view, edit, list, search (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 2`
2. `yes` (the three TDD behaviors: case-insensitive email constraint in the DB, duplicate-email form error linking to the existing candidate, list search by name/email)
3. `i approve` (RED test for behavior 1)
4. `yes` (move on to behavior 2)
5. `i approve` (RED test for behavior 2)
6. `yes` (move on to behavior 3)
7. `i approve` (RED test for behavior 3)
8. `yes` (finish the rest of the phase normally)

### Summary
- **Outcome:** A `Candidate` model (first/last name, email, phone, LinkedIn/portfolio URL, resume URL, notes, archived flag, timestamps) whose first migration includes a unique constraint on `Lower("email")`. A new `tracker/services.py` holds the rules: `create_candidate` and `update_candidate` lowercase the email and call `check_email_is_free`, which raises `DuplicateCandidateEmail` carrying the existing record, and `search_candidates` matches first name, last name, or email without regard to case. `CandidateForm.clean_email` turns the duplicate error into an Email-field error that links to the existing candidate, on both create and edit. DaisyUI pages for the list (with `?q=` search), create, detail, and edit live under `/candidates/`, and the nav's Candidates link now works. Creating a candidate redirects to their page. There are 32 passing tests: 20 new, of which 3 behaviors (7 test cases) were driven by TDD. CLAUDE.md's `tracker` description was updated.
- **Deviations:** All three proposed TDD behaviors and their RED tests were approved unchanged. Without asking, the agent left full-name search ("Jo Park") unsupported, since the plan only asks for name or email search. The CLAUDE.md edits that were already uncommitted at the start of the session were committed along with this phase.
- **Sideways:**
  - Behavior 1's migration was generated before the constraint existed, so the test could start RED. It was then deleted and regenerated so `0001_initial` creates the constraint directly.
  - Behavior 2's first draft used `errors["email"]`, which crashed with a `KeyError` instead of failing an assertion. It was changed to `errors.get("email", [])` before approval. The first fix also didn't work: catching the service error in the view never ran, because Django's `ModelForm` validates model constraints inside `is_valid()` and refused the form first with a generic non-field error. The check moved into `clean_email`, which calls the service.
  - During behavior 3, a combined shell script hung on a stray `cat > /tmp/x` waiting for input. It was stopped, the partly applied edits were checked, and the rest were reapplied.
  - A normal test caught a real bug: `request.POST or None` treats an empty POST as no submission, so a blank form came back with no errors. Forms are now bound on every POST.
  - Ruff's DJ012 rule required `get_absolute_url` to come before the `full_name` property.

## 2026-11-02 — Implemented Phase 1: project skeleton and authentication (TDD)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 1`
2. `i approve them` (the three TDD behaviors: anonymous redirect to login, Admin-only Skills nav link, login shows the user / deactivated user refused)
3. `i approve` (RED test for behavior 1)
4. `yes` (move on to behavior 2)
5. `i approve` (RED test for behavior 2)
6. `yes` (move on to behavior 3)
7. `i approve` (RED test for behavior 3)
8. `yes` (finish the rest of the phase normally)

### Summary
- **Outcome:** A uv-managed Django 6.1 project (`config`) with `accounts` and `tracker` apps. `accounts.User` extends `AbstractUser` with a `role` field (Admin/Staff, default Staff) in its initial migration. The role drives Django's flags: Admins get `is_staff` and `is_superuser` so they can manage users at `/admin/`, Staff get neither, and `createsuperuser` produces an Admin. The User admin exposes role and active status and forbids deleting users. `LoginRequiredMiddleware` protects every page. DaisyUI-styled login, logged-out, and placeholder home pages share a nav shell (Workspace, Candidates, Job Openings, Admin-only Skills, current user and role, logout). Tailwind + DaisyUI (corporate theme) build through django-tailwind-cli. Ruff and pytest are configured; shared fixtures provide `admin_user`, `staff_user`, `admin_client`, and `staff_client`. There are 12 passing tests: 3 driven by TDD and 9 written normally for the User model, admin, and logout. The README gained setup steps.
- **Deviations:** All three proposed TDD behaviors and their RED tests were approved unchanged. The agent chose, without asking, to give Admins `is_superuser` as well as `is_staff`. The PRD only mentions the staff flag, but with that flag alone an Admin can open `/admin/` yet has no permission to manage users there.
- **Sideways:**
  - The agent had already added `LoginRequiredMiddleware` and the "Signed in as" nav text while scaffolding, which would have made tests 1 and 3 pass without ever failing. It removed both before writing those tests so each started RED on an assertion, then restored them as the fix.
  - The deactivated-user half of test 3 needed no new code; it locks in Django's built-in refusal of inactive accounts.
  - `ruff check` flagged unused imports in Django's generated stub files, which were removed or emptied.
  - DaisyUI 5 does not ship the `corporate` theme by default, so it was enabled in `frontend/source.css`.
  - Nav links other than the home link point to `#` until their pages exist in later phases.

## 2026-11-01 — Grilled the project idea, prototyped two decisions, wrote the PRD

### Prompts
1. `/grill-me @project-idea.md`
2. `B` (Q1, roles: Admin and Staff)
3. `A` (Q2, custom User model with a `role` field)
4. `A` (Q3, required, unique, case-insensitive email)
5. `A` (Q4, fixed source list + source details. The candidate-vs-application follow-up was not answered.)
6. `B, using the core field set above` (Q5, resume URL + core candidate fields)
7. `B,block` (Q6, edit + archive + delete-only-without-applications; archive blocked while applications in progress)
8. `A,using the field list above` (Q7, free-text department + proposed job opening fields)
9. `/prototype can you prototype from the latest question in our grill?` (for Q8, job closing rules)
10. `B,reopening allowed` (Q8, closing stops new applications only; Admins may reopen)
11. `B,admin only reopen` (Q9, forward-with-skipping stage moves, final stages locked, Admin-only reopen)
12. `run prototype on this one` (for Q10, pipeline screen layout)
13. `the page does not work properly, it loads a web page full of code`
14. `C, all-jobs list + detail` (Q10, pipeline screen)
15. `A` (Q11, stage counts on job page linking to filtered workspace)
16. `A,Y` (Q12, plain many-to-many skills + separate Admin-managed Skills page)
17. `B` (Q13, StageChange log with who/when/note)
18. `A` (Q14, user management in Django `/admin/`)
19. `A` (Q15, pytest + pytest-django)
20. `A` (Q16, `accounts` + `tracker` apps)
21. `A` (Q17, record applications from the candidate page)
22. `A` (Q18, `seed_demo` management command)
23. `/to-prd`
24. `Write this session log to PROMPTS.md according to its instructions.`

### Summary
- **Outcome:** An 18-question grill session resolved every part of `project-idea.md`, including the spec's two open questions (candidate lifecycle and job closing). Two throwaway prototypes were built in `prototypes/`: `job-closing-rules.html` (a logic demo comparing the Block, Keep-moving, and Auto-reject closing policies) and `pipeline-screen.html` (three Tailwind/DaisyUI UI variants: Kanban, sidebar + table, all-jobs list + detail). The decisions were turned into `prd/applicant-tracking-system.md`, with 68 user stories, implementation decisions, testing decisions, out-of-scope items, and notes. No application code was written, and nothing was committed.
- **Deviations:**
  - Q10 (pipeline screen): the recommendation was A (Kanban board per job). After viewing the UI prototype, the user chose C (all-jobs list + detail). That choice created a gap (no per-job overview), which led to Q11 (stage counts on the job page).
  - Q4: only the source-format part was answered. The candidate-vs-application follow-up was left blank, so the agent went with its recommendation (source stored on the application) and said the user could change it.
  - All other answers matched the agent's recommendations.
  - The user asked for prototypes twice, for Q8 and Q10, instead of answering directly.
- **Sideways:**
  - The pipeline-screen prototype was reported as "a web page full of code." The agent rendered it in headless Edge, and the screenshot showed the page working. The likely cause was the file opening as text in an editor rather than in a browser. The agent opened it with the default app and gave Open-with-Edge instructions; the user then reviewed it successfully.
  - The first headless Edge screenshot attempt produced no image. A retry with a separate browser profile worked.
  - Node.js isn't installed, so the JavaScript in the prototypes couldn't be syntax-checked locally. The job-closing prototype was handed over untested in a browser.
  - The Kanban variant's last column was cut off at 1400px width, which was noted as evidence of that layout's width problem.