from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .forms import CandidateForm, SkillForm
from .models import Candidate, Skill
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
    return render(request, "tracker/candidates/detail.html", {"candidate": candidate})


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
