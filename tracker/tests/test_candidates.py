import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils.html import escape

from tracker import services
from tracker.models import IN_PROGRESS_STAGES, Candidate, Stage
from tracker.tests.html import marked


def test_database_refuses_a_second_candidate_whose_email_differs_only_in_case(db):
    Candidate.objects.create(first_name="Jo", last_name="Park", email="jo.park@example.com")

    with pytest.raises(IntegrityError), transaction.atomic():
        Candidate.objects.create(first_name="Joanne", last_name="Park", email="Jo.Park@Example.COM")

    assert Candidate.objects.count() == 1


def test_create_form_refuses_a_duplicate_email_and_links_to_the_existing_candidate(
    staff_client,
):
    existing = Candidate.objects.create(
        first_name="Jo", last_name="Park", email="jo.park@example.com"
    )

    response = staff_client.post(
        reverse("tracker:candidate_create"),
        {"first_name": "Joanne", "last_name": "Park", "email": "JO.PARK@example.com"},
    )

    assert response.status_code == 200
    assert Candidate.objects.count() == 1
    email_errors = response.context["form"].errors.get("email", [])
    assert len(email_errors) == 1
    assert f'<a href="{existing.get_absolute_url()}"' in response.content.decode()


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("park", {"Jo Park"}),
        ("RIVERA", {"Ana Rivera"}),
        ("ana", {"Ana Rivera", "Diana Okafor"}),
        ("@bigcorp", {"Diana Okafor"}),
        ("", {"Jo Park", "Ana Rivera", "Diana Okafor"}),
    ],
)
def test_candidate_list_search_matches_first_name_last_name_or_email_ignoring_case(
    staff_client, query, expected
):
    Candidate.objects.create(first_name="Jo", last_name="Park", email="jo@example.com")
    Candidate.objects.create(first_name="Ana", last_name="Rivera", email="ana.r@example.com")
    Candidate.objects.create(first_name="Diana", last_name="Okafor", email="dokafor@bigcorp.io")

    response = staff_client.get(reverse("tracker:candidate_list"), {"q": query})

    assert response.status_code == 200
    assert {c.full_name for c in response.context["candidates"]} == expected


@pytest.mark.parametrize(
    "url_name",
    ["candidate_list", "candidate_create", "candidate_detail", "candidate_edit"],
)
def test_candidate_pages_require_login(client, candidate, url_name):
    args = [candidate.pk] if url_name in {"candidate_detail", "candidate_edit"} else []
    url = reverse(f"tracker:{url_name}", args=args)

    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={url}"


@pytest.mark.parametrize("client_fixture", ["staff_client", "admin_client"])
def test_both_roles_can_open_every_candidate_page(request, candidate, client_fixture):
    client = request.getfixturevalue(client_fixture)

    for url in [
        reverse("tracker:candidate_list"),
        reverse("tracker:candidate_create"),
        candidate.get_absolute_url(),
        reverse("tracker:candidate_edit", args=[candidate.pk]),
    ]:
        assert client.get(url).status_code == 200, url


def test_creating_a_candidate_with_every_field_redirects_to_their_page(staff_client):
    data = {
        "first_name": "Ana",
        "last_name": "Rivera",
        "email": "Ana.Rivera@Example.com",
        "phone": "555-0199",
        "profile_url": "https://www.linkedin.com/in/ana-rivera",
        "resume_url": "https://example.com/ana-rivera.pdf",
        "notes": "Met at the spring career fair.",
    }

    response = staff_client.post(reverse("tracker:candidate_create"), data)

    candidate = Candidate.objects.get()
    assert response.status_code == 302
    assert response.url == candidate.get_absolute_url()
    assert candidate.email == "ana.rivera@example.com"
    for field in ["first_name", "last_name", "phone", "profile_url", "resume_url", "notes"]:
        assert getattr(candidate, field) == data[field]
    assert candidate.archived is False

    page = staff_client.get(response.url).content.decode()
    assert "Ana Rivera" in page
    assert "Met at the spring career fair." in page
    assert "https://example.com/ana-rivera.pdf" in page


def test_only_first_name_last_name_and_email_are_required(staff_client):
    response = staff_client.post(reverse("tracker:candidate_create"), {})

    assert response.status_code == 200
    assert set(response.context["form"].errors) == {"first_name", "last_name", "email"}

    response = staff_client.post(
        reverse("tracker:candidate_create"),
        {"first_name": "Lee", "last_name": "Chen", "email": "lee@example.com"},
    )

    assert response.status_code == 302
    assert Candidate.objects.filter(email="lee@example.com").exists()


