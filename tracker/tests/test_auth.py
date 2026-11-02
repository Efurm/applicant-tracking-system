import pytest
from django.urls import reverse

from conftest import TEST_PASSWORD


def test_anonymous_visitor_is_redirected_to_login(client, db):
    home = reverse("tracker:home")

    response = client.get(home)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={home}"


@pytest.mark.parametrize(
    ("user_fixture", "sees_skills"),
    [("admin_user", True), ("staff_user", False)],
)
def test_skills_nav_link_is_shown_only_to_admins(client, request, user_fixture, sees_skills):
    client.force_login(request.getfixturevalue(user_fixture))

    response = client.get(reverse("tracker:home"))

    assert response.status_code == 200
    assert (">Skills</a>" in response.content.decode()) is sees_skills


def test_active_user_logs_in_and_sees_their_name_but_deactivated_user_is_refused(
    client, staff_user
):
    credentials = {"username": staff_user.username, "password": TEST_PASSWORD}

    response = client.post(reverse("login"), credentials, follow=True)

    assert response.wsgi_request.user == staff_user
    assert response.request["PATH_INFO"] == reverse("tracker:home")
    assert f"Signed in as <strong>{staff_user.username}</strong>" in response.content.decode()

    client.post(reverse("logout"))
    staff_user.is_active = False
    staff_user.save()

    response = client.post(reverse("login"), credentials, follow=True)

    assert not response.wsgi_request.user.is_authenticated
    assert response.request["PATH_INFO"] == reverse("login")
    assert "Please enter a correct username and password" in response.content.decode()


def test_logging_out_ends_the_session_and_shows_logged_out_page(staff_client):
    response = staff_client.post(reverse("logout"))

    assert response.status_code == 200
    assert "You have been logged out" in response.content.decode()
    assert staff_client.get(reverse("tracker:home")).status_code == 302
