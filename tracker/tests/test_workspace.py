from django.urls import reverse
from django.utils import dateformat, timezone

from tracker import services
from tracker.models import Candidate, JobOpening, Stage
from tracker.tests.html import marked as _marked

WORKSPACE_URL = reverse("tracker:application_workspace")


def _listed(response):
    return set(response.context["applications"])


def test_with_no_parameters_the_workspace_lists_in_progress_applications_across_all_jobs(
    staff_client, candidate, open_job, make_application
):
    other = Candidate.objects.create(first_name="Ana", last_name="Diaz", email="ana@example.com")
    third = Candidate.objects.create(first_name="Lee", last_name="Wong", email="lee@example.com")
    second_job = JobOpening.objects.create(
        title="Data Analyst", department="Finance", description="Analyze data."
    )
    applied = make_application()
    offer = make_application(Stage.OFFER, candidate=other)
    make_application(Stage.REJECTED, candidate=third)
    interview = make_application(Stage.INTERVIEW, job=second_job)
    make_application(Stage.HIRED, candidate=other, job=second_job)
    make_application(Stage.WITHDRAWN, candidate=third, job=second_job)
    services.close_job(second_job)  # closing a job keeps its in-progress applications listed

    response = staff_client.get(WORKSPACE_URL)

    assert response.status_code == 200
    assert _listed(response) == {applied, offer, interview}


def test_job_stage_and_name_filters_narrow_the_list_and_are_restored_from_the_url(
    staff_client, candidate, open_job, make_application
):
    other = Candidate.objects.create(first_name="Ana", last_name="Diaz", email="ana@example.com")
    second_job = JobOpening.objects.create(
        title="Data Analyst", department="Finance", description="Analyze data."
    )
    jo_backend = make_application(Stage.SCREENING)
    jo_data = make_application(Stage.HIRED, job=second_job)
    ana_backend = make_application(Stage.REJECTED, candidate=other)
    ana_data = make_application(Stage.SCREENING, candidate=other, job=second_job)

    def get(**params):
        response = staff_client.get(WORKSPACE_URL, params)
        assert response.status_code == 200
        return response

    # Job alone keeps the in-progress default.
    response = get(job=second_job.pk)
    assert _listed(response) == {ana_data}
    assert (response.context["job"], response.context["stage"]) == (second_job, "")

    # A specific stage, including a final one.
    assert _listed(get(stage=Stage.SCREENING)) == {jo_backend, ana_data}
    assert _listed(get(stage=Stage.REJECTED)) == {ana_backend}

    # "all" includes final stages.
    response = get(stage="all", job=open_job.pk)
    assert _listed(response) == {jo_backend, ana_backend}
    assert (response.context["job"], response.context["stage"]) == (open_job, "all")

    # Name search matches first or last name, any case, and combines with the other filters.
    response = get(q="PARK", stage="all")
    assert _listed(response) == {jo_backend, jo_data}
    assert response.context["query"] == "PARK"
    assert _listed(get(q="ana diaz", stage="all", job=second_job.pk)) == {ana_data}
    assert _listed(get(q="jo park", stage=Stage.HIRED)) == {jo_data}

    # Unknown values are ignored: back to the in-progress default across all jobs.
    response = get(job="999", stage="bogus")
    assert _listed(response) == {jo_backend, ana_data}
    assert (response.context["job"], response.context["stage"]) == (None, "")
    assert _listed(get(job="not-a-number")) == {jo_backend, ana_data}


def test_selecting_an_application_shows_its_details_and_the_candidates_other_applications(
    staff_client, candidate, open_job, make_application
):
    candidate.profile_url = "https://www.linkedin.com/in/jopark"
    candidate.resume_url = "https://example.com/jo-park-resume.pdf"
    candidate.save()
    second_job = JobOpening.objects.create(
        title="Data Analyst", department="Finance", description="Analyze data."
    )
    selected = make_application(Stage.INTERVIEW, job=second_job)
    selected.source_details = "LinkedIn"
    selected.save()
    other = make_application(Stage.HIRED)
    services.close_job(second_job)
    ana = Candidate.objects.create(first_name="Ana", last_name="Diaz", email="ana@example.com")
    make_application(candidate=ana)  # someone else's application is not "other"

    response = staff_client.get(
        WORKSPACE_URL, {"stage": "all", "q": "park", "selected": selected.pk}
    )

    assert response.status_code == 200
    fields = {value: text for value, _, text in _marked(response, "data-panel-field")}
    assert fields == {
        "name": "Jo Park",
        "email": "jo.park@example.com",
        "phone": "555-0100",
        "profile_url": "https://www.linkedin.com/in/jopark",
        "resume_url": "https://example.com/jo-park-resume.pdf",
        "job": "Data Analyst",
        "job_status": "Closed",
        "source": "Job Board",
        "source_details": "LinkedIn",
        "applied_on": dateformat.format(timezone.localdate(), "M j, Y"),
        "stage": "Interview",
    }
    steps = [
        (value, attrs["data-step-state"]) for value, attrs, _ in _marked(response, "data-step")
    ]
    assert steps == [
        ("applied", "done"),
        ("screening", "done"),
        ("interview", "current"),
        ("final_review", "todo"),
        ("offer", "todo"),
        ("hired", "todo"),
    ]
    others = [
        (value, attrs["href"], text)
        for value, attrs, text in _marked(response, "data-other-application")
    ]
    assert others == [
        (
            str(other.pk),
            f"{WORKSPACE_URL}?stage=all&q=park&selected={other.pk}",
            "Backend Developer · Hired",
        )
    ]

    # Without a selection (or with one that doesn't exist) there is no panel.
    for params in ({}, {"selected": "999"}, {"selected": "abc"}):
        response = staff_client.get(WORKSPACE_URL, params)
        assert response.status_code == 200
        assert _marked(response, "data-panel-field") == []


