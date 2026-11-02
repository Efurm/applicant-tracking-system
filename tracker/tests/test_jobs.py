from django.urls import reverse
from django.utils.html import escape

from tracker import services
from tracker.models import EmploymentType, JobOpening, JobStatus, Skill, Stage
from tracker.tests.html import marked


def test_job_list_filters_by_status_from_the_url(staff_client, open_job, closed_job):
    url = reverse("tracker:job_list")

    assert list(staff_client.get(url).context["jobs"]) == [open_job, closed_job]
    assert list(staff_client.get(url, {"status": "open"}).context["jobs"]) == [open_job]
    assert list(staff_client.get(url, {"status": "closed"}).context["jobs"]) == [closed_job]
    assert list(staff_client.get(url, {"status": "bogus"}).context["jobs"]) == [
        open_job,
        closed_job,
    ]


def test_admin_creates_a_job_with_several_skills_that_other_jobs_can_share(admin_client, open_job):
    python, sql, excel = (Skill.objects.create(name=n) for n in ["Python", "SQL", "Excel"])
    open_job.skills.add(python)

    response = admin_client.post(
        reverse("tracker:job_create"),
        {
            "title": "Data Engineer",
            "department": "Engineering",
            "location": "Remote",
            "employment_type": EmploymentType.CONTRACT,
            "description": "Build pipelines.",
            "skills": [python.pk, sql.pk],
        },
    )

    job = JobOpening.objects.get(title="Data Engineer")
    assert response.status_code == 302
    assert response.url == job.get_absolute_url()
    assert (job.department, job.location, job.employment_type, job.status) == (
        "Engineering",
        "Remote",
        EmploymentType.CONTRACT,
        JobStatus.OPEN,
    )
    assert job.description == "Build pipelines."
    assert list(job.skills.all()) == [python, sql]
    assert list(python.job_openings.all()) == [open_job, job]


def job_form_data(**overrides):
    data = {
        "title": "Data Engineer",
        "department": "Engineering",
        "location": "",
        "employment_type": EmploymentType.FULL_TIME,
        "description": "Build pipelines.",
    }
    return data | overrides


def test_staff_can_view_jobs_but_are_refused_on_create_and_edit(staff_client, open_job):
    assert staff_client.get(reverse("tracker:job_list")).status_code == 200
    assert staff_client.get(open_job.get_absolute_url()).status_code == 200

    create_url = reverse("tracker:job_create")
    edit_url = reverse("tracker:job_edit", args=[open_job.pk])
    assert staff_client.get(create_url).status_code == 403
    assert staff_client.get(edit_url).status_code == 403
    assert staff_client.post(create_url, job_form_data()).status_code == 403
    assert staff_client.post(edit_url, job_form_data(title="Hacked")).status_code == 403

    open_job.refresh_from_db()
    assert open_job.title == "Backend Developer"
    assert JobOpening.objects.count() == 1


def test_staff_see_no_create_or_edit_controls(staff_client, open_job):
    list_page = staff_client.get(reverse("tracker:job_list")).content.decode()
    detail_page = staff_client.get(open_job.get_absolute_url()).content.decode()

    assert reverse("tracker:job_create") not in list_page
    assert reverse("tracker:job_edit", args=[open_job.pk]) not in detail_page


def test_admin_sees_create_and_edit_controls(admin_client, open_job):
    list_page = admin_client.get(reverse("tracker:job_list")).content.decode()
    detail_page = admin_client.get(open_job.get_absolute_url()).content.decode()

    assert reverse("tracker:job_create") in list_page
    assert reverse("tracker:job_edit", args=[open_job.pk]) in detail_page
    assert admin_client.get(reverse("tracker:job_create")).status_code == 200
    assert admin_client.get(reverse("tracker:job_edit", args=[open_job.pk])).status_code == 200


def test_job_pages_require_login(client, open_job):
    for url in [
        reverse("tracker:job_list"),
        reverse("tracker:job_create"),
        open_job.get_absolute_url(),
        reverse("tracker:job_edit", args=[open_job.pk]),
    ]:
        response = client.get(url)
        assert response.status_code == 302, url
        assert response.url == f"{reverse('login')}?next={url}"


def test_create_form_requires_title_department_and_description(admin_client, db):
    response = admin_client.post(reverse("tracker:job_create"), {})

    assert response.status_code == 200
    assert set(response.context["form"].errors) == {
        "title",
        "department",
        "employment_type",
        "description",
    }
    assert not JobOpening.objects.exists()


def test_a_job_can_be_created_without_skills_or_location(admin_client, db):
    response = admin_client.post(reverse("tracker:job_create"), job_form_data())

    assert response.status_code == 302
    job = JobOpening.objects.get()
    assert job.location == ""
    assert not job.skills.exists()


