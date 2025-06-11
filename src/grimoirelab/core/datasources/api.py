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

from .models import Repository, Ecosystem
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