def test_the_workspace_requires_login(client, db):
    response = client.get(WORKSPACE_URL, {"stage": "all"})

    assert response.status_code == 302
    assert response.url.startswith(f"{reverse('login')}?next=")


def test_admins_see_the_same_workspace(admin_client, make_application):
    application = make_application()

    response = admin_client.get(WORKSPACE_URL, {"selected": application.pk})

    assert _listed(response) == {application}
    assert [value for value, _, _ in _marked(response, "data-panel")] == [str(application.pk)]


def test_the_nav_workspace_link_opens_the_workspace(staff_client):
    response = staff_client.get(reverse("tracker:home"))

    assert f'<a href="{WORKSPACE_URL}">Workspace</a>' in response.content.decode()


def test_the_list_rows_link_to_each_application_and_highlight_the_selected_one(
    staff_client, candidate, open_job, make_application
):
    other = Candidate.objects.create(first_name="Ana", last_name="Diaz", email="ana@example.com")
    jo = make_application(Stage.SCREENING)
    ana = make_application(Stage.OFFER, candidate=other)

    response = staff_client.get(WORKSPACE_URL, {"job": open_job.pk, "selected": jo.pk})

    rows = {
        value: (attrs, text) for value, attrs, text in _marked(response, "data-application-row")
    }
    assert set(rows) == {str(jo.pk), str(ana.pk)}
    highlighted = [
        attrs for value, attrs, _ in _marked(response, "aria-current") if value == "true"
    ]
    assert [attrs["href"] for attrs in highlighted] == [
        f"{WORKSPACE_URL}?job={open_job.pk}&selected={jo.pk}"
    ]
    assert "Ana Diaz" in rows[str(ana.pk)][1] and "Offer" in rows[str(ana.pk)][1]


def test_the_filter_controls_show_the_values_restored_from_the_url(
    staff_client, open_job, closed_job
):
    response = staff_client.get(
        WORKSPACE_URL, {"job": closed_job.pk, "stage": Stage.WITHDRAWN, "q": "park"}
    )

    selected_options = [attrs["value"] for _, attrs, _ in _marked(response, "selected")]
    assert selected_options == [str(closed_job.pk), Stage.WITHDRAWN]
    search = [attrs for _, attrs, _ in _marked(response, "name") if attrs["name"] == "q"]
    assert search[0]["value"] == "park"

    default = staff_client.get(WORKSPACE_URL)
    # "All jobs" is the first option, so only the stage's "In progress" needs ``selected``.
    assert [attrs["value"] for _, attrs, _ in _marked(default, "selected")] == [""]


def test_the_tracker_for_final_stages(staff_client, make_application):
    application = make_application(Stage.HIRED)

    response = staff_client.get(WORKSPACE_URL, {"selected": application.pk})
    states = [attrs["data-step-state"] for _, attrs, _ in _marked(response, "data-step")]
    assert states == ["done"] * 5 + ["current"]

    application.stage = Stage.REJECTED
    application.save()
    response = staff_client.get(WORKSPACE_URL, {"selected": application.pk})
    states = [attrs["data-step-state"] for _, attrs, _ in _marked(response, "data-step")]
    assert states == ["todo"] * 6
    assert "This application ended as <strong>Rejected</strong>." in response.content.decode()


def test_the_panel_shows_dashes_for_missing_contact_details_and_no_other_applications(
    staff_client, make_application
):
    application = make_application()
    application.candidate.phone = ""
    application.candidate.save()

    response = staff_client.get(WORKSPACE_URL, {"selected": application.pk})

    fields = {value: text for value, _, text in _marked(response, "data-panel-field")}
    assert (fields["phone"], fields["profile_url"], fields["resume_url"]) == ("—", "—", "—")
    assert fields["job_status"] == "Open"
    assert "source_details" not in fields
    assert _marked(response, "data-other-application") == []
    assert "Other applications by this candidate" not in response.content.decode()


def test_an_empty_list_says_so(staff_client, db):
    response = staff_client.get(WORKSPACE_URL, {"q": "nobody"})

    assert "No matching applications." in response.content.decode()
