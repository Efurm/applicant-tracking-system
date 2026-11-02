import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from tracker import services
from tracker.models import Candidate


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