def test_admin_edits_a_job_and_replaces_its_skills(admin_client, open_job):
    python, sql = Skill.objects.create(name="Python"), Skill.objects.create(name="SQL")
    open_job.skills.add(python)

    response = admin_client.post(
        reverse("tracker:job_edit", args=[open_job.pk]),
        job_form_data(
            title="Senior Backend Developer",
            location="Austin, TX",
            employment_type=EmploymentType.PART_TIME,
            skills=[sql.pk],
        ),
    )

    assert response.status_code == 302
    assert response.url == open_job.get_absolute_url()
    open_job.refresh_from_db()
    assert open_job.title == "Senior Backend Developer"
    assert open_job.location == "Austin, TX"
    assert open_job.employment_type == EmploymentType.PART_TIME
    assert list(open_job.skills.all()) == [sql]


def test_editing_a_job_with_no_skills_checked_removes_them_all(admin_client, open_job):
    open_job.skills.add(Skill.objects.create(name="Python"))

    admin_client.post(reverse("tracker:job_edit", args=[open_job.pk]), job_form_data())

    assert not open_job.skills.exists()


def test_editing_a_job_keeps_its_status(admin_client, closed_job):
    admin_client.post(reverse("tracker:job_edit", args=[closed_job.pk]), job_form_data())

    closed_job.refresh_from_db()
    assert closed_job.status == JobStatus.CLOSED


def test_job_detail_shows_details_and_skills(staff_client, open_job):
    open_job.skills.add(Skill.objects.create(name="Django"), Skill.objects.create(name="SQL"))
    open_job.location = "Remote"
    open_job.save()

    page = staff_client.get(open_job.get_absolute_url()).content.decode()

    for text in [
        "Backend Developer",
        "Engineering",
        "Remote",
        "Full-time",
        "Build APIs.",
        "Django",
        "SQL",
    ]:
        assert text in page, text


def test_job_create_form_lists_every_skill_as_a_checkbox(admin_client, db):
    for name in ["SQL", "Python"]:
        Skill.objects.create(name=name)

    page = admin_client.get(reverse("tracker:job_create")).content.decode()

    assert page.count('type="checkbox" name="skills"') == 2
    assert page.index("Python") < page.index("SQL")


def test_nav_job_openings_link_points_to_the_job_list(staff_client):
    page = staff_client.get(reverse("tracker:home")).content.decode()

    assert f'href="{reverse("tracker:job_list")}">Job Openings</a>' in page


def test_admin_closes_an_open_job_and_reopens_it(admin_client, open_job):
    close_url = reverse("tracker:job_close", args=[open_job.pk])
    reopen_url = reverse("tracker:job_reopen", args=[open_job.pk])

    response = admin_client.post(close_url, follow=True)

    open_job.refresh_from_db()
    assert open_job.status == JobStatus.CLOSED
    assert response.redirect_chain == [(open_job.get_absolute_url(), 302)]
    assert escape('Closed "Backend Developer" to new applicants.') in response.content.decode()

    response = admin_client.post(reopen_url, follow=True)

    open_job.refresh_from_db()
    assert open_job.status == JobStatus.OPEN
    assert response.redirect_chain == [(open_job.get_absolute_url(), 302)]
    assert escape('Reopened "Backend Developer".') in response.content.decode()


def test_closed_jobs_are_labeled_closed_to_new_applicants(staff_client, open_job, closed_job):
    label = "Closed to new applicants"
    list_page = staff_client.get(reverse("tracker:job_list")).content.decode()
    closed_page = staff_client.get(closed_job.get_absolute_url()).content.decode()
    open_page = staff_client.get(open_job.get_absolute_url()).content.decode()

    assert list_page.count(label) == 1
    assert list_page.index("Data Analyst") < list_page.index(label)
    assert label in closed_page
    assert label not in open_page


def test_close_and_reopen_services_change_only_the_status(open_job):
    python = Skill.objects.create(name="Python")
    open_job.skills.add(python)

    services.close_job(open_job)
    open_job.refresh_from_db()
    assert open_job.status == JobStatus.CLOSED
    assert not open_job.is_open

    services.reopen_job(open_job)
    open_job.refresh_from_db()
    assert open_job.status == JobStatus.OPEN
    assert (open_job.title, open_job.department) == ("Backend Developer", "Engineering")
    assert list(open_job.skills.all()) == [python]


def test_closing_a_closed_job_or_reopening_an_open_one_is_harmless(open_job, closed_job):
    services.close_job(closed_job)
    services.reopen_job(open_job)

    closed_job.refresh_from_db()
    open_job.refresh_from_db()
    assert closed_job.status == JobStatus.CLOSED
    assert open_job.status == JobStatus.OPEN


def test_staff_are_refused_on_close_and_reopen(staff_client, open_job, closed_job):
    close_url = reverse("tracker:job_close", args=[open_job.pk])
    reopen_url = reverse("tracker:job_reopen", args=[closed_job.pk])

    assert staff_client.post(close_url).status_code == 403
    assert staff_client.post(reopen_url).status_code == 403
    assert staff_client.get(close_url).status_code == 403
    assert staff_client.get(reopen_url).status_code == 403

    open_job.refresh_from_db()
    closed_job.refresh_from_db()
    assert open_job.status == JobStatus.OPEN
    assert closed_job.status == JobStatus.CLOSED


