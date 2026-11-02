from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import services
from .forms import ApplicationForm, CandidateForm, JobOpeningForm, SkillForm
from .models import Application, Candidate, JobOpening, JobStatus, Skill, Stage
from .permissions import admin_required


def _form_data(request):
    """Bind forms on every POST, even an empty one, so missing fields show errors."""
    return request.POST if request.method == "POST" else None


def home(request):
    return render(request, "tracker/home.html")


def candidate_list(request):
    """Candidates matching ``?q=``; archived ones only with ``?archived=1``."""
    query = request.GET.get("q", "")
    show_archived = request.GET.get("archived", "") == "1"
    candidates = services.search_candidates(query, include_archived=show_archived)
    return render(
        request,
        "tracker/candidates/list.html",
        {"candidates": candidates, "query": query, "show_archived": show_archived},
    )


def candidate_detail(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    applications = candidate.applications.select_related("job")
    return render(
        request,
        "tracker/candidates/detail.html",
        {"candidate": candidate, "applications": applications},
    )


def candidate_create(request):
    form = CandidateForm(_form_data(request))
    if request.method == "POST" and form.is_valid():
        candidate = services.create_candidate(**form.cleaned_data)
        return redirect(candidate)
    return render(request, "tracker/candidates/form.html", {"form": form})


def candidate_edit(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    form = CandidateForm(_form_data(request), instance=candidate)
    if request.method == "POST" and form.is_valid():
        services.update_candidate(candidate, **form.cleaned_data)
        return redirect(candidate)
    return render(request, "tracker/candidates/form.html", {"form": form, "candidate": candidate})


def candidate_apply(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    if candidate.archived:
        messages.error(
            request, services.CandidateArchived(candidate, services.APPLY_REFUSAL).message
        )
        return redirect(candidate)
    form = ApplicationForm(_form_data(request), candidate=candidate)
    if request.method == "POST" and form.is_valid():
        try:
            application = services.create_application(candidate, **form.cleaned_data)
        except (
            services.CandidateArchived,
            services.JobClosedToApplicants,
            services.DuplicateApplication,
        ) as error:
            form.add_error(None, error)
        else:
            messages.success(request, f'Recorded application to "{application.job.title}".')
            return redirect(candidate)
    return render(request, "tracker/candidates/apply.html", {"form": form, "candidate": candidate})


@admin_required
@require_POST
def candidate_archive(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    try:
        services.archive_candidate(candidate)
    except services.CandidateHasApplicationsInProgress as error:
        messages.error(request, error.message)
    else:
        messages.success(request, f"Archived {candidate.full_name}.")
    return redirect(candidate)


@admin_required
@require_POST
def candidate_unarchive(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    services.unarchive_candidate(candidate)
    messages.success(request, f"Unarchived {candidate.full_name}.")
    return redirect(candidate)


@admin_required
@require_POST
def candidate_delete(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    try:
        services.delete_candidate(candidate)
    except services.CandidateHasApplications as error:
        messages.error(request, error.message)
        return redirect(candidate)
    messages.success(request, f"Deleted {candidate.full_name}.")
    return redirect("tracker:candidate_list")


@admin_required
def skill_list(request):
    return render(request, "tracker/skills/list.html", {"skills": Skill.objects.all()})


@admin_required
def skill_create(request):
    form = SkillForm(_form_data(request))
    if request.method == "POST" and form.is_valid():
        skill = services.create_skill(form.cleaned_data["name"])
        messages.success(request, f'Added skill "{skill.name}".')
        return redirect("tracker:skill_list")
    return render(request, "tracker/skills/form.html", {"form": form})


@admin_required
def skill_edit(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    form = SkillForm(_form_data(request), instance=skill)
    if request.method == "POST" and form.is_valid():
        services.rename_skill(skill, form.cleaned_data["name"])
        messages.success(request, f'Renamed skill to "{skill.name}".')
        return redirect("tracker:skill_list")
    return render(request, "tracker/skills/form.html", {"form": form, "skill": skill})


@admin_required
@require_POST
def skill_delete(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    try:
        services.delete_skill(skill)
    except services.SkillInUse as error:
        messages.error(request, error.message)
    else:
        messages.success(request, f'Deleted skill "{skill.name}".')
    return redirect("tracker:skill_list")


def job_list(request):
    status = request.GET.get("status", "")
    if status not in JobStatus.values:
        status = ""
    jobs = services.filter_jobs(status)
    return render(
        request,
        "tracker/jobs/list.html",
        {"jobs": jobs, "status": status, "status_choices": JobStatus.choices},
    )


def job_detail(request, pk):
    job = get_object_or_404(JobOpening.objects.prefetch_related("skills"), pk=pk)
    return render(request, "tracker/jobs/detail.html", {"job": job})


@admin_required
def job_create(request):
    form = JobOpeningForm(_form_data(request))
    if request.method == "POST" and form.is_valid():
        job = services.create_job(**form.cleaned_data)
        messages.success(request, f'Created job opening "{job.title}".')
        return redirect(job)
    return render(request, "tracker/jobs/form.html", {"form": form})


@admin_required
def job_edit(request, pk):
    job = get_object_or_404(JobOpening, pk=pk)
    form = JobOpeningForm(_form_data(request), instance=job)
    if request.method == "POST" and form.is_valid():
        services.update_job(job, **form.cleaned_data)
        messages.success(request, f'Saved changes to "{job.title}".')
        return redirect(job)
    return render(request, "tracker/jobs/form.html", {"form": form, "job": job})


@admin_required
@require_POST
def job_close(request, pk):
    job = get_object_or_404(JobOpening, pk=pk)
    services.close_job(job)
    messages.success(request, f'Closed "{job.title}" to new applicants.')
    return redirect(job)


@admin_required
@require_POST
def job_reopen(request, pk):
    job = get_object_or_404(JobOpening, pk=pk)
    services.reopen_job(job)
    messages.success(request, f'Reopened "{job.title}".')
    return redirect(job)


def _workspace_filters(request):
    """The workspace filters from the query string, cleaned, plus them as a query string.

    Unknown jobs and stages fall back to the defaults (all jobs, in-progress).
    The query string lets links and the move form keep the current filters.
    """
    job_id = request.GET.get("job", "")
    job = JobOpening.objects.filter(pk=job_id).first() if job_id.isdigit() else None
    stage = request.GET.get("stage", "")
    if stage != services.ALL_STAGES and stage not in Stage.values:
        stage = ""
    query = request.GET.get("q", "")
    filters = {"job": job.pk if job else "", "stage": stage, "q": query}
    filter_query = urlencode({name: value for name, value in filters.items() if value})
    return job, stage, query, filter_query


def _panel_context(request, application, filter_query, move_error=None):
    """What the detail panel (and its list row) need to render ``application``.

    The allowed moves are split into forward moves, endings (Reject and
    Withdraw), and Admin reopens (any move out of a final stage), which the
    panel draws as separate controls. ``stage_changes`` feeds the
    stage-history timeline.
    """
    allowed = services.allowed_next_stages(application.stage, request.user)
    reopening = application.is_final
    if reopening and application.candidate.archived:
        allowed = ()
    return {
        "application": application,
        "selected": application,
        "filter_query": filter_query,
        "other_applications": application.candidate.applications.exclude(
            pk=application.pk
        ).select_related("job"),
        "allowed_moves": allowed,
        "forward_moves": []
        if reopening
        else [s for s in allowed if s not in services.ENDING_STAGES],
        "ending_moves": [] if reopening else [s for s in allowed if s in services.ENDING_STAGES],
        "reopen_moves": list(allowed) if reopening else [],
        "stage_changes": application.stage_changes.select_related("changed_by"),
        "move_error": move_error,
        "candidate_archived": application.candidate.archived,
    }


def application_workspace(request):
    job, stage, query, filter_query = _workspace_filters(request)
    applications = services.filter_applications(job=job, stage=stage, query=query)

    selected_id = request.GET.get("selected", "")
    selected = None
    if selected_id.isdigit():
        selected = (
            Application.objects.select_related("candidate", "job").filter(pk=selected_id).first()
        )
    context = {
        "applications": applications,
        "job": job,
        "stage": stage,
        "query": query,
        "filter_query": filter_query,
        "selected": selected,
        "jobs": JobOpening.objects.all(),
        "stage_choices": Stage.choices,
        "all_stages": services.ALL_STAGES,
    }
    if selected is not None:
        context |= _panel_context(request, selected, filter_query)
    return render(request, "tracker/applications/workspace.html", context)


@require_POST
def application_move(request, pk):
    """Move an application to the posted stage.

    An HTMX request gets the re-rendered detail panel plus the application's
    list row as an out-of-band swap; a refused move renders its message in the
    panel and changes nothing. Without HTMX, the result is flashed and the
    browser goes back to the workspace.
    """
    application = get_object_or_404(Application.objects.select_related("candidate", "job"), pk=pk)
    _, _, _, filter_query = _workspace_filters(request)
    to_stage = request.POST.get("stage", "")
    move_error = None
    try:
        services.move_application(
            application, to_stage, request.user, note=request.POST.get("note", "")
        )
    except (services.InvalidStageMove, services.CandidateArchived) as error:
        move_error = error.message
        application.refresh_from_db()

    if not request.headers.get("HX-Request"):
        if move_error:
            messages.error(request, move_error)
        else:
            messages.success(
                request,
                f"Moved {application.candidate.full_name} to {application.get_stage_display()}.",
            )
        query = f"{filter_query}&" if filter_query else ""
        return redirect(f"{reverse('tracker:application_workspace')}?{query}selected={pk}")

    return render(
        request,
        "tracker/applications/_move.html",
        _panel_context(request, application, filter_query, move_error),
    )
