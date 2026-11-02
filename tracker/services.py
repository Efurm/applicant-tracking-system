"""Business rules for the tracker app.

Views and forms call these functions instead of saving models directly. A rule
that is broken raises ``django.core.exceptions.ValidationError`` (or a
subclass), which the caller turns into a message for the user.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from .models import Application, Candidate, JobOpening, JobStatus, Skill

CANDIDATE_FIELDS = (
    "first_name",
    "last_name",
    "email",
    "phone",
    "profile_url",
    "resume_url",
    "notes",
)


class DuplicateCandidateEmail(ValidationError):
    """Another candidate already uses this email (ignoring capitalization)."""

    def __init__(self, existing):
        self.existing = existing
        super().__init__("A candidate with this email already exists.", code="duplicate_email")


def normalize_email(email):
    return email.strip().lower()


def check_email_is_free(email, candidate=None):
    """Raise DuplicateCandidateEmail if a candidate other than ``candidate`` uses ``email``."""
    others = Candidate.objects.filter(email__iexact=email)
    if candidate is not None and candidate.pk is not None:
        others = others.exclude(pk=candidate.pk)
    existing = others.first()
    if existing is not None:
        raise DuplicateCandidateEmail(existing)


@transaction.atomic
def create_candidate(**fields):
    candidate = Candidate(**fields)
    candidate.email = normalize_email(candidate.email)
    check_email_is_free(candidate.email)
    candidate.save()
    return candidate


@transaction.atomic
def update_candidate(candidate, **fields):
    for name, value in fields.items():
        setattr(candidate, name, value)
    candidate.email = normalize_email(candidate.email)
    check_email_is_free(candidate.email, candidate)
    candidate.save()
    return candidate


def search_candidates(query=""):
    """Candidates whose first name, last name, or email contains ``query`` (any case)."""
    candidates = Candidate.objects.all()
    query = query.strip()
    if query:
        candidates = candidates.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )
    return candidates


class DuplicateSkillName(ValidationError):
    """Another skill already uses this name (ignoring capitalization)."""

    def __init__(self, existing):
        self.existing = existing
        super().__init__(f'A skill named "{existing.name}" already exists.', code="duplicate_skill")


def normalize_skill_name(name):
    """Trim and collapse whitespace, but keep the capitalization the Admin typed."""
    return " ".join(name.split())


def check_skill_name_is_free(name, skill=None):
    """Raise DuplicateSkillName if a skill other than ``skill`` uses ``name``."""
    others = Skill.objects.filter(name__iexact=name)
    if skill is not None and skill.pk is not None:
        others = others.exclude(pk=skill.pk)
    existing = others.first()
    if existing is not None:
        raise DuplicateSkillName(existing)


@transaction.atomic
def create_skill(name):
    name = normalize_skill_name(name)
    check_skill_name_is_free(name)
    return Skill.objects.create(name=name)


@transaction.atomic
def rename_skill(skill, name):
    skill.name = normalize_skill_name(name)
    check_skill_name_is_free(skill.name, skill)
    skill.save()
    return skill


class SkillInUse(ValidationError):
    """The skill can't be deleted because job openings use it."""

    def __init__(self, skill, job_count):
        self.skill = skill
        self.job_count = job_count
        noun = "job opening uses" if job_count == 1 else "job openings use"
        super().__init__(
            f'"{skill.name}" can\'t be deleted because {job_count} {noun} it.',
            code="skill_in_use",
        )


@transaction.atomic
def delete_skill(skill):
    """Delete ``skill``, refusing with SkillInUse while any job opening uses it."""
    job_count = skill.job_openings.count()
    if job_count:
        raise SkillInUse(skill, job_count)
    skill.delete()


def filter_jobs(status=""):
    """Job openings with ``status`` (Open or Closed); any other value means all jobs."""
    jobs = JobOpening.objects.all()
    if status in JobStatus.values:
        jobs = jobs.filter(status=status)
    return jobs


JOB_FIELDS = ("title", "department", "location", "employment_type", "description", "skills")


@transaction.atomic
def create_job(skills=(), **fields):
    """Create an Open job opening with the given skills."""
    job = JobOpening.objects.create(**fields)
    job.skills.set(skills)
    return job


@transaction.atomic
def update_job(job, skills=None, **fields):
    """Update a job opening's details and, if given, replace its skills."""
    for name, value in fields.items():
        setattr(job, name, value)
    job.save()
    if skills is not None:
        job.skills.set(skills)
    return job


@transaction.atomic
def close_job(job):
    """Close ``job`` to new applicants. Always allowed; existing applications are untouched."""
    job.status = JobStatus.CLOSED
    job.save(update_fields=["status", "updated_at"])
    return job


@transaction.atomic
def reopen_job(job):
    """Reopen ``job`` to new applicants. Existing applications are untouched."""
    job.status = JobStatus.OPEN
    job.save(update_fields=["status", "updated_at"])
    return job


APPLICATION_FIELDS = ("job", "source", "source_details")


class JobClosedToApplicants(ValidationError):
    """The job opening is Closed, so it takes no new applications."""

    def __init__(self, job):
        self.job = job
        super().__init__(f'"{job.title}" is closed to new applicants.', code="job_closed")


class DuplicateApplication(ValidationError):
    """The candidate already has an application for this job opening."""

    def __init__(self, existing):
        self.existing = existing
        super().__init__(
            f'{existing.candidate.full_name} has already applied to "{existing.job.title}".',
            code="duplicate_application",
        )


def jobs_open_to(candidate):
    """Open job openings that ``candidate`` hasn't applied to yet."""
    return JobOpening.objects.filter(status=JobStatus.OPEN).exclude(
        applications__candidate=candidate
    )


@transaction.atomic
def create_application(candidate, job, source, source_details=""):
    """Record ``candidate``'s application to ``job``, starting at Applied.

    Refused with JobClosedToApplicants if the job is Closed, and with
    DuplicateApplication if the candidate has already applied to it.
    """
    if not job.is_open:
        raise JobClosedToApplicants(job)
    existing = candidate.applications.filter(job=job).first()
    if existing is not None:
        raise DuplicateApplication(existing)
    return Application.objects.create(
        candidate=candidate, job=job, source=source, source_details=source_details
    )
