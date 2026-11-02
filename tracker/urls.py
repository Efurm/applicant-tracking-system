from django.urls import path

from . import views

app_name = "tracker"

urlpatterns = [
    path("", views.home, name="home"),
    path("candidates/", views.candidate_list, name="candidate_list"),
    path("candidates/new/", views.candidate_create, name="candidate_create"),
    path("candidates/<int:pk>/", views.candidate_detail, name="candidate_detail"),
    path("candidates/<int:pk>/edit/", views.candidate_edit, name="candidate_edit"),
]
