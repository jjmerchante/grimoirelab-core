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

from rest_framework import (
    generics,
    pagination,
    response,
    serializers,
)
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter)
from drf_spectacular.types import OpenApiTypes
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import (
    Repository,
    Ecosystem,
    Project)
from ..scheduler.api import EventizerTaskListSerializer


class DataSourcesPaginator(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = 'size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return response.Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'results': data
        })


class EventizerRepositoryListSerializer(serializers.ModelSerializer):
    task = EventizerTaskListSerializer()

    class Meta:
        model = Repository
        fields = [
            'uri', 'datasource_type', 'datasource_category', 'task',
        ]


class ProjectSerializer(serializers.ModelSerializer):
    subprojects = serializers.SlugRelatedField(many=True,
                                               read_only=True,
                                               slug_field='name')

    class Meta:
        model = Project
        fields = ['id', 'name', 'title', 'parent_project', 'subprojects']
        lookup_field = 'name'

    def validate_name(self, value,):
        ecosystem = self.context['ecosystem']
        if Project.objects.filter(ecosystem=ecosystem, name=value).count() > 0:
            raise serializers.ValidationError(f"Ecosystem '{ecosystem.name}' already has a project named '{value}'")

        return value


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


class RepositoryList(generics.ListAPIView):
    serializer_class = EventizerRepositoryListSerializer
    pagination_class = DataSourcesPaginator

    def get_queryset(self):
        datasource = self.request.query_params.get('datasource')
        category = self.request.query_params.get('category')
        uri = self.request.query_params.get('uri')

        queryset = Repository.objects.select_related('task')
        if datasource is not None:
            queryset = queryset.filter(datasource_type=datasource)
        if category is not None:
            queryset = queryset.filter(datasource_category=category)
        if uri is not None:
            queryset = queryset.filter(uri=uri)

        return queryset


class EcosystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ecosystem
        fields = ['name', 'title', 'description']


class EcosystemDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Ecosystem.objects.all()
    lookup_field = 'name'
    serializer_class = EcosystemSerializer
    model = Ecosystem


class EcosystemList(generics.ListCreateAPIView):
    queryset = Ecosystem.objects.all()
    serializer_class = EcosystemSerializer
    pagination_class = DataSourcesPaginator
    model = Ecosystem


@extend_schema_view(get=extend_schema(
    parameters=[
        OpenApiParameter('parent_id', OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter('term', OpenApiTypes.STR, OpenApiParameter.QUERY)]
))
class ProjectList(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    pagination_class = DataSourcesPaginator
    model = Project

    def get_serializer_context(self):
        context = super().get_serializer_context()
        ecosystem = get_object_or_404(Ecosystem, name=self.kwargs.get('ecosystem_name'))
        context.update({'ecosystem': ecosystem})

        return context

    def get_queryset(self):
        ecosystem_name = self.kwargs.get('ecosystem_name')
        queryset = Project.objects.filter(ecosystem__name=ecosystem_name)
        parent_id = self.request.query_params.get('parent_id')
        term = self.request.query_params.get('term')

        if term is not None:
            queryset = queryset.filter(Q(name__icontains=term) |
                                       Q(title__icontains=term))
        if parent_id is not None:
            queryset = queryset.filter(parent_project_id=parent_id)
        elif not term and not parent_id:
            queryset = queryset.filter(parent_project__isnull=True)

        return queryset

    def perform_create(self, serializer):
        ecosystem = serializer.context['ecosystem']
        serializer.save(ecosystem=ecosystem)


class ProjectDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectDetailSerializer
    model = Project
    lookup_field = 'name'

    def get_queryset(self):
        ecosystem_name = self.kwargs.get('ecosystem_name')
        queryset = Project.objects.filter(ecosystem__name=ecosystem_name)

        return queryset
