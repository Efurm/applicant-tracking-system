import pytest
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.urls import reverse
from django.utils.html import escape

from tracker import services
from tracker.models import FINAL_STAGES, IN_PROGRESS_STAGES, JobOpening, Stage, StageChange
from tracker.tests.html import marked

WORKSPACE_URL = reverse("tracker:application_workspace")


ENDINGS = [Stage.REJECTED, Stage.WITHDRAWN]


@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        (
            Stage.APPLIED,
            [Stage.SCREENING, Stage.INTERVIEW, Stage.FINAL_REVIEW, Stage.OFFER, Stage.HIRED]
            + ENDINGS,
        ),
        (
            Stage.SCREENING,
            [Stage.INTERVIEW, Stage.FINAL_REVIEW, Stage.OFFER, Stage.HIRED] + ENDINGS,
        ),
        (Stage.INTERVIEW, [Stage.FINAL_REVIEW, Stage.OFFER, Stage.HIRED] + ENDINGS),
        (Stage.FINAL_REVIEW, [Stage.OFFER, Stage.HIRED] + ENDINGS),
        (Stage.OFFER, [Stage.HIRED] + ENDINGS),
        (Stage.HIRED, []),
        (Stage.REJECTED, []),
        (Stage.WITHDRAWN, []),
    ],
)
def test_allowed_next_stages_offers_later_stages_and_endings_then_locks_final_stages_for_staff(
    stage, expected, staff_user
):
    assert list(services.allowed_next_stages(stage, staff_user)) == expected


@pytest.mark.parametrize("stage", IN_PROGRESS_STAGES)
def test_admins_get_the_same_moves_as_staff_from_in_progress_stages(stage, admin_user, staff_user):
    assert list(services.allowed_next_stages(stage, admin_user)) == list(
        services.allowed_next_stages(stage, staff_user)
    )


def test_move_application_updates_the_stage_and_records_who_moved_it_even_on_a_closed_job(
    staff_user, open_job, make_application
):
    application = make_application(Stage.SCREENING)
    services.close_job(open_job)

    services.move_application(application, Stage.FINAL_REVIEW, staff_user)

    application.refresh_from_db()
    assert application.stage == Stage.FINAL_REVIEW
    change = application.stage_changes.last()
    assert (change.from_stage, change.to_stage, change.changed_by) == (
        Stage.SCREENING,
        Stage.FINAL_REVIEW,
        staff_user,
    )


@pytest.mark.parametrize("to_stage", [Stage.APPLIED, Stage.INTERVIEW, "not-a-stage"])
def test_move_application_refuses_backward_same_stage_and_unknown_moves_without_changing_data(
    to_stage, staff_user, make_application
):
    application = make_application(Stage.INTERVIEW)
    changes_before = list(StageChange.objects.values_list("pk", flat=True))

    with pytest.raises(services.InvalidStageMove) as refused:
        services.move_application(application, to_stage, staff_user)

    assert isinstance(refused.value, ValidationError)
    application.refresh_from_db()
    assert application.stage == Stage.INTERVIEW
    assert list(StageChange.objects.values_list("pk", flat=True)) == changes_before


@pytest.mark.parametrize("from_stage", IN_PROGRESS_STAGES)
@pytest.mark.parametrize("ending", ENDINGS)
def test_any_in_progress_application_can_be_rejected_or_withdrawn(
    from_stage, ending, staff_user, make_application
):
    application = make_application(from_stage)

    services.move_application(application, ending, staff_user)

    application.refresh_from_db()
    assert application.stage == ending
    assert application.is_final
    change = application.stage_changes.last()
    assert (change.from_stage, change.to_stage, change.changed_by) == (
        from_stage,
        ending,
        staff_user,
    )


def _move(client, application, stage):
    url = reverse("tracker:application_move", args=[application.pk])
    return client.post(url, {"stage": stage}, headers={"HX-Request": "true"})


