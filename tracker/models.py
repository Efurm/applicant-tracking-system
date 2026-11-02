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
