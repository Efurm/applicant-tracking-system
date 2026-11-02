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

## References

- PRD (requirements and decisions): `prd/applicant-tracking-system.md`
- Implementation plan (phases): `plans/applicant-tracking-system.md`
- Prototypes: `prototypes/`
- Original assignment brief: `project-idea.md`
