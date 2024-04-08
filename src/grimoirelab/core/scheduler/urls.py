from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^list', views.list_tasks),
    re_path(r'^task/(?P<task_id>[a-zA-Z0-9_.-]+)/$', views.show_task),
    re_path(r'^job/(?P<job_id>[a-zA-Z0-9_.-]+)/$', views.show_job),
    re_path(r'^add_task', views.add_task),
    re_path(r'^remove_task', views.delete_task),
    re_path(r'^reschedule_task', views.reschedule_task),
    # re_path(r'^add_token', views.add_token),
]
