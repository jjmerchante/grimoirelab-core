"""GrimoireLab URL Configuration"""


from django.urls import path, include

from grimoirelab.core.scheduler.urls import urlpatterns as sched_urlpatterns

urlpatterns = [
    path("scheduler/", include(sched_urlpatterns))
]