def test_htmx_move_returns_the_updated_panel_and_an_out_of_band_list_row(
    staff_client, staff_user, make_application
):
    application = make_application(Stage.SCREENING)

    response = _move(staff_client, application, Stage.OFFER)

    assert response.status_code == 200
    assert b"<html" not in response.content
    assert [value for value, _, _ in marked(response, "data-panel")] == [str(application.pk)]
    stage_fields = [
        text for value, _, text in marked(response, "data-panel-field") if value == "stage"
    ]
    assert stage_fields == ["Offer"]
    [(row_pk, row_attrs, row_text)] = marked(response, "data-application-row")
    assert row_pk == str(application.pk)
    assert row_attrs["id"] == f"application-row-{application.pk}"
    assert row_attrs["hx-swap-oob"] == "true"
    assert "Offer" in row_text
    application.refresh_from_db()
    assert application.stage == Stage.OFFER
    assert application.stage_changes.last().changed_by == staff_user


def test_htmx_move_refuses_a_backward_move_in_place_without_changing_data(
    staff_client, make_application
):
    application = make_application(Stage.INTERVIEW)
    changes_before = list(StageChange.objects.values_list("pk", flat=True))

    response = _move(staff_client, application, Stage.SCREENING)

    assert response.status_code == 200
    assert b"<html" not in response.content
    assert [value for value, _, _ in marked(response, "data-panel")] == [str(application.pk)]
    [(_, _, error)] = marked(response, "data-move-error")
    assert error == "Can't move this application from Interview to Screening."
    application.refresh_from_db()
    assert application.stage == Stage.INTERVIEW
    assert list(StageChange.objects.values_list("pk", flat=True)) == changes_before


def test_htmx_reject_ends_the_application_and_shows_final_messaging(
    staff_client, staff_user, make_application
):
    application = make_application(Stage.FINAL_REVIEW)

    response = _move(staff_client, application, Stage.REJECTED)

    assert response.status_code == 200
    stage_fields = [
        text for value, _, text in marked(response, "data-panel-field") if value == "stage"
    ]
    assert stage_fields == ["Rejected"]
    assert marked(response, "data-move-form") == []
    assert len(marked(response, "data-final-message")) == 1
    [(_, _, row_text)] = marked(response, "data-application-row")
    assert "Rejected" in row_text
    application.refresh_from_db()
    assert application.stage == Stage.REJECTED
    assert application.stage_changes.last().changed_by == staff_user


@pytest.mark.parametrize("final_stage", FINAL_STAGES)
@pytest.mark.parametrize("to_stage", [Stage.APPLIED, Stage.OFFER, Stage.REJECTED, Stage.WITHDRAWN])
def test_a_direct_post_out_of_a_final_stage_is_refused_without_changing_data(
    final_stage, to_stage, staff_client, make_application
):
    application = make_application(final_stage)
    changes_before = list(StageChange.objects.values_list("pk", flat=True))

    response = _move(staff_client, application, to_stage)

    assert response.status_code == 200
    [(_, _, error)] = marked(response, "data-move-error")
    assert error == (
        f"Can't move this application from {Stage(final_stage).label} to {Stage(to_stage).label}."
    )
    assert marked(response, "data-move-form") == []
    application.refresh_from_db()
    assert application.stage == final_stage
    assert list(StageChange.objects.values_list("pk", flat=True)) == changes_before


def test_the_panel_offers_one_move_button_per_allowed_stage(staff_client, make_application):
    application = make_application(Stage.INTERVIEW)

    response = staff_client.get(WORKSPACE_URL, {"selected": application.pk})

    buttons = [value for value, _, _ in marked(response, "data-move-to")]
    assert buttons == [Stage.FINAL_REVIEW, Stage.OFFER, Stage.HIRED]


def test_a_hired_application_offers_no_move_buttons(staff_client, make_application):
    application = make_application(Stage.HIRED)

    response = staff_client.get(WORKSPACE_URL, {"selected": application.pk, "stage": "all"})

    assert marked(response, "data-panel")
    assert marked(response, "data-move-form") == []


