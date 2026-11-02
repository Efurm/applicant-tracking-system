import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from tracker import services
from tracker.models import Skill


@pytest.fixture
def skill(db):
    return Skill.objects.create(name="Python")


def skill_urls(skill):
    return [
        reverse("tracker:skill_list"),
        reverse("tracker:skill_create"),
        reverse("tracker:skill_edit", args=[skill.pk]),
    ]


def test_only_admins_can_use_the_skill_pages(staff_client, admin_user, skill):
    for url in skill_urls(skill):
        assert staff_client.get(url).status_code == 403, url

    assert staff_client.post(reverse("tracker:skill_create"), {"name": "SQL"}).status_code == 403
    edit_url = reverse("tracker:skill_edit", args=[skill.pk])
    assert staff_client.post(edit_url, {"name": "Django"}).status_code == 403
    assert list(Skill.objects.values_list("name", flat=True)) == ["Python"]

    staff_client.force_login(admin_user)
    for url in skill_urls(skill):
        assert staff_client.get(url).status_code == 200, url


def test_database_refuses_a_second_skill_whose_name_differs_only_in_case(skill):
    with pytest.raises(IntegrityError), transaction.atomic():
        Skill.objects.create(name="python")

    assert Skill.objects.count() == 1


def test_admin_creates_a_skill_and_returns_to_the_list(admin_client):
    response = admin_client.post(reverse("tracker:skill_create"), {"name": "  Machine   Learning "})

    assert response.status_code == 302
    assert response.url == reverse("tracker:skill_list")
    assert Skill.objects.get().name == "Machine Learning"
    page = admin_client.get(response.url).content.decode()
    assert "Machine Learning" in page


def test_create_form_refuses_a_name_that_exists_in_another_capitalization(admin_client, skill):
    response = admin_client.post(reverse("tracker:skill_create"), {"name": "PYTHON"})

    assert response.status_code == 200
    assert response.context["form"].errors["name"] == ['A skill named "Python" already exists.']
    assert Skill.objects.count() == 1


def test_create_form_requires_a_name(admin_client, db):
    response = admin_client.post(reverse("tracker:skill_create"), {})

    assert response.status_code == 200
    assert set(response.context["form"].errors) == {"name"}
    assert not Skill.objects.exists()


def test_admin_renames_a_skill(admin_client, skill):
    response = admin_client.post(
        reverse("tracker:skill_edit", args=[skill.pk]), {"name": "Python 3"}
    )

    assert response.status_code == 302
    assert response.url == reverse("tracker:skill_list")
    skill.refresh_from_db()
    assert skill.name == "Python 3"


def test_renaming_a_skill_to_change_only_its_own_capitalization_is_allowed(admin_client):
    skill = Skill.objects.create(name="javascript")

    response = admin_client.post(
        reverse("tracker:skill_edit", args=[skill.pk]), {"name": "JavaScript"}
    )

    assert response.status_code == 302
    skill.refresh_from_db()
    assert skill.name == "JavaScript"


def test_renaming_a_skill_to_another_skills_name_is_refused(admin_client, skill):
    other = Skill.objects.create(name="SQL")

    response = admin_client.post(reverse("tracker:skill_edit", args=[other.pk]), {"name": "python"})

    assert response.status_code == 200
    assert response.context["form"].errors["name"] == ['A skill named "Python" already exists.']
    other.refresh_from_db()
    assert other.name == "SQL"


def test_create_skill_service_refuses_a_duplicate_even_without_the_form(skill):
    with pytest.raises(services.DuplicateSkillName) as excinfo:
        services.create_skill(" PYTHON ")

    assert excinfo.value.existing == skill
    assert Skill.objects.count() == 1


def test_skill_list_is_sorted_by_name_ignoring_case(admin_client, db):
    for name in ["sql", "Django", "AWS", "python"]:
        Skill.objects.create(name=name)

    response = admin_client.get(reverse("tracker:skill_list"))

    assert [s.name for s in response.context["skills"]] == ["AWS", "Django", "python", "sql"]


def test_skill_pages_require_login(client, skill):
    for url in skill_urls(skill):
        response = client.get(url)
        assert response.status_code == 302, url
        assert response.url == f"{reverse('login')}?next={url}"


def test_staff_refusal_shows_the_styled_forbidden_page(staff_client, skill):
    response = staff_client.get(reverse("tracker:skill_list"))

    assert response.status_code == 403
    page = response.content.decode()
    assert "You don't have access to this page" in page
    assert "Only Admins can do this." in page


def test_admin_nav_skills_link_points_to_the_skill_list(admin_client):
    page = admin_client.get(reverse("tracker:home")).content.decode()

    assert f'href="{reverse("tracker:skill_list")}">Skills</a>' in page
