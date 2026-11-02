from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import timezone


class Candidate(models.Model):
    """One record per person, identified by an email address that ignores case."""

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    profile_url = models.URLField("LinkedIn/portfolio URL", blank=True)
    resume_url = models.URLField("resume URL", blank=True)
    notes = models.TextField(blank=True)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="unique_candidate_email_ci",
                violation_error_message="A candidate with this email already exists.",
            ),
        ]

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse("tracker:candidate_detail", args=[self.pk])

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Skill(models.Model):
    """A shared, Admin-managed skill name, unique regardless of capitalization."""

    name = models.CharField(max_length=100)

    class Meta:
        ordering = [Lower("name")]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="unique_skill_name_ci",
                violation_error_message="A skill with this name already exists.",
            ),
        ]

    def __str__(self):
        return self.name


class EmploymentType(models.TextChoices):
    FULL_TIME = "full_time", "Full-time"
    PART_TIME = "part_time", "Part-time"
    CONTRACT = "contract", "Contract"
    INTERNSHIP = "internship", "Internship"


class JobStatus(models.TextChoices):
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"


class JobOpening(models.Model):
    """A role the hiring team is recruiting for, with the skills it needs."""

    title = models.CharField(max_length=200)
    department = models.CharField(max_length=100)
    location = models.CharField(max_length=100, blank=True)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType, default=EmploymentType.FULL_TIME
    )
    description = models.TextField()
    status = models.CharField(max_length=10, choices=JobStatus, default=JobStatus.OPEN)
    skills = models.ManyToManyField(Skill, blank=True, related_name="job_openings")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title", "pk"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("tracker:job_detail", args=[self.pk])

    @property
    def is_open(self):
        return self.status == JobStatus.OPEN


class ApplicationSource(models.TextChoices):
    COMPANY_WEBSITE = "company_website", "Company Website"
    JOB_BOARD = "job_board", "Job Board"
    REFERRAL = "referral", "Referral"
    OTHER = "other", "Other"


class Stage(models.TextChoices):
    APPLIED = "applied", "Applied"
    SCREENING = "screening", "Screening"
    INTERVIEW = "interview", "Interview"
    FINAL_REVIEW = "final_review", "Final Review"
    OFFER = "offer", "Offer"
    HIRED = "hired", "Hired"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"


# The main pipeline, in order. Rejected and Withdrawn can end an application from
# any in-progress stage, so they sit outside it.
PIPELINE_STAGES = (
    Stage.APPLIED,
    Stage.SCREENING,
    Stage.INTERVIEW,
    Stage.FINAL_REVIEW,
    Stage.OFFER,
    Stage.HIRED,
)
IN_PROGRESS_STAGES = PIPELINE_STAGES[:-1]
FINAL_STAGES = (Stage.HIRED, Stage.REJECTED, Stage.WITHDRAWN)


class Application(models.Model):
    """One candidate's application to one job opening, and where it stands."""

    candidate = models.ForeignKey(Candidate, on_delete=models.PROTECT, related_name="applications")
    job = models.ForeignKey(JobOpening, on_delete=models.PROTECT, related_name="applications")
    source = models.CharField(max_length=20, choices=ApplicationSource)
    source_details = models.CharField(max_length=200, blank=True)
    stage = models.CharField(max_length=20, choices=Stage, default=Stage.APPLIED)
    applied_on = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-applied_on", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "job"],
                name="unique_application_per_candidate_job",
                violation_error_message="This candidate has already applied to this job.",
            ),
        ]

    def __str__(self):
        return f"{self.candidate} → {self.job}"

    @property
    def is_final(self):
        return self.stage in FINAL_STAGES

    def pipeline_progress(self):
        """The pipeline stages, each with a state for the progress tracker.

        Stages before the current one are "done", the current one is "current",
        and later ones are "todo". Rejected and Withdrawn sit outside the
        pipeline, so every step is "todo" for them.
        """
        current = PIPELINE_STAGES.index(self.stage) if self.stage in PIPELINE_STAGES else -1
        steps = []
        for index, stage in enumerate(PIPELINE_STAGES):
            if current == -1 or index > current:
                state = "todo"
            elif index == current:
                state = "current"
            else:
                state = "done"
            steps.append({"stage": stage, "label": stage.label, "state": state})
        return steps


class StageChange(models.Model):
    """One move of an application from one stage to another, and who made it."""

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="stage_changes"
    )
    from_stage = models.CharField(max_length=20, choices=Stage)
    to_stage = models.CharField(max_length=20, choices=Stage)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stage_changes"
    )
    changed_at = models.DateTimeField(default=timezone.now)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["changed_at", "pk"]

    def __str__(self):
        return (
            f"{self.application}: {self.get_from_stage_display()} → {self.get_to_stage_display()}"
        )
