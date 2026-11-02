import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from tracker import services
from tracker.models import Application, ApplicationSource, Candidate, JobOpening, Stage


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


def test_create_application_refuses_an_archived_candidate(archived_candidate, open_job):
    with pytest.raises(services.CandidateArchived) as refused:
        services.create_application(archived_candidate, open_job, ApplicationSource.JOB_BOARD)

    assert refused.value.candidate == archived_candidate
    assert refused.value.message == (
        f"{archived_candidate.full_name} is archived, so they can't receive new applications."
    )
    assert not Application.objects.filter(candidate=archived_candidate).exists()


def test_an_archived_candidate_is_offered_no_jobs(archived_candidate, open_job):
    assert list(services.jobs_open_to(archived_candidate)) == []


@pytest.mark.parametrize("method", ["get", "post"])
def test_the_apply_page_turns_an_archived_candidate_away_without_saving(
    staff_client, archived_candidate, open_job, method
):
    response = getattr(staff_client, method)(
        reverse("tracker:candidate_apply", args=[archived_candidate.pk]),
        {"job": open_job.pk, "source": ApplicationSource.REFERRAL} if method == "post" else {},
        follow=True,
    )

    assert response.redirect_chain == [(archived_candidate.get_absolute_url(), 302)]
    assert (
        escape(
            f"{archived_candidate.full_name} is archived, so they can't receive new applications."
        )
        in response.content.decode()
    )
    assert not Application.objects.filter(candidate=archived_candidate).exists()
