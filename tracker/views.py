from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .forms import ApplicationForm, CandidateForm, JobOpeningForm, SkillForm
from .models import Candidate, JobOpening, JobStatus, Skill
from .permissions import admin_required


def _form_data(request):
    """Bind forms on every POST, even an empty one, so missing fields show errors."""
    return request.POST if request.method == "POST" else None


def home(request):
    return render(request, "tracker/home.html")


def candidate_list(request):
    query = request.GET.get("q", "")
    candidates = services.search_candidates(query)
    return render(
        request, "tracker/candidates/list.html", {"candidates": candidates, "query": query}
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
    form = ApplicationForm(_form_data(request), candidate=candidate)
    if request.method == "POST" and form.is_valid():
        try:
            application = services.create_application(candidate, **form.cleaned_data)
        except (services.JobClosedToApplicants, services.DuplicateApplication) as error:
            form.add_error(None, error)
        else:
            messages.success(request, f'Recorded application to "{application.job.title}".')
            return redirect(candidate)
    return render(request, "tracker/candidates/apply.html", {"form": form, "candidate": candidate})


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
