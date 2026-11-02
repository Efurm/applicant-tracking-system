import pytest

from accounts.models import Role, User

TEST_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="alice.admin",
        password=TEST_PASSWORD,
        first_name="Alice",
        last_name="Admin",
        role=Role.ADMIN,
    )


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="sam.staff",
        password=TEST_PASSWORD,
        first_name="Sam",
        last_name="Staff",
        role=Role.STAFF,
    )


@pytest.fixture
def admin_client(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def staff_client(client, staff_user):
    client.force_login(staff_user)
    return client
