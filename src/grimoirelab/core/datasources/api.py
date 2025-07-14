# -*- coding: utf-8 -*-
#
# Copyright (C) GrimoireLab Contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import itertools

from rest_framework import (
    generics,
    pagination,
    response,
    serializers,
    status,
)
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    extend_schema_serializer,
    OpenApiParameter,
)
from drf_spectacular.types import OpenApiTypes
from django.db.models import Q
from django.conf import settings
from django.shortcuts import get_object_or_404

from .models import (
    DataSet,
    Repository,
    Ecosystem,
    Project,
)
from .utils import generate_uuid
from ..scheduler.api import EventizerTaskSerializer
from ..scheduler.scheduler import schedule_task, cancel_task


class DataSourcesPaginator(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = "size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return response.Response(
            {
                "links": {
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "count": self.page.paginator.count,
                "page": self.page.number,
                "total_pages": self.page.paginator.num_pages,
                "results": data,
            }
        )


class ProjectSerializer(serializers.ModelSerializer):
    subprojects = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    repos = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "title",
            "parent_project",
            "subprojects",
            "repos",
        ]
        lookup_field = "name"

    def validate_name(
        self,
        value,
    ):
        ecosystem = self.context["ecosystem"]
        if Project.objects.filter(ecosystem=ecosystem, name=value).count() > 0:
            raise serializers.ValidationError(
                f"Ecosystem '{ecosystem.name}' already has a project named '{value}'"
            )

        return value

    def get_repos(self, obj):
        return Repository.objects.filter(dataset__project=obj).distinct().values("uuid")


class ParentProjectField(serializers.Field):
    def to_representation(self, value):
        return ProjectSerializer(value).data

    def to_internal_value(self, data):
        try:
            return Project.objects.get(id=int(data))
        except (AttributeError, KeyError):
            pass


class ProjectDetailSerializer(ProjectSerializer):
    parent_project = ParentProjectField()
    subprojects = ProjectSerializer(many=True, read_only=True)


class EcosystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ecosystem
        fields = [
            "name",
            "title",
            "description",
        ]


class EcosystemDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Ecosystem.objects.all()
    lookup_field = "name"
    serializer_class = EcosystemSerializer
    model = Ecosystem


class EcosystemList(generics.ListCreateAPIView):
    queryset = Ecosystem.objects.all()
    serializer_class = EcosystemSerializer
    pagination_class = DataSourcesPaginator
    model = Ecosystem


