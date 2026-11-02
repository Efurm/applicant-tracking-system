"""Business rules for the tracker app.

Views and forms call these functions instead of saving models directly. A rule
that is broken raises ``django.core.exceptions.ValidationError`` (or a
subclass), which the caller turns into a message for the user.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from .models import Candidate

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
