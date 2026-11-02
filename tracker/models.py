from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse


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
