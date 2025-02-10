"""GrimoireLab URL Configuration"""


from django.urls import path, include, re_path
from django.views.generic import TemplateView

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from ..views import api_login

from grimoirelab.core.scheduler.urls import urlpatterns as sched_urlpatterns
from grimoirelab.core.datasources.urls import urlpatterns as datasources_urlpatterns

urlpatterns = [
    path("login", api_login, name="api_login"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("scheduler/", include(sched_urlpatterns)),
    path("datasources/", include(datasources_urlpatterns)),
    re_path(r'^(?!static|scheduler).*$', TemplateView.as_view(template_name="index.html"))
]
