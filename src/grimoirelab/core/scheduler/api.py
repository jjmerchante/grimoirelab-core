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

from .tasks.models import EventizerTask


class EventizerTaskPaginator(pagination.PageNumberPagination):
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


class EventizerTaskListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='get_status_display')

    class Meta:
        model = EventizerTask
        fields = [
            'uuid', 'status', 'runs', 'failures', 'last_run',
            'scheduled_at', 'datasource_type', 'datasource_category',
        ]


class EventizerTaskList(generics.ListCreateAPIView):
    queryset = EventizerTask.objects.all()
    serializer_class = EventizerTaskListSerializer
    pagination_class = EventizerTaskPaginator
