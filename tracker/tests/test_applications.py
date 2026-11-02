import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.urls import reverse
from django.utils import timezone

from tracker import services
from tracker.models import Application, ApplicationSource, Candidate, JobOpening, Stage


@pytest.fixture
def make_application(candidate, open_job):
    """Build an application at a given stage (defaults: the ``candidate`` fixture, ``open_job``).

    The stage is set directly, since stage moves arrive in a later phase.
    """

    def make(stage=Stage.APPLIED, candidate=candidate, job=open_job):
        application = services.create_application(candidate, job, ApplicationSource.JOB_BOARD)
        if stage != Stage.APPLIED:
            application.stage = stage
            application.save(update_fields=["stage", "updated_at"])
        return application

    return make


def test_create_application_refuses_a_closed_job_and_a_duplicate(candidate, open_job, closed_job):
    with pytest.raises(services.JobClosedToApplicants):
        services.create_application(candidate, closed_job, ApplicationSource.JOB_BOARD)

    services.create_application(candidate, open_job, ApplicationSource.JOB_BOARD)
    with pytest.raises(services.DuplicateApplication) as refused:
        services.create_application(candidate, open_job, ApplicationSource.REFERRAL)

    assert isinstance(refused.value, ValidationError)
    assert Application.objects.filter(candidate=candidate).count() == 1
    assert Application.objects.get().job == open_job


def test_apply_form_offers_only_open_jobs_the_candidate_has_not_applied_to(
    staff_client, candidate, open_job, closed_job
):
    applied_job = JobOpening.objects.create(
        title="Frontend Developer", department="Engineering", description="Build UIs."
    )
    services.create_application(candidate, applied_job, ApplicationSource.REFERRAL)
    other = Candidate.objects.create(first_name="Ana", last_name="Diaz", email="ana@example.com")
    services.create_application(other, open_job, ApplicationSource.JOB_BOARD)

    response = staff_client.get(reverse("tracker:candidate_apply", args=[candidate.pk]))

    assert response.status_code == 200
    assert list(response.context["form"].fields["job"].queryset) == [open_job]


def test_staff_apply_a_candidate_from_their_page_and_see_it_listed(
    staff_client, candidate, open_job
):
    response = staff_client.post(
        reverse("tracker:candidate_apply", args=[candidate.pk]),
        {
            "job": open_job.pk,
            "source": ApplicationSource.REFERRAL,
            "source_details": "Referred by Maria in Sales",
        },
    )

    assert response.status_code == 302
    assert response.url == candidate.get_absolute_url()
    application = Application.objects.get(candidate=candidate)
    assert (application.job, application.stage, application.applied_on) == (
        open_job,
        Stage.APPLIED,
        timezone.localdate(),
    )
    assert (application.source, application.source_details) == (
        ApplicationSource.REFERRAL,
        "Referred by Maria in Sales",
    )
    detail_page = staff_client.get(candidate.get_absolute_url()).content.decode()
    assert open_job.title in detail_page
    assert "Applied" in detail_page
    assert reverse("tracker:candidate_apply", args=[candidate.pk]) in detail_page


def test_database_refuses_a_second_application_for_the_same_candidate_and_job(make_application):
    application = make_application()

    with pytest.raises(IntegrityError), transaction.atomic():
        Application.objects.create(
            candidate=application.candidate, job=application.job, source=ApplicationSource.OTHER
        )

    assert Application.objects.count() == 1


def test_make_application_fixture_builds_an_application_at_the_given_stage(make_application):
    application = make_application(Stage.INTERVIEW)

    application.refresh_from_db()
    assert application.stage == Stage.INTERVIEW


def test_a_candidate_can_apply_to_several_jobs_and_the_page_lists_them_all(
    staff_client, candidate, open_job, make_application
):
    second_job = JobOpening.objects.create(
        title="Frontend Developer", department="Engineering", description="Build UIs."
    )
    make_application()
    make_application(Stage.SCREENING, job=second_job)

    response = staff_client.get(candidate.get_absolute_url())

    assert list(response.context["applications"].values_list("job__title", flat=True)) == [
        "Frontend Developer",
        "Backend Developer",
    ]
    page = response.content.decode()
    assert "Screening" in page
    assert "Applied" in page


def test_the_candidate_page_says_when_there_are_no_applications(staff_client, candidate):
    page = staff_client.get(candidate.get_absolute_url()).content.decode()

    assert "No applications yet." in page


def test_a_candidate_with_applications_cannot_be_deleted(make_application):
    application = make_application()

    with pytest.raises(ProtectedError):
        application.candidate.delete()


@pytest.mark.parametrize("job_fixture", ["closed_job", "applied_job"])
def test_posting_a_job_the_form_does_not_offer_is_refused_without_saving(
    request, staff_client, candidate, make_application, job_fixture
):
    if job_fixture == "applied_job":
        job = make_application().job
    else:
        job = request.getfixturevalue(job_fixture)

    response = staff_client.post(
        reverse("tracker:candidate_apply", args=[candidate.pk]),
        {"job": job.pk, "source": ApplicationSource.JOB_BOARD},
    )

    assert response.status_code == 200
    assert "job" in response.context["form"].errors
    assert Application.objects.filter(candidate=candidate, job=job).count() == (
        1 if job_fixture == "applied_job" else 0
    )


def test_apply_form_requires_a_job_and_a_source(staff_client, candidate, open_job):
    response = staff_client.post(reverse("tracker:candidate_apply", args=[candidate.pk]), {})

    assert response.status_code == 200
    assert set(response.context["form"].errors) == {"job", "source"}
    assert not Application.objects.exists()


def test_the_apply_page_requires_login(client, candidate):
    url = reverse("tracker:candidate_apply", args=[candidate.pk])

    response = client.get(url)

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))