def test_editing_a_candidate_saves_changes_and_redirects_to_their_page(staff_client, candidate):
    url = reverse("tracker:candidate_edit", args=[candidate.pk])
    data = {
        "first_name": "Joanne",
        "last_name": "Park",
        "email": "JO.PARK@example.com",
        "phone": "",
        "notes": "Prefers email.",
    }

    response = staff_client.post(url, data)

    assert response.status_code == 302
    assert response.url == candidate.get_absolute_url()
    candidate.refresh_from_db()
    assert candidate.first_name == "Joanne"
    assert candidate.email == "jo.park@example.com"
    assert candidate.phone == ""
    assert candidate.notes == "Prefers email."


def test_editing_a_candidate_to_another_candidates_email_is_refused(staff_client, candidate):
    other = Candidate.objects.create(first_name="Ana", last_name="Rivera", email="ana@example.com")
    url = reverse("tracker:candidate_edit", args=[other.pk])

    response = staff_client.post(
        url, {"first_name": "Ana", "last_name": "Rivera", "email": "Jo.Park@example.com"}
    )

    assert response.status_code == 200
    assert f'<a href="{candidate.get_absolute_url()}"' in response.content.decode()
    other.refresh_from_db()
    assert other.email == "ana@example.com"


def test_create_candidate_service_refuses_a_duplicate_email_even_without_the_form(candidate):
    with pytest.raises(services.DuplicateCandidateEmail) as excinfo:
        services.create_candidate(first_name="J", last_name="P", email=" JO.PARK@EXAMPLE.COM ")

    assert excinfo.value.existing == candidate
    assert Candidate.objects.count() == 1


def test_missing_candidate_returns_404(staff_client, db):
    assert staff_client.get(reverse("tracker:candidate_detail", args=[999])).status_code == 404


def test_nav_links_to_the_candidate_list(staff_client):
    page = staff_client.get(reverse("tracker:home")).content.decode()

    assert f'href="{reverse("tracker:candidate_list")}"' in page


@pytest.mark.parametrize("stage", IN_PROGRESS_STAGES)
def test_archiving_is_refused_while_the_candidate_has_an_application_in_progress(
    stage, candidate, make_application
):
    make_application(stage)

    with pytest.raises(services.CandidateHasApplicationsInProgress) as refusal:
        services.archive_candidate(candidate)

    assert refusal.value.in_progress_count == 1
    candidate.refresh_from_db()
    assert candidate.archived is False


@pytest.mark.parametrize("stage", [Stage.APPLIED, Stage.HIRED, Stage.WITHDRAWN])
def test_deleting_is_refused_when_the_candidate_has_any_application_and_suggests_archiving(
    stage, candidate, make_application
):
    make_application(stage)

    with pytest.raises(services.CandidateHasApplications) as refusal:
        services.delete_candidate(candidate)

    assert refusal.value.application_count == 1
    assert "Archive them instead." in refusal.value.message
    assert Candidate.objects.filter(pk=candidate.pk).exists()


def test_archiving_succeeds_once_every_application_is_final_and_unarchiving_reverses_it(
    candidate, make_application
):
    make_application(Stage.HIRED)

    services.archive_candidate(candidate)
    candidate.refresh_from_db()
    assert candidate.archived is True

    services.unarchive_candidate(candidate)
    candidate.refresh_from_db()
    assert candidate.archived is False


def test_archiving_a_candidate_with_no_applications_is_allowed(candidate):
    services.archive_candidate(candidate)

    candidate.refresh_from_db()
    assert candidate.archived is True


def test_a_candidate_with_no_applications_can_be_deleted(candidate):
    services.delete_candidate(candidate)

    assert not Candidate.objects.filter(pk=candidate.pk).exists()


@pytest.mark.parametrize("action", ["archive", "unarchive", "delete"])
def test_staff_are_refused_on_candidate_admin_actions_and_nothing_changes(
    staff_client, candidate, archived_candidate, action
):
    target = archived_candidate if action == "unarchive" else candidate
    url = reverse(f"tracker:candidate_{action}", args=[target.pk])

    assert staff_client.post(url).status_code == 403
    assert staff_client.get(url).status_code == 403

    target.refresh_from_db()
    assert target.archived is (action == "unarchive")


@pytest.mark.parametrize("action", ["archive", "unarchive", "delete"])
def test_candidate_admin_actions_require_post(admin_client, candidate, action):
    url = reverse(f"tracker:candidate_{action}", args=[candidate.pk])

    assert admin_client.get(url).status_code == 405


