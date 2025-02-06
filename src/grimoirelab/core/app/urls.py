"""GrimoireLab URL Configuration"""


from django.urls import path, include, re_path
from django.views.generic import TemplateView

from grimoirelab.core.scheduler.urls import urlpatterns as sched_urlpatterns
from grimoirelab.core.datasources.urls import urlpatterns as datasources_urlpatterns

urlpatterns = [
    path("scheduler/", include(sched_urlpatterns)),
    path("datasources/", include(datasources_urlpatterns)),
    re_path(r'^(?!static|scheduler).*$', TemplateView.as_view(template_name="index.html"))
]
