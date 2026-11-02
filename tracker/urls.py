from django.urls import path

from . import views

app_name = "tracker"

urlpatterns = [
    path("", views.home, name="home"),
    path("candidates/", views.candidate_list, name="candidate_list"),
    path("candidates/new/", views.candidate_create, name="candidate_create"),
    path("candidates/<int:pk>/", views.candidate_detail, name="candidate_detail"),
    path("candidates/<int:pk>/edit/", views.candidate_edit, name="candidate_edit"),
    path("candidates/<int:pk>/apply/", views.candidate_apply, name="candidate_apply"),
    path("jobs/", views.job_list, name="job_list"),
    path("jobs/new/", views.job_create, name="job_create"),
    path("jobs/<int:pk>/", views.job_detail, name="job_detail"),
    path("jobs/<int:pk>/edit/", views.job_edit, name="job_edit"),
    path("jobs/<int:pk>/close/", views.job_close, name="job_close"),
    path("jobs/<int:pk>/reopen/", views.job_reopen, name="job_reopen"),
    path("applications/", views.application_workspace, name="application_workspace"),
    path("applications/<int:pk>/move/", views.application_move, name="application_move"),
    path("skills/", views.skill_list, name="skill_list"),
    path("skills/new/", views.skill_create, name="skill_create"),
    path("skills/<int:pk>/edit/", views.skill_edit, name="skill_edit"),
    path("skills/<int:pk>/delete/", views.skill_delete, name="skill_delete"),
]
