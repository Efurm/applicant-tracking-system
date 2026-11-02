import pytest

from accounts.models import Role, User
from tracker import services
from tracker.models import ApplicationSource, Candidate, JobOpening, JobStatus, Stage

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


@pytest.fixture
def make_application(candidate, open_job, staff_user):
    """Build an application at a given stage (defaults: the ``candidate`` fixture, ``open_job``).

    Pipeline stages are reached with one move by ``staff_user`` through the
    move service. Rejected and Withdrawn aren't allowed moves yet (Phase 9),
    so for now those are set directly.
    """

    def make(stage=Stage.APPLIED, candidate=candidate, job=open_job):
        application = services.create_application(candidate, job, ApplicationSource.JOB_BOARD)
        if stage in services.allowed_next_stages(application.stage, staff_user):
            services.move_application(application, stage, staff_user)
        elif stage != Stage.APPLIED:
            application.stage = stage
            application.save(update_fields=["stage", "updated_at"])
        return application

    return make
