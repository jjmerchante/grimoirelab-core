"""GrimoireLab URL Configuration"""

from django.conf import settings
from django.urls import path, include, re_path
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from sortinghat.app.schema import schema
from sortinghat.core.views import SortingHatGraphQLView
from ..views import api_login

from grimoirelab.core.scheduler.urls import tasks_urlpatterns
from grimoirelab.core.datasources.urls import ecosystems_urlpatterns


urlpatterns = [
    path("login", api_login, name="api_login"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "api/v1/",
        include(
            [
                # Ecosystems and Projects API
                path("ecosystems/", include(ecosystems_urlpatterns)),
                # SortingHat GraphQL API for identities
                path(
                    "identities/",
                    csrf_exempt(
                        SortingHatGraphQLView.as_view(graphiql=settings.DEBUG, schema=schema)
                    ),
                ),
                # Tasks API
                path("tasks/", include(tasks_urlpatterns)),
            ]
        ),
    ),
    re_path(
        r"^(?!static|login|token|api).*$",
        TemplateView.as_view(template_name="index.html"),
    ),
]
