from django.urls import path

from . import views

urlpatterns = [
    path("add/", views.create_job),
    path("list/", views.list_jobs),
    path("clear/", views.clear_jobs),
]
