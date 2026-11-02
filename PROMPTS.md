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