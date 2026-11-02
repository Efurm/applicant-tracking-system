"""Load demo data for local development: ``uv run python manage.py seed_demo``.

Everything except the two user accounts is created through ``tracker.services``,
so the demo data obeys the same rules as the app, and a broken rule shows up
here as an error.

It is safe to run again: it deletes its own earlier demo data and loads it
fresh. It refuses, changing nothing, if the database holds any candidate, job
opening, or skill it didn't create. Real user accounts are never touched.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Role, User
from tracker import services
from tracker.models import (
    Application,
    ApplicationSource,
    Candidate,
    EmploymentType,
    JobOpening,
    Skill,
    Stage,
)

# Local development only: these credentials are published in the README.
DEMO_PASSWORD = "demo-password-123"
DEMO_EMAIL_DOMAIN = "demo.example.com"

# (username, first name, last name, role)
USERS = [
    ("demo-admin", "Avery", "Admin", Role.ADMIN),
    ("demo-staff", "Sam", "Staff", Role.STAFF),
]

SKILLS = [
    "Python",
    "Django",
    "PostgreSQL",
    "REST APIs",
    "Git",
    "JavaScript",
    "React",
    "CSS",
    "Accessibility",
    "SQL",
    "Excel",
    "Tableau",
    "Communication",
    "Copywriting",
    "Customer Service",
]

# The last job is closed once its applications are recorded.
JOBS = [
    {
        "title": "Backend Engineer",
        "department": "Engineering",
        "location": "Austin, TX",
        "employment_type": EmploymentType.FULL_TIME,
        "description": "Design and build the APIs behind our products.",
        "skills": ["Python", "Django", "PostgreSQL", "REST APIs", "Git"],
    },
    {
        "title": "Frontend Developer",
        "department": "Engineering",
        "location": "Remote",
        "employment_type": EmploymentType.FULL_TIME,
        "description": "Build accessible, responsive interfaces for our web app.",
        "skills": ["JavaScript", "React", "CSS", "Accessibility", "Git"],
    },
    {
        "title": "Data Analyst",
        "department": "Finance",
        "location": "Chicago, IL",
        "employment_type": EmploymentType.FULL_TIME,
        "description": "Turn sales and finance data into reports the business can act on.",
        "skills": ["SQL", "Excel", "Tableau", "Python", "Communication"],
    },
    {
        "title": "Marketing Coordinator",
        "department": "Marketing",
        "location": "Denver, CO",
        "employment_type": EmploymentType.PART_TIME,
        "description": "Plan campaigns and write copy for our newsletter and social channels.",
        "skills": ["Communication", "Copywriting", "Excel"],
    },
    {
        "title": "Customer Support Intern",
        "department": "Support",
        "location": "Remote",
        "employment_type": EmploymentType.INTERNSHIP,
        "description": "Answer customer questions by email and chat over the summer.",
        "skills": ["Communication", "Customer Service"],
    },
]
CLOSED_JOB = "Customer Support Intern"

# (first name, last name, phone, notes). First names are unique, so the
# applications below refer to candidates by first name.
CANDIDATES = [
    ("Jordan", "Reyes", "555-0101", "Six years of Django experience."),
    ("Priya", "Shah", "555-0102", ""),
    ("Marcus", "Bell", "555-0103", "Open to relocating."),
    ("Elena", "Novak", "", ""),
    ("Tyler", "Brooks", "555-0105", "Met at the spring career fair."),
    ("Hana", "Kim", "555-0106", ""),
    ("Diego", "Alvarez", "555-0107", "Portfolio includes a design system."),
    ("Grace", "Okafor", "", ""),
    ("Liam", "Walsh", "555-0109", ""),
    ("Sofia", "Rossi", "555-0110", "Tableau certified."),
    ("Noah", "Patel", "555-0111", ""),
    ("Chloe", "Martin", "", "Prefers hybrid work."),
    ("Ethan", "Nguyen", "555-0113", ""),
    ("Maya", "Johnson", "555-0114", ""),
    ("Lucas", "Schmidt", "555-0115", ""),
    ("Zoe", "Carter", "555-0116", "Ran a nonprofit newsletter."),
    ("Owen", "Murphy", "", ""),
    ("Isla", "Fraser", "555-0118", ""),
    ("Ravi", "Iyer", "555-0119", "Computer science student, graduating in May."),
    ("Quinn", "Foster", "555-0120", "Not looking right now; archived."),
]
# Archived last, once all of their applications are final.
ARCHIVED_CANDIDATE = "Quinn"

S, A = "demo-staff", "demo-admin"
web = ApplicationSource.COMPANY_WEBSITE
board = ApplicationSource.JOB_BOARD
referral = ApplicationSource.REFERRAL
other = ApplicationSource.OTHER

# (candidate, job, source, source details, moves). Each move is (stage, mover,
# note), applied in order through the move service.
APPLICATIONS = [
    ("Jordan", "Backend Engineer", board, "LinkedIn", [
        (Stage.SCREENING, S, "Strong Django background."),
        (Stage.INTERVIEW, S, ""),
        (Stage.FINAL_REVIEW, A, "Great system design interview."),
    ]),
    ("Priya", "Backend Engineer", referral, "Referred by Maria in Sales", [
        (Stage.INTERVIEW, S, "Referral, so fast-tracked past screening."),
        (Stage.OFFER, A, ""),
        (Stage.HIRED, A, "Accepted the offer."),
    ]),
    ("Marcus", "Backend Engineer", web, "", []),
    ("Elena", "Backend Engineer", board, "Indeed", [
        (Stage.SCREENING, S, ""),
        (Stage.REJECTED, S, "Not enough backend experience yet."),
    ]),
    ("Tyler", "Backend Engineer", other, "Career fair", [(Stage.SCREENING, S, "")]),
    ("Noah", "Backend Engineer", board, "LinkedIn", [(Stage.INTERVIEW, S, "")]),
    ("Lucas", "Backend Engineer", web, "", [
        (Stage.SCREENING, S, ""),
        (Stage.WITHDRAWN, S, "Withdrew by email."),
        (Stage.SCREENING, A, "Reopened: the withdrawal email was meant for another company."),
    ]),
    ("Hana", "Frontend Developer", board, "LinkedIn", [
        (Stage.SCREENING, S, ""),
        (Stage.REJECTED, S, "Portfolio looked thin."),
        (Stage.INTERVIEW, A, "Reopened: rejected by mistake, the portfolio link was broken."),
        (Stage.FINAL_REVIEW, S, ""),
    ]),
    ("Diego", "Frontend Developer", web, "", [
        (Stage.SCREENING, S, ""),
        (Stage.INTERVIEW, S, ""),
        (Stage.OFFER, A, "Offer sent."),
    ]),
    ("Grace", "Frontend Developer", referral, "Referred by Dev in Engineering", []),
    ("Liam", "Frontend Developer", board, "Indeed", [
        (Stage.WITHDRAWN, S, "Accepted another offer."),
    ]),
    ("Marcus", "Frontend Developer", web, "", [(Stage.SCREENING, S, "")]),
    ("Maya", "Frontend Developer", other, "Hackathon", [
        (Stage.REJECTED, S, "Looking for a backend role."),
    ]),
    ("Sofia", "Data Analyst", board, "LinkedIn", [
        (Stage.SCREENING, S, ""),
        (Stage.INTERVIEW, S, ""),
    ]),
    ("Noah", "Data Analyst", web, "", [
        (Stage.SCREENING, S, ""),
        (Stage.INTERVIEW, S, ""),
        (Stage.FINAL_REVIEW, S, ""),
        (Stage.OFFER, A, ""),
        (Stage.HIRED, A, "Starts next month."),
    ]),
    ("Chloe", "Data Analyst", other, "Analytics meetup", []),
    ("Ethan", "Data Analyst", referral, "Referred by Priya in Finance", [
        (Stage.REJECTED, S, "Looking for a more senior role."),
    ]),
    ("Jordan", "Data Analyst", board, "LinkedIn", [
        (Stage.WITHDRAWN, S, "Prefers the Backend Engineer role."),
    ]),
    ("Diego", "Data Analyst", referral, "Referred by Ana in Engineering", []),
    ("Maya", "Marketing Coordinator", web, "", [(Stage.SCREENING, S, "")]),
    ("Lucas", "Marketing Coordinator", board, "Indeed", [
        (Stage.SCREENING, S, ""),
        (Stage.INTERVIEW, S, ""),
        (Stage.FINAL_REVIEW, S, "Writing sample was excellent."),
    ]),
    ("Zoe", "Marketing Coordinator", referral, "Referred by Tom in Marketing", [
        (Stage.OFFER, A, "Referral with agency experience."),
    ]),
    ("Owen", "Marketing Coordinator", board, "Indeed", []),
    ("Elena", "Marketing Coordinator", board, "Indeed", [
        (Stage.SCREENING, S, ""),
        (Stage.INTERVIEW, S, ""),
    ]),
    ("Quinn", "Marketing Coordinator", board, "LinkedIn", [
        (Stage.SCREENING, S, ""),
        (Stage.REJECTED, S, "Schedule didn't fit the part-time hours."),
    ]),
    ("Isla", "Customer Support Intern", web, "", [
        (Stage.SCREENING, S, ""),
        (Stage.INTERVIEW, S, ""),
    ]),
    ("Ravi", "Customer Support Intern", other, "University job board", [
        (Stage.SCREENING, S, ""),
        (Stage.INTERVIEW, S, ""),
        (Stage.HIRED, A, "Summer intern."),
    ]),
    ("Owen", "Customer Support Intern", board, "Handshake", [(Stage.REJECTED, S, "")]),
    ("Tyler", "Customer Support Intern", web, "", [(Stage.SCREENING, S, "")]),
    ("Quinn", "Customer Support Intern", web, "", [
        (Stage.WITHDRAWN, S, "Moved out of state."),
    ]),
]  # fmt: skip


def demo_email(first_name, last_name):
    return f"{first_name}.{last_name}@{DEMO_EMAIL_DOMAIN}".lower()


def non_demo_data():
    """Descriptions of the candidates, job openings, and skills the command didn't create."""
    found = {
        "candidate": Candidate.objects.exclude(email__iendswith=f"@{DEMO_EMAIL_DOMAIN}"),
        "job opening": JobOpening.objects.exclude(title__in=[job["title"] for job in JOBS]),
        "skill": Skill.objects.exclude(name__in=SKILLS),
    }
    descriptions = []
    for noun, rows in found.items():
        count = rows.count()
        if count:
            descriptions.append(f"{count} {noun}{'' if count == 1 else 's'}")
    return descriptions


def remove_demo_data():
    """Delete what an earlier run created, in the order the PROTECT foreign keys allow.

    Applications go first (their StageChanges cascade with them), which frees
    the candidates, the jobs, and the demo users who made the moves. Skills go
    after the jobs that used them.
    """
    demo_candidates = Candidate.objects.filter(email__iendswith=f"@{DEMO_EMAIL_DOMAIN}")
    Application.objects.filter(candidate__in=demo_candidates).delete()
    demo_candidates.delete()
    JobOpening.objects.filter(title__in=[job["title"] for job in JOBS]).delete()
    Skill.objects.filter(name__in=SKILLS).delete()
    User.objects.filter(username__in=[username for username, *_ in USERS]).delete()


class Command(BaseCommand):
    help = "Load demo data (users, skills, jobs, candidates, applications) for local development."

    @transaction.atomic
    def handle(self, *args, **options):
        found = non_demo_data()
        if found:
            raise CommandError(
                f"Found non-demo data ({', '.join(found)}). seed_demo only replaces its own "
                "demo data, so run it on a fresh database (local development only)."
            )
        remove_demo_data()
        users = {
            username: User.objects.create_user(
                username=username,
                password=DEMO_PASSWORD,
                first_name=first_name,
                last_name=last_name,
                email=f"{username}@{DEMO_EMAIL_DOMAIN}",
                role=role,
            )
            for username, first_name, last_name, role in USERS
        }
        skills = {name: services.create_skill(name) for name in SKILLS}
        jobs = {}
        for fields in JOBS:
            fields = dict(fields, skills=[skills[name] for name in fields["skills"]])
            jobs[fields["title"]] = services.create_job(**fields)
        candidates = {
            first_name: services.create_candidate(
                first_name=first_name,
                last_name=last_name,
                email=demo_email(first_name, last_name),
                phone=phone,
                notes=notes,
            )
            for first_name, last_name, phone, notes in CANDIDATES
        }

        # Record applications before closing the job and archiving the candidate,
        # since both refuse new applications afterwards.
        for first_name, title, source, details, moves in APPLICATIONS:
            application = services.create_application(
                candidates[first_name], jobs[title], source, details
            )
            for stage, mover, note in moves:
                services.move_application(application, stage, users[mover], note)
        services.close_job(jobs[CLOSED_JOB])
        services.archive_candidate(candidates[ARCHIVED_CANDIDATE])

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded demo data: {len(SKILLS)} skills, {len(JOBS)} jobs, "
                f"{len(CANDIDATES)} candidates, {len(APPLICATIONS)} applications. "
                f"Log in as demo-admin or demo-staff with password {DEMO_PASSWORD!r}."
            )
        )
