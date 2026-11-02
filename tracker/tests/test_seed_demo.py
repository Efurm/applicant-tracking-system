import pytest
from django.contrib.auth import authenticate
from django.core.management import CommandError, call_command

from accounts.models import Role, User
from tracker import services
from tracker.management.commands.seed_demo import DEMO_PASSWORD
from tracker.models import (
    FINAL_STAGES,
    IN_PROGRESS_STAGES,
    Application,
    Candidate,
    JobOpening,
    JobStatus,
    Skill,
    Stage,
    StageChange,
)


def _assert_history_is_valid(application):
    """The application's StageChanges run from Applied to its stage, each step allowed."""
    stage = Stage.APPLIED
    for change in application.stage_changes.select_related("changed_by"):
        assert change.from_stage == stage, application
        assert change.to_stage in services.allowed_next_stages(stage, change.changed_by)
        stage = change.to_stage
    assert stage == application.stage, application


def test_seed_demo_creates_demo_data_that_follows_the_rules(db):
    call_command("seed_demo")

    admin = authenticate(username="demo-admin", password=DEMO_PASSWORD)
    staff = authenticate(username="demo-staff", password=DEMO_PASSWORD)
    assert admin is not None and admin.role == Role.ADMIN
    assert staff is not None and staff.role == Role.STAFF

    assert JobOpening.objects.count() == 5
    assert JobOpening.objects.filter(status=JobStatus.CLOSED).count() == 1
    assert Skill.objects.count() == 15
    assert Candidate.objects.count() == 20
    archived = Candidate.objects.get(archived=True)
    assert not archived.applications.filter(stage__in=IN_PROGRESS_STAGES).exists()

    applications = Application.objects.all()
    assert 25 <= applications.count() <= 35
    assert set(applications.values_list("stage", flat=True)) == set(Stage.values)
    for application in applications:
        _assert_history_is_valid(application)
    reopens = [
        change
        for application in applications
        for change in application.stage_changes.all()
        if change.from_stage in FINAL_STAGES
    ]
    assert reopens and all(change.changed_by == admin for change in reopens)
    assert any(
        change.note for application in applications for change in application.stage_changes.all()
    )


def _row_counts():
    return {
        model.__name__: model.objects.count()
        for model in (User, Skill, JobOpening, Candidate, Application, StageChange)
    }


def test_seed_demo_twice_replaces_its_demo_data_without_duplicating_it(admin_user):
    call_command("seed_demo")
    first_run = _row_counts()

    call_command("seed_demo")

    assert _row_counts() == first_run
    assert authenticate(username="demo-admin", password=DEMO_PASSWORD) is not None
    assert authenticate(username="demo-staff", password=DEMO_PASSWORD) is not None
    assert User.objects.filter(pk=admin_user.pk).exists()


@pytest.mark.parametrize(
    "make_real_row",
    [
        lambda request: request.getfixturevalue("candidate"),
        lambda request: request.getfixturevalue("open_job"),
        lambda request: services.create_skill("Kotlin"),
    ],
    ids=["candidate", "job", "skill"],
)
def test_seed_demo_refuses_and_changes_nothing_when_non_demo_data_exists(
    db, request, make_real_row
):
    call_command("seed_demo")
    make_real_row(request)
    before = _row_counts()
    stage_change_pks = set(StageChange.objects.values_list("pk", flat=True))

    with pytest.raises(CommandError):
        call_command("seed_demo")

    assert _row_counts() == before
    assert set(StageChange.objects.values_list("pk", flat=True)) == stage_change_pks