def test_staff_see_no_archive_or_delete_buttons(staff_client, candidate):
    response = staff_client.get(candidate.get_absolute_url())

    assert marked(response, "data-candidate-action") == []


def test_admins_see_archive_and_delete_for_an_active_candidate_and_unarchive_when_archived(
    admin_client, candidate, archived_candidate
):
    active = marked(admin_client.get(candidate.get_absolute_url()), "data-candidate-action")
    archived = marked(
        admin_client.get(archived_candidate.get_absolute_url()), "data-candidate-action"
    )

    assert [value for value, _, _ in active] == ["archive", "delete"]
    assert [value for value, _, _ in archived] == ["unarchive", "delete"]


def test_admin_archives_a_candidate_from_their_page(admin_client, candidate):
    response = admin_client.post(
        reverse("tracker:candidate_archive", args=[candidate.pk]), follow=True
    )

    assert response.redirect_chain == [(candidate.get_absolute_url(), 302)]
    assert escape(f"Archived {candidate.full_name}.") in response.content.decode()
    [(_, _, badge)] = marked(response, "data-archived-badge")
    assert badge == "Archived"
    assert marked(response, "data-apply-link") == []
    candidate.refresh_from_db()
    assert candidate.archived is True


def test_admin_archive_is_refused_with_a_message_while_an_application_is_in_progress(
    admin_client, candidate, make_application
):
    make_application(Stage.INTERVIEW)

    response = admin_client.post(
        reverse("tracker:candidate_archive", args=[candidate.pk]), follow=True
    )

    assert response.redirect_chain == [(candidate.get_absolute_url(), 302)]
    assert (
        escape(f"{candidate.full_name} can't be archived while 1 application is still in progress.")
        in response.content.decode()
    )
    candidate.refresh_from_db()
    assert candidate.archived is False


def test_admin_unarchives_a_candidate(admin_client, archived_candidate):
    response = admin_client.post(
        reverse("tracker:candidate_unarchive", args=[archived_candidate.pk]), follow=True
    )

    assert response.redirect_chain == [(archived_candidate.get_absolute_url(), 302)]
    assert escape(f"Unarchived {archived_candidate.full_name}.") in response.content.decode()
    assert len(marked(response, "data-apply-link")) == 1
    archived_candidate.refresh_from_db()
    assert archived_candidate.archived is False


def test_admin_deletes_a_candidate_with_no_applications(admin_client, candidate):
    response = admin_client.post(
        reverse("tracker:candidate_delete", args=[candidate.pk]), follow=True
    )

    assert response.redirect_chain == [(reverse("tracker:candidate_list"), 302)]
    assert escape(f"Deleted {candidate.full_name}.") in response.content.decode()
    assert not Candidate.objects.filter(pk=candidate.pk).exists()


def test_admin_delete_is_refused_and_suggests_archiving_when_there_are_applications(
    admin_client, candidate, make_application
):
    make_application(Stage.WITHDRAWN)

    response = admin_client.post(
        reverse("tracker:candidate_delete", args=[candidate.pk]), follow=True
    )

    assert response.redirect_chain == [(candidate.get_absolute_url(), 302)]
    assert (
        escape(
            f"{candidate.full_name} can't be deleted because they have 1 application. "
            "Archive them instead."
        )
        in response.content.decode()
    )
    assert Candidate.objects.filter(pk=candidate.pk).exists()


def test_candidate_list_hides_archived_candidates_unless_the_toggle_is_on(
    staff_client, candidate, archived_candidate
):
    url = reverse("tracker:candidate_list")

    default = staff_client.get(url)
    toggled = staff_client.get(url, {"archived": "1"})

    assert [int(pk) for pk, _, _ in marked(default, "data-candidate-row")] == [candidate.pk]
    [(_, toggle_attrs, _)] = marked(default, "data-show-archived")
    assert "checked" not in toggle_attrs
    shown = {int(pk) for pk, _, _ in marked(toggled, "data-candidate-row")}
    assert shown == {candidate.pk, archived_candidate.pk}
    [(_, toggle_attrs, _)] = marked(toggled, "data-show-archived")
    assert "checked" in toggle_attrs
    assert len(marked(toggled, "data-archived-badge")) == 1


def test_candidate_search_respects_the_archived_toggle(staff_client, archived_candidate):
    url = reverse("tracker:candidate_list")

    hidden = staff_client.get(url, {"q": "Kim"})
    shown = staff_client.get(url, {"q": "Kim", "archived": "1"})

    assert marked(hidden, "data-candidate-row") == []
    assert [int(pk) for pk, _, _ in marked(shown, "data-candidate-row")] == [archived_candidate.pk]
