# PRD: Applicant Tracking System

## Problem Statement

Our hiring team has no single place to manage hiring. Job openings, candidate details, and where each person stands in the hiring process are scattered across email, spreadsheets, and memory. Candidates arrive from the company website, job boards, referrals, and other sources, and the same person may apply to several roles. As a result:

- Staff can't easily see where any applicant stands, or how a particular job's search is going.
- Duplicate candidate records and duplicate applications creep in.
- There's no record of who moved an applicant forward or rejected them, or when.
- There are no agreed rules for what happens when a job closes, or for how candidate records should be kept, archived, or removed over time.

## Solution

An internal Django web application, the **Applicant Tracking System**, used only by hiring-team employees (candidates never log in). It provides:

- **Candidates:** one record per person, identified by a unique email address, with basic contact information, a resume link, and notes. Records can be edited, archived (hidden but preserved), or deleted only if the person never applied to anything.
- **Job openings:** created and managed by Admins, with descriptive details and associated skills. An opening is Open or Closed. Closing stops new applications, but people already in progress keep moving. Closed openings can be reopened.
- **Skills:** a shared, Admin-managed list attached to job openings.
- **Applications:** recorded from a candidate's page against an open job, capturing how the candidate came to us (the source). Each candidate can apply to a given opening only once.
- **A defined hiring pipeline:** Applied → Screening → Interview → Final Review → Offer → Hired, plus Rejected and Withdrawn. The rules for moving between stages are enforced, and every move is logged with who made it, when, and an optional note.
- **An applications workspace:** a searchable, filterable list of applications across all jobs, alongside a detail panel. Staff can see an applicant's progress and history and move them to an allowed stage without a full page reload.
- **Per-job stage counts:** on each job opening's page, linking into the workspace filtered to that job and stage.
- **Two roles:** **Admin** and **Staff**. Admins handle job openings, skills, archiving and deleting candidates, and reopening finished applications. Staff handle day-to-day candidate and application work.

## User Stories

### Access and accounts

1. As a hiring-team employee, I want to log in with my own account, so that only authorized staff can see candidate information.
2. As a hiring-team employee, I want to log out, so that nobody else can use my session on a shared computer.
3. As an anonymous visitor, I want to be redirected to the login page when I try to open any app page, so that candidate data is never exposed publicly.
4. As an Admin, I want to create user accounts and assign each one the Admin or Staff role, so that every employee has the right level of access.
5. As an Admin, I want to deactivate a departed employee's account instead of deleting it, so that they can no longer log in but their history of actions remains intact.
6. As a developer setting up the system, I want to create the first Admin account from the command line, so that the system can be bootstrapped.
7. As a Staff member, I want Admin-only actions to be hidden from me and refused if I try them anyway, so that I can't accidentally make changes outside my role.

### Candidates

8. As a Staff member, I want to add a candidate with first name, last name, email, phone, LinkedIn/portfolio URL, resume URL, and notes, so that we have their basic information in one place.
9. As a Staff member, I want the system to refuse a new candidate whose email already exists (regardless of capitalization) and point me to the existing record, so that we never end up with duplicate people.
10. As a Staff member, I want to be taken to the new candidate's page after creating them, so that I can immediately record their application.
11. As a Staff member, I want to edit a candidate's information at any time, so that their details stay current.
12. As a Staff member, I want to see a list of candidates that hides archived candidates by default, so that I'm working with active people.
13. As a Staff member, I want to search the candidate list, so that I can quickly find a specific person.
14. As a Staff member, I want an option to show archived candidates, so that I can still look up past applicants.
15. As a Staff member, I want a candidate's page to show all of their applications across jobs, so that I can see their full history with us.
16. As an Admin, I want to archive a candidate, so that they no longer clutter day-to-day lists but their history is preserved.
17. As an Admin, I want archiving to be refused while the candidate has any application still in progress, so that nobody is archived in the middle of a hiring process.
18. As an Admin, I want to unarchive a candidate, so that a returning applicant can be considered again.
19. As a Staff member, I want archived candidates to be blocked from receiving new applications, so that archived people aren't accidentally put back in the pipeline.
20. As an Admin, I want to permanently delete a candidate who has no applications, so that records created by mistake can be cleaned up.
21. As an Admin, I want deletion to be refused (with a suggestion to archive) when the candidate has any applications, so that hiring history is never destroyed.

