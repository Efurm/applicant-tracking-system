import pytest

from accounts.models import Role, User
from tracker.models import Candidate, JobOpening, JobStatus

TEST_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="alice.admin",
        password=TEST_PASSWORD,
        first_name="Alice",
        last_name="Admin",
        role=Role.ADMIN,
    )


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="sam.staff",
        password=TEST_PASSWORD,
        first_name="Sam",
        last_name="Staff",
        role=Role.STAFF,
    )


@pytest.fixture
def admin_client(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def staff_client(client, staff_user):
    client.force_login(staff_user)
    return client


@pytest.fixture
def candidate(db):
    return Candidate.objects.create(
        first_name="Jo", last_name="Park", email="jo.park@example.com", phone="555-0100"
    )


@pytest.fixture
def open_job(db):
    return JobOpening.objects.create(
        title="Backend Developer", department="Engineering", description="Build APIs."
    )


@pytest.fixture
def closed_job(db):
    return JobOpening.objects.create(
        title="Data Analyst",
        department="Finance",
        description="Analyze data.",
        status=JobStatus.CLOSED,
    )
