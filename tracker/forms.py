from django import forms
from django.utils.html import format_html

from . import services
from .models import Application, Candidate, JobOpening, Skill


class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = services.CANDIDATE_FIELDS
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}

    def clean_email(self):
        email = services.normalize_email(self.cleaned_data["email"])
        try:
            services.check_email_is_free(email, self.instance)
        except services.DuplicateCandidateEmail as error:
            raise forms.ValidationError(
                format_html(
                    'A candidate with this email already exists: <a href="{}" class="link">{}</a>.',
                    error.existing.get_absolute_url(),
                    error.existing.full_name,
                ),
                code=error.code,
            ) from error
        return email


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ["name"]

    def clean_name(self):
        name = services.normalize_skill_name(self.cleaned_data["name"])
        try:
            services.check_skill_name_is_free(name, self.instance)
        except services.DuplicateSkillName as error:
            raise forms.ValidationError(error.message, code=error.code) from error
        return name


class JobOpeningForm(forms.ModelForm):
    class Meta:
        model = JobOpening
        fields = services.JOB_FIELDS
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "skills": forms.CheckboxSelectMultiple,
        }


class ApplicationForm(forms.ModelForm):
    """Record an application for one candidate; job choices depend on that candidate."""

    class Meta:
        model = Application
        fields = services.APPLICATION_FIELDS

    def __init__(self, *args, candidate, **kwargs):
        super().__init__(*args, **kwargs)
        self.candidate = candidate
        self.fields["job"].queryset = services.jobs_open_to(candidate)