### Job openings

22. As an Admin, I want to create a job opening with a title, department, location, employment type (Full-time, Part-time, Contract, Internship), description, and skills, so that the team knows what we're hiring for.
23. As an Admin, I want to edit a job opening, so that I can correct or update its details.
24. As a Staff member, I want to view the list of job openings and their details, so that I know what roles are being hired for.
25. As a Staff member, I want to filter the job list by Open or Closed, so that I can focus on active hiring.
26. As an Admin, I want to close a job opening even while some applicants are still in progress, so that we can stop accepting new applicants while we finish evaluating the current ones.
27. As a Staff member, I want a closed job to be clearly labeled "Closed to new applicants," so that I understand existing applicants can still move forward.
28. As a Staff member, I want applications on a closed job to keep moving through the pipeline normally, so that closing a job doesn't stall interviews in progress.
29. As a Staff member, I want the system to refuse new applications to a closed job, so that we don't take on applicants for a role we've stopped recruiting for.
30. As an Admin, I want to reopen a closed job, so that we can resume recruiting (for example, when a hire falls through) without creating a duplicate opening.
31. As a Staff member, I want close and reopen to be Admin-only, so that the status of an opening is controlled by the people responsible for it.
32. As a Staff member, I want a job opening's page to show how many applications are in each stage, so that I can see at a glance how the search for that role is going.
33. As a Staff member, I want to click a stage count on a job's page and land in the applications workspace filtered to that job and stage, so that I can act on those applicants immediately.

### Skills

34. As an Admin, I want to manage a shared list of skills (create, rename, view), so that job openings use consistent skill names.
35. As an Admin, I want skill names to be unique regardless of capitalization, so that "Python" and "python" don't both exist.
36. As an Admin, I want to pick several skills from the shared list when creating or editing a job opening, so that each opening shows the skills it needs.
37. As an Admin, I want the same skill to be usable on many job openings, so that common skills aren't re-entered for each role.
38. As an Admin, I want deleting a skill to be refused while any job opening uses it, so that job descriptions don't silently lose information.
39. As a Staff member, I want to see a job opening's skills on its page, so that I can judge candidate fit.

### Recording applications

40. As a Staff member, I want an "Apply to a job" action on a candidate's page, so that I can record an application while I'm looking at that person.
41. As a Staff member, I want the job choices to include only open jobs the candidate hasn't already applied to, so that I can't pick an invalid option.
42. As a Staff member, I want to record the application's source (Company Website, Job Board, Referral, Other) and optional source details (e.g. "LinkedIn" or "Referred by Maria in Sales"), so that we know how each applicant reached us for that role.
43. As a Staff member, I want the system to refuse a second application by the same candidate to the same opening, even if the form is bypassed, so that each person has at most one application per opening.
44. As a Staff member, I want a candidate to be able to apply to several different openings, so that we can consider them for multiple roles.
45. As a Staff member, I want a new application to start in the Applied stage, with the application date recorded automatically, so that every application has a consistent starting point.

### Hiring pipeline and stage moves