@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter("parent_id", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter("term", OpenApiTypes.STR, OpenApiParameter.QUERY),
        ]
    )
)
class ProjectList(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    pagination_class = DataSourcesPaginator
    model = Project

    def get_serializer_context(self):
        context = super().get_serializer_context()
        ecosystem = get_object_or_404(Ecosystem, name=self.kwargs.get("ecosystem_name"))
        context.update({"ecosystem": ecosystem})

        return context

    def get_queryset(self):
        ecosystem_name = self.kwargs.get("ecosystem_name")
        queryset = Project.objects.filter(ecosystem__name=ecosystem_name)
        parent_id = self.request.query_params.get("parent_id")
        term = self.request.query_params.get("term")

        if term is not None:
            queryset = queryset.filter(Q(name__icontains=term) | Q(title__icontains=term))
        if parent_id is not None:
            queryset = queryset.filter(parent_project_id=parent_id)
        elif not term and not parent_id:
            queryset = queryset.filter(parent_project__isnull=True)

        return queryset

    def perform_create(self, serializer):
        ecosystem = serializer.context["ecosystem"]
        serializer.save(ecosystem=ecosystem)


class ProjectDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectDetailSerializer
    model = Project
    lookup_field = "name"

    def get_queryset(self):
        ecosystem_name = self.kwargs.get("ecosystem_name")
        queryset = Project.objects.filter(ecosystem__name=ecosystem_name)

        return queryset


class CategorySerializer(serializers.ModelSerializer):
    task = EventizerTaskSerializer(read_only=True)

    class Meta:
        model = DataSet
        fields = [
            "id",
            "category",
            "task",
        ]


class RepoSerializer(serializers.ModelSerializer):
    categories = serializers.SlugRelatedField(
        source="dataset_set", many=True, read_only=True, slug_field="category"
    )

    class Meta:
        model = Repository
        fields = [
            "uuid",
            "uri",
            "datasource_type",
            "categories",
        ]


class RepoDetailSerializer(RepoSerializer):
    categories = serializers.SerializerMethodField(read_only=True, method_name="get_categories")

    class Meta:
        model = Repository
        fields = [
            "uuid",
            "uri",
            "datasource_type",
            "categories",
        ]

    def get_categories(self, obj):
        serializer = CategorySerializer(instance=obj.dataset_set.all(), many=True)
        return serializer.data


@extend_schema_serializer(exclude_fields=("project__id"))
class CreateRepoSerializer(serializers.Serializer):
    uri = serializers.CharField()
    datasource_type = serializers.CharField()
    category = serializers.CharField()
    project__id = serializers.CharField()
    scheduler = serializers.JSONField(required=False)

    def validate(self, attrs):
        try:
            Repository.objects.get(
                uri=attrs["uri"],
                dataset__project__id=attrs["project__id"],
                dataset__category=attrs["category"],
            )
        except Repository.DoesNotExist:
            pass
        else:
            msg = f"Repository '{attrs['uri']}' with category '{attrs['category']}' already exists in project."
            raise serializers.ValidationError(msg)

        return attrs


@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter("datasource_type", OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter("category", OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter("uri", OpenApiTypes.STR, OpenApiParameter.QUERY),
        ]
    )
)
@extend_schema(request=CreateRepoSerializer)
class RepoList(generics.ListCreateAPIView):
    serializer_class = RepoDetailSerializer
    pagination_class = DataSourcesPaginator
    model = Repository

    def get_queryset(self):
        project = get_object_or_404(
            Project,
            name=self.kwargs.get("project_name"),
            ecosystem__name=self.kwargs.get("ecosystem_name"),
        )
        queryset = Repository.objects.filter(dataset__project=project).distinct()

        datasource = self.request.query_params.get("datasource_type")
        category = self.request.query_params.get("category")
        uri = self.request.query_params.get("uri")

        if datasource is not None:
            queryset = queryset.filter(datasource_type=datasource)
        if category is not None:
            queryset = queryset.filter(dataset__category=category).distinct()
        if uri is not None:
            queryset = queryset.filter(uri=uri)

        return queryset

    def create(self, request, *args, **kwargs):
        # Get project from URL params
        project = get_object_or_404(
            Project,
            name=self.kwargs.get("project_name"),
            ecosystem__name=self.kwargs.get("ecosystem_name"),
        )
        request.data["project__id"] = project.id

        # Validate request data
        serializer = CreateRepoSerializer(data=request.data)
        if serializer.is_valid():
            # Create repository if it does not exist yet
            uuid = generate_uuid(str(request.data["uri"]), str(request.data["datasource_type"]))
            repository, _ = Repository.objects.get_or_create(
                uri=request.data["uri"], datasource_type=request.data["datasource_type"], uuid=uuid
            )
            # Create data set
            dataset = DataSet.objects.create(
                project=project, repository=repository, category=request.data["category"]
            )

            # Create task
            job_interval = settings.GRIMOIRELAB_JOB_INTERVAL
            job_max_retries = settings.GRIMOIRELAB_JOB_MAX_RETRIES
            if "scheduler" in request.data:
                job_interval = request.data["scheduler"].get("job_interval", job_interval)
                job_max_retries = request.data["scheduler"].get("job_max_retries", job_max_retries)

            task_args = {"uri": request.data["uri"]}
            task = schedule_task(
                "eventizer",
                task_args,
                datasource_type=request.data["datasource_type"],
                datasource_category=request.data["category"],
                job_interval=job_interval,
                job_max_retries=job_max_retries,
            )
            dataset.task = task
            dataset.save()
            response_serializer = self.get_serializer(repository)

            return response.Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class RepoDetail(generics.RetrieveDestroyAPIView):
    serializer_class = RepoDetailSerializer
    model = Repository
    lookup_field = "uuid"

    def get_queryset(self):
        project = get_object_or_404(
            Project,
            name=self.kwargs.get("project_name"),
            ecosystem__name=self.kwargs.get("ecosystem_name"),
        )
        queryset = Repository.objects.filter(dataset__project=project).distinct()

        return queryset

    def destroy(self, request, *args, **kwargs):
        project = get_object_or_404(
            Project,
            name=self.kwargs.get("project_name"),
            ecosystem__name=self.kwargs.get("ecosystem_name"),
        )
        repo = get_object_or_404(Repository, uuid=self.kwargs.get("uuid"))
        datasets = DataSet.objects.filter(project=project, repository=repo)

        # Cancel all related tasks
        for dataset in datasets:
            if dataset.task:
                cancel_task(dataset.task.uuid)

        # Delete repository
        repo.delete()

        return response.Response(status=status.HTTP_204_NO_CONTENT)


