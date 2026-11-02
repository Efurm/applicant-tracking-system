from django.core.management import call_command
from django.urls import reverse

from accounts.models import Role, User
from conftest import TEST_PASSWORD


def test_new_users_default_to_staff_without_admin_site_access(db):
    user = User.objects.create_user(username="new.hire", password=TEST_PASSWORD)

    assert user.role == Role.STAFF
    assert not user.is_admin
    assert not user.is_staff
    assert not user.is_superuser


def test_admin_role_grants_admin_site_access_and_staff_role_removes_it(admin_user):
    assert admin_user.is_admin
    assert admin_user.is_staff and admin_user.is_superuser

    admin_user.role = Role.STAFF
    admin_user.save()
    admin_user.refresh_from_db()

    assert not admin_user.is_staff and not admin_user.is_superuser


def test_createsuperuser_bootstraps_an_admin(db):
    call_command("createsuperuser", username="root", email="root@example.com", interactive=False)

    assert User.objects.get(username="root").role == Role.ADMIN


def test_admin_can_create_a_user_with_a_role_in_django_admin(admin_client):
    response = admin_client.post(
        reverse("admin:accounts_user_add"),
        {
            "username": "new.staffer",
            "role": Role.STAFF,
            "password1": "a-long-unusual-passphrase-42",
            "password2": "a-long-unusual-passphrase-42",
            "usable_password": "true",
        },
    )

    assert response.status_code == 302
    created = User.objects.get(username="new.staffer")
    assert created.role == Role.STAFF
    assert created.check_password("a-long-unusual-passphrase-42")


def test_admin_can_deactivate_a_user_in_django_admin(admin_client, staff_user):
    response = admin_client.post(
        reverse("admin:accounts_user_change", args=[staff_user.pk]),
        {
            "username": staff_user.username,
            "first_name": staff_user.first_name,
            "last_name": staff_user.last_name,
            "email": "",
            "role": Role.STAFF,
            # "is_active" omitted: an unchecked checkbox
        },
    )

    assert response.status_code == 302
    staff_user.refresh_from_db()
    assert not staff_user.is_active


def test_users_cannot_be_deleted_in_django_admin(admin_client, staff_user):
    response = admin_client.post(reverse("admin:accounts_user_delete", args=[staff_user.pk]))

    assert response.status_code == 403
    assert User.objects.filter(pk=staff_user.pk).exists()


def test_staff_users_cannot_open_django_admin(staff_client):
    response = staff_client.get(reverse("admin:index"))

    assert response.status_code == 302
    assert reverse("admin:login") in response.url
