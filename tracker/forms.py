from django import forms
from django.utils.html import format_html

from . import services
from .models import Candidate


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