class CategoryDetail(generics.RetrieveDestroyAPIView):
    serializer_class = CategorySerializer
    model = DataSet
    lookup_field = "category"

    def get_queryset(self):
        project = get_object_or_404(
            Project,
            name=self.kwargs.get("project_name"),
            ecosystem__name=self.kwargs.get("ecosystem_name"),
        )
        repo = get_object_or_404(Repository, uuid=self.kwargs.get("uuid"))
        queryset = DataSet.objects.filter(project=project, repository=repo)

        return queryset

    def destroy(self, request, *args, **kwargs):
        project = get_object_or_404(
            Project,
            name=self.kwargs.get("project_name"),
            ecosystem__name=self.kwargs.get("ecosystem_name"),
        )
        repo = get_object_or_404(Repository, uuid=self.kwargs.get("uuid"))
        dataset = get_object_or_404(
            DataSet, category=self.kwargs.get("category"), repository=repo, project=project
        )

        # Cancel related task
        if dataset.task:
            cancel_task(dataset.task.uuid)

        # Delete data set
        dataset.delete()
        dataset.repository.save()

        # Check if the related repository has no data set associated
        if not dataset.repository.dataset_set.exists():
            dataset.repository.delete()

        return response.Response(status=status.HTTP_204_NO_CONTENT)


class ProjectChildSerializer(serializers.ModelSerializer):
    """Returns different fields for a project or a repository."""

    type = serializers.CharField()
    name = serializers.CharField(required=False)
    title = serializers.CharField(required=False)
    uri = serializers.CharField(required=False)
    subprojects = serializers.IntegerField(required=False)
    repos = serializers.IntegerField(required=False)
    categories = serializers.IntegerField(required=False)
    uuid = serializers.CharField(required=False)

    class Meta:
        model = Project
        fields = [
            "type",
            "name",
            "title",
            "uri",
            "subprojects",
            "repos",
            "categories",
            "uuid",
        ]

    def to_representation(self, instance):
        representation = {"id": instance.id}
        if hasattr(instance, "name"):
            # Return project data
            representation["type"] = "project"
            representation["name"] = instance.name
            representation["title"] = instance.title
            representation["subprojects"] = instance.subprojects.count()
            representation["repos"] = (
                Repository.objects.filter(dataset__project=instance).distinct().count()
            )
        else:
            # Return repository data
            representation["type"] = "repository"
            representation["uri"] = instance.uri
            representation["categories"] = instance.dataset_set.count()
            representation["uuid"] = instance.uuid

        return representation


@extend_schema_view(
    get=extend_schema(
        parameters=[OpenApiParameter("term", OpenApiTypes.STR, OpenApiParameter.QUERY)]
    )
)
class ProjectChildrenList(generics.ListAPIView):
    """Returns a paginated list of a project's descendants (repositories and subprojects)."""

    serializer_class = ProjectChildSerializer
    pagination_class = DataSourcesPaginator

    def get_queryset(self):
        project = get_object_or_404(
            Project,
            name=self.kwargs.get("project_name"),
            ecosystem__name=self.kwargs.get("ecosystem_name"),
        )
        project_queryset = Project.objects.filter(parent_project=project)
        repo_queryset = Repository.objects.filter(dataset__project=project).distinct()

        term = self.request.query_params.get("term")
        if term is not None:
            project_queryset = project_queryset.filter(
                Q(name__icontains=term) | Q(title__icontains=term)
            )
            repo_queryset = repo_queryset.filter(uri__icontains=term)

        queryset = list(itertools.chain(project_queryset, repo_queryset))

        return queryset