def test_close_and_reopen_refuse_get_for_admins(admin_client, open_job, closed_job):
    assert admin_client.get(reverse("tracker:job_close", args=[open_job.pk])).status_code == 405
    assert admin_client.get(reverse("tracker:job_reopen", args=[closed_job.pk])).status_code == 405

    open_job.refresh_from_db()
    assert open_job.status == JobStatus.OPEN


def test_close_and_reopen_require_login(client, open_job):
    for name in ["tracker:job_close", "tracker:job_reopen"]:
        url = reverse(name, args=[open_job.pk])
        response = client.post(url)
        assert response.status_code == 302, url
        assert response.url == f"{reverse('login')}?next={url}"
    open_job.refresh_from_db()
    assert open_job.status == JobStatus.OPEN


def test_close_and_reopen_of_a_missing_job_is_404(admin_client, db):
    assert admin_client.post(reverse("tracker:job_close", args=[999])).status_code == 404
    assert admin_client.post(reverse("tracker:job_reopen", args=[999])).status_code == 404


def test_admin_sees_close_on_open_jobs_and_reopen_on_closed_jobs(
    admin_client, open_job, closed_job
):
    open_page = admin_client.get(open_job.get_absolute_url()).content.decode()
    closed_page = admin_client.get(closed_job.get_absolute_url()).content.decode()

    assert reverse("tracker:job_close", args=[open_job.pk]) in open_page
    assert reverse("tracker:job_reopen", args=[open_job.pk]) not in open_page
    assert reverse("tracker:job_reopen", args=[closed_job.pk]) in closed_page
    assert reverse("tracker:job_close", args=[closed_job.pk]) not in closed_page


def test_staff_see_no_close_or_reopen_controls(staff_client, open_job, closed_job):
    open_page = staff_client.get(open_job.get_absolute_url()).content.decode()
    closed_page = staff_client.get(closed_job.get_absolute_url()).content.decode()

    assert reverse("tracker:job_close", args=[open_job.pk]) not in open_page
    assert reverse("tracker:job_reopen", args=[closed_job.pk]) not in closed_page


def _candidates(count):
    return [
        services.create_candidate(
            first_name=f"Person{i}", last_name="Test", email=f"p{i}@example.com"
        )
        for i in range(count)
    ]


def test_stage_counts_cover_every_stage_in_order_for_that_job_only(make_application, open_job):
    other_job = services.create_job(
        title="Recruiter", department="People", employment_type=EmploymentType.FULL_TIME
    )
    first, second, third, fourth = _candidates(4)
    make_application(Stage.SCREENING, candidate=first)
    make_application(Stage.SCREENING, candidate=second)
    make_application(Stage.REJECTED, candidate=third)
    make_application(Stage.OFFER, candidate=fourth, job=other_job)

    counts = services.stage_counts(open_job)

    assert counts == [
        (Stage.APPLIED, 0),
        (Stage.SCREENING, 2),
        (Stage.INTERVIEW, 0),
        (Stage.FINAL_REVIEW, 0),
        (Stage.OFFER, 0),
        (Stage.HIRED, 0),
        (Stage.REJECTED, 1),
        (Stage.WITHDRAWN, 0),
    ]


def test_job_page_links_each_stage_count_to_the_filtered_workspace(
    staff_client, make_application, open_job
):
    first, second = _candidates(2)
    make_application(Stage.INTERVIEW, candidate=first)
    make_application(Stage.HIRED, candidate=second)

    response = staff_client.get(open_job.get_absolute_url())

    workspace = reverse("tracker:application_workspace")
    expected_counts = {Stage.INTERVIEW: 1, Stage.HIRED: 1}
    assert [
        (value, attrs["href"], text) for value, attrs, text in marked(response, "data-stage-count")
    ] == [
        (
            stage.value,
            f"{workspace}?job={open_job.pk}&stage={stage.value}",
            f"{stage.label} {expected_counts.get(stage, 0)}",
        )
        for stage in Stage
    ]


def test_a_stage_count_link_opens_the_workspace_on_that_jobs_applications_in_that_stage(
    staff_client, make_application, open_job
):
    other_job = services.create_job(
        title="Recruiter", department="People", employment_type=EmploymentType.FULL_TIME
    )
    first, second, third = _candidates(3)
    hired = make_application(Stage.HIRED, candidate=first)
    make_application(Stage.INTERVIEW, candidate=second)
    make_application(Stage.HIRED, candidate=third, job=other_job)
    page = staff_client.get(open_job.get_absolute_url())
    hired_link = next(
        attrs["href"]
        for value, attrs, _ in marked(page, "data-stage-count")
        if value == Stage.HIRED
    )

    response = staff_client.get(hired_link)

    assert list(response.context["applications"]) == [hired]