46. As a Staff member, I want an applications workspace that lists applications across all jobs, so that I can manage my whole workload in one place.
47. As a Staff member, I want to filter the workspace by job and by stage (defaulting to in-progress applications) and search by candidate name, so that I can focus on the applicants I need.
48. As a Staff member, I want the workspace filters reflected in the page address, so that I can bookmark or share a filtered view.
49. As a Staff member, I want to select an application and see its details in a side panel (the candidate's contact information, job, job status, source, application date, and a progress tracker of stages), so that I understand where they stand.
50. As a Staff member, I want the detail panel to list the candidate's other applications and let me jump to them, so that I'm aware of their interest in other roles.
51. As a Staff member, I want to move an application to its next stage from the detail panel without the whole page reloading, so that working through applicants is quick.
52. As a Staff member, I want the list to reflect the new stage right after a move, so that the list and the panel always agree.
53. As a Staff member, I want to move an application forward to any later stage, skipping intermediate stages when appropriate, so that strong or referred candidates can be fast-tracked.
54. As a Staff member, I want to be prevented from moving an application backward along the pipeline, so that stages reflect real progress.
55. As a Staff member, I want to mark an in-progress application as Rejected or Withdrawn from any stage, so that I can end the process at any time.
56. As a Staff member, I want to be offered only the moves that are allowed for the application's current stage, so that I'm never shown an invalid choice.
57. As a Staff member, I want Hired, Rejected, and Withdrawn to be final, so that hiring decisions are dependable.
58. As an Admin, I want to reopen a final application back to an in-progress stage, so that mistakes (such as an accidental rejection) can be corrected.
59. As an Admin, I want reopening an application to be refused while its candidate is archived, so that archived candidates never have in-progress applications.
60. As an Admin, I want to be able to reopen an application on a closed job, so that a correction is possible even after recruiting has stopped.
61. As a Staff member, I want to add an optional note when moving an application, so that the reason for the move is recorded.
62. As a Staff member, I want every stage move to be recorded with the from-stage, to-stage, who made it, and when, so that we have an accountable history.
63. As a Staff member, I want the detail panel to show the application's stage history as a timeline, including any Admin reopens, so that I can see how the applicant got where they are.
64. As a Staff member, I want an invalid move attempted directly against the server to be refused with a clear message, so that the rules can't be bypassed.

### Demo and development

65. As a developer or instructor, I want one command that loads realistic demo data (Admin and Staff logins, several job openings including a closed one, skills, candidates including an archived one, and applications across every stage with stage history including an Admin reopen), so that the app can be demonstrated immediately.
66. As a developer, I want the demo-data command to create its data through the same business rules the app uses, so that the demo data is always valid and a broken rule is noticed.
67. As a developer, I want the demo-data command to be safe to run again, so that I can reset the demo without corrupting real data.
68. As a developer, I want the README to list the demo login credentials and mark them as local-development only, so that anyone can try the app.

## Implementation Decisions

### Technology stack
- Python, Django, and SQLite, with the project managed by **uv**.
- **Tailwind CSS with DaisyUI** through **django-tailwind-cli** for styling.
- **HTMX** for partial page updates (stage moves).
- **Ruff** for linting and formatting.
- **pytest with pytest-django** for automated tests.

### Project structure
- Two Django apps:
  - **accounts:** contains only the custom User model. It exists from the very first migration.
  - **tracker:** contains all hiring models, views, forms, and templates.
- Business rules live in a dedicated **services module** within the tracker app, not in views or forms. Views stay thin: they call services and render results. Services raise clear validation errors, which views turn into user-facing messages.

### Users and roles
- A custom User model extends Django's abstract user and adds a **role** choice field with values **Admin** and **Staff**. The project's user-model setting points to it.
- Permission checks use the role field. Shared helpers/mixins guard Admin-only views, and templates hide Admin-only controls from Staff.
- All app pages require login. Logging in and out uses Django's built-in authentication views, styled with DaisyUI.
- User management happens in Django's built-in admin site. The User model, with its role, is registered there. App Admins also get Django's staff flag (access to the admin site); Staff users do not. Deactivation uses Django's active flag. Users are never deleted, so the history that references them is preserved.

### Data model
- **Candidate:**
  - First name and last name (required).
  - Email (required, unique, compared case-insensitively). Normalize to lowercase on save and/or use a case-insensitive unique constraint.
  - Phone (optional), LinkedIn/portfolio URL (optional), resume URL (optional), notes (optional).
  - An archived flag.
  - Created and updated timestamps.
- **JobOpening:**
  - Title (required) and department (required, free text).
  - Location (optional, free text).
  - Employment type: a fixed choice of Full-time, Part-time, Contract, or Internship.
  - Description.
  - Status: a fixed choice of Open or Closed.
  - A many-to-many relationship to Skill (a plain relationship with no extra fields).
  - Created and updated timestamps.
- **Skill:** a name, unique case-insensitively.
- **Application:**
  - Links one Candidate and one JobOpening, with a database-level unique constraint on that pair.
  - Source: a fixed choice of Company Website, Job Board, Referral, or Other. Source details: optional free text. The source lives on the application, not the candidate, because the same person may arrive through different channels for different jobs.
  - Current stage: a fixed choice of Applied, Screening, Interview, Final Review, Offer, Hired, Rejected, or Withdrawn. Defaults to Applied.
  - Applied date, and created and updated timestamps.
- **StageChange:**
  - Links to an Application.
  - Records the from-stage and to-stage, the user who made the change (a protected reference, so users can't be deleted out from under history), the timestamp, and an optional note.
  - Ordered by time.
- Deletion protection:
  - Candidate → Application references are protected, so a candidate with applications can't be deleted at the database level.
  - Skills in use are protected from deletion at the service/view level.

### Stage rules (enforced in services)
- The main pipeline order is Applied → Screening → Interview → Final Review → Offer → Hired.
- **In-progress stages:** Applied, Screening, Interview, Final Review, Offer. **Final stages:** Hired, Rejected, Withdrawn.
- From an in-progress stage, the allowed moves are any later stage in the pipeline (skipping allowed), plus Rejected or Withdrawn. Backward moves are not allowed.
- From a final stage, no moves are allowed, except that an **Admin** may reopen the application to any in-progress stage. Reopening is refused if the candidate is archived. Reopening is allowed on closed jobs.
- A single "allowed next stages for this stage and user" function drives both the UI (which buttons appear) and validation (which moves are accepted).
- A single **move application** service validates the move, updates the stage, and writes a StageChange record in one database transaction. Every stage change in the system goes through it, including the demo-data command.

### Lifecycle rules (enforced in services)
- **Create application:**
  - Refused if the job is Closed, the candidate is archived, or the candidate already has an application for that job.
  - On success, the application starts at Applied.
  - Whether to also write an initial StageChange row for "created at Applied" is left to implementation; the timeline must at least show the application date.
- **Close job:** Admin only. Always allowed, whatever the state of its applications. Existing applications are untouched.
- **Reopen job:** Admin only. Sets the status back to Open. Existing applications are untouched.
- **Archive candidate:** Admin only. Refused while the candidate has any in-progress application.
- **Unarchive candidate:** Admin only.
- **Delete candidate:** Admin only. Refused if the candidate has any applications.
- **Delete skill:** Admin only. Refused if any job opening uses it.
- **Create and edit job openings and skills:** Admin only.
- **Create and edit candidates, record applications, and move applications between non-final stages:** both roles.

### Screens and interactions
- **Candidates:** a list (searchable, with a "show archived" toggle) and pages to create, edit, and view a candidate.
  - The candidate page lists all of the candidate's applications and has an "Apply to a job" action.
  - The apply form's job choices are limited to open jobs the candidate hasn't applied to, and the form includes source and source details.
  - Creating a candidate redirects to the new candidate's page.
  - A duplicate email produces a form error linking to the existing candidate.
- **Job openings:** a list (filterable by status) and pages to create, edit, and view a job opening.
  - The job page shows the job's details and skills.
  - It shows a stage-count summary (DaisyUI stats style) where each count links to the workspace filtered by that job and stage.
  - Close and reopen actions appear for Admins.
  - Closed jobs display "Closed to new applicants."
- **Skills:** an Admin-only list with create, edit, and delete (delete refused while in use).
- **Applications workspace** (the layout chosen from the UI prototype, variant C):
  - Left side: a searchable list of applications across all jobs. Filters for job and stage (defaulting to in-progress) are kept in the URL query string.
  - Right side: a detail panel for the selected application, showing candidate contact information, job, job status, source, application date, a stage progress tracker, the allowed-move buttons, the stage-history timeline, and links to the candidate's other applications.
  - Final applications show "final" messaging to Staff and "Reopen" options to Admins.
- **HTMX stage moves:**
  - A move button (with an optional note) sends an HTMX request to a move endpoint.
  - The server responds with the re-rendered detail panel plus an out-of-band update of that application's row in the list, so there's no full page reload.
  - Refused moves return an error message rendered in place.
  - The endpoint validates permissions and rules server-side, regardless of what the UI showed.
- **Navigation:** a shared DaisyUI page shell with links to the Workspace, Candidates, Job Openings, Skills (Admin only), the current user, and logout.

### Demo data
- A management command creates demo data by calling the service functions, so the data obeys every rule.
- It creates:
  - Demo Admin and Staff accounts.
  - About 5 job openings, with one closed.
  - About 15 skills.
  - About 20 candidates, with one archived.
  - About 30 applications spread across all stages, with realistic stage history including at least one Admin reopen.
- It's safe to re-run: it removes its own previously created demo data first, or refuses to run if non-demo data is present.

## Testing Decisions

- **What makes a good test:** tests check externally visible behavior (what a user or caller can and cannot do, and what the resulting data looks like), not internal implementation details. A test should still pass after a refactor that preserves behavior.
- **Framework:** pytest with pytest-django. Shared fixtures for common setup: an Admin user, a Staff user, an open job, a closed job, a candidate, an archived candidate, and an application at a given stage.
- **Modules to test:**
  - **Services (most coverage):**
    - The allowed-next-stages function, for every stage and both roles.
    - The move service: valid moves, backward moves refused, Rejected/Withdrawn from any in-progress stage, final stages locked for Staff, Admin reopen allowed, reopen refused for archived candidates, reopen allowed on closed jobs, and a StageChange written with the correct user, stages, and note.
    - The create-application service: closed job refused, archived candidate refused, duplicate refused, initial stage is Applied.
    - The job close/reopen rules, candidate archive/unarchive/delete rules, and skill delete protection.
  - **Models and constraints:** case-insensitive unique email, unique skill name, and the unique (candidate, job opening) constraint at the database level.
  - **Views and permissions:**
    - Anonymous users are redirected to login.
    - Staff are refused on Admin-only views and actions (job create/edit/close/reopen, skill management, archive/unarchive/delete, reopening an application).
    - Admins succeed on those views and actions.
  - **HTMX move endpoint:**
    - An HTMX request returns a partial (not a full page) containing the updated panel and the out-of-band list row.
    - Invalid moves return an error without changing data.
  - **Workspace filtering:** job, stage, the in-progress default, and name search, all driven by URL parameters.
  - **Job detail stage counts:** counts are correct and link to the correctly filtered workspace URLs.
  - **Forms:** the apply form offers only open, not-yet-applied jobs. The duplicate-email error points to the existing candidate.
  - **Demo-data command:** runs successfully, produces data that obeys the rules, and can be run twice safely.
- **Prior art:** the repository has no existing tests. These tests establish the project's conventions.

## Out of Scope

- Candidate-facing features of any kind: a candidate login, a public careers page, an application portal, or emails to candidates.
- Resume file uploads and storage. Only a resume URL is stored.
- Roles beyond Admin and Staff (Hiring Manager, Interviewer), and per-job or per-object permissions.
- In-app user management pages. Users are managed in Django's admin site.
- An admin-managed list of sources or departments. Sources are a fixed list, and the department is free text.
- Required vs. preferred skills, skill levels, or skills on candidates. Candidate-to-job skill matching.
- A per-job Kanban board or table with move controls. Moves happen only in the workspace.
- Drag-and-drop stage moves.
- Full audit history of all field edits. Only stage changes are logged.
- Interview scheduling, scorecards, offers/compensation tracking, notifications, email integration, calendars, and reporting dashboards beyond the per-job stage counts.
- Bulk actions (bulk move, bulk reject).
- Recording applications from the job page or through a combined new-candidate-plus-application form. These are possible later add-ons.
- Production deployment, a non-SQLite database, and data import/export.

## Further Notes

- Two throwaway prototypes informed decisions and live in the repository's prototypes folder. They aren't production code and shouldn't be promoted into the app.
  - **Job closing rules:** a logic prototype comparing three policies. It confirmed "close stops new applications; in-progress ones continue; reopen allowed (Admin)." It also surfaced the need for locked final stages, which became the stage rules above.
  - **Pipeline screen:** a UI prototype comparing a Kanban board, a per-job table, and an all-jobs list + detail workspace. The **all-jobs list + detail** layout was chosen because it fits any screen width, suits staff working across several jobs, and shows a candidate's other applications. The prototype also showed that a Kanban board with eight stages overflows a typical laptop screen.
- The spec's two open questions are resolved in this PRD:
  - **Candidate lifecycle:** edit anytime; archive (Admin; blocked while applications are in progress); unarchive; delete only without applications.
  - **Job closing:** closes to new applicants only; in-progress applications continue; Admins may reopen.
- A good build order is:
  1. Custom User model first, before any migration.
  2. Core models and services with tests.
  3. Candidate, job, and skill pages.
  4. The workspace with HTMX moves.
  5. Job stage counts.
  6. The demo-data command.