@pytest.mark.parametrize("final_stage", FINAL_STAGES)
def test_the_panel_offers_reject_and_withdraw_while_in_progress_and_final_messaging_after(
    final_stage, staff_client, candidate, make_application
):
    in_progress = make_application(Stage.INTERVIEW)
    second_job = JobOpening.objects.create(
        title="Data Analyst", department="Finance", description="Analyze data."
    )
    final = make_application(final_stage, candidate=candidate, job=second_job)

    response = staff_client.get(WORKSPACE_URL, {"selected": in_progress.pk})
    endings = [value for value, _, _ in marked(response, "data-end-to")]
    assert endings == [Stage.REJECTED, Stage.WITHDRAWN]
    assert marked(response, "data-final-message") == []

    response = staff_client.get(WORKSPACE_URL, {"selected": final.pk, "stage": "all"})
    assert marked(response, "data-move-form") == []
    assert marked(response, "data-end-to") == []
    [(_, _, message)] = marked(response, "data-final-message")
    assert message == (
        f"This application ended as {Stage(final_stage).label}. It is final, so it can't be moved."
    )


def test_the_workspace_page_loads_htmx(staff_client):
    response = staff_client.get(WORKSPACE_URL)

    assert any(
        attrs.get("src", "").endswith("js/htmx.min.js") for _, attrs, _ in marked(response, "src")
    )


def test_admins_can_move_applications_too(admin_client, admin_user, make_application):
    application = make_application()

    response = _move(admin_client, application, Stage.INTERVIEW)

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.stage == Stage.INTERVIEW
    assert application.stage_changes.last().changed_by == admin_user


def test_a_move_keeps_the_current_filters_in_the_returned_links(
    staff_client, candidate, make_application
):
    application = make_application(Stage.SCREENING)
    second_job = JobOpening.objects.create(
        title="Data Analyst", department="Finance", description="Analyze data."
    )
    other = make_application(candidate=candidate, job=second_job)
    url = reverse("tracker:application_move", args=[application.pk])

    response = staff_client.post(
        f"{url}?stage=screening&q=jo", {"stage": Stage.OFFER}, headers={"HX-Request": "true"}
    )

    [(_, row_attrs, _)] = marked(response, "data-application-row")
    [(_, link_attrs, _)] = marked(response, "data-other-application")
    expected_query = "stage=screening&q=jo&selected="
    assert f"{WORKSPACE_URL}?{expected_query}{other.pk}" == link_attrs["href"]
    [(_, form_attrs, _)] = marked(response, "data-move-form")
    assert form_attrs["hx-post"] == f"{url}?stage=screening&q=jo"
    assert row_attrs["id"] == f"application-row-{application.pk}"


def test_a_move_without_htmx_redirects_back_to_the_workspace_with_a_message(
    staff_client, make_application
):
    application = make_application()
    url = reverse("tracker:application_move", args=[application.pk])

    response = staff_client.post(f"{url}?stage=all", {"stage": Stage.SCREENING}, follow=True)

    assert response.redirect_chain == [
        (f"{WORKSPACE_URL}?stage=all&selected={application.pk}", 302)
    ]
    assert escape("Moved Jo Park to Screening.") in response.content.decode()
    application.refresh_from_db()
    assert application.stage == Stage.SCREENING


def test_a_refused_move_without_htmx_flashes_the_error(staff_client, make_application):
    application = make_application(Stage.OFFER)
    url = reverse("tracker:application_move", args=[application.pk])

    response = staff_client.post(url, {"stage": Stage.APPLIED}, follow=True)

    assert escape("Can't move this application from Offer to Applied.") in (
        response.content.decode()
    )
    application.refresh_from_db()
    assert application.stage == Stage.OFFER


def test_the_move_endpoint_accepts_only_post_and_known_applications(staff_client, make_application):
    application = make_application()
    url = reverse("tracker:application_move", args=[application.pk])

    assert staff_client.get(url).status_code == 405
    missing = reverse("tracker:application_move", args=[application.pk + 1])
    assert staff_client.post(missing, {"stage": Stage.SCREENING}).status_code == 404


def test_anonymous_moves_are_redirected_to_login_and_change_nothing(client, make_application):
    application = make_application()
    url = reverse("tracker:application_move", args=[application.pk])

    response = client.post(url, {"stage": Stage.SCREENING})

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))
    application.refresh_from_db()
    assert application.stage == Stage.APPLIED
    assert not application.stage_changes.exists()


def test_a_user_with_stage_changes_cannot_be_deleted(staff_user, make_application):
    make_application(Stage.SCREENING)

    with pytest.raises(ProtectedError):
        staff_user.delete()
