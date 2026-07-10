from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Driver
from .permissions import IsManagerOrDispatcher
from .serializers import DriverSerializer
from .services import get_available_drivers


class DriverPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class DriverViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for drivers. Only Managers and Dispatchers allowed."""

    queryset = Driver.objects.select_related('user').all()
    serializer_class = DriverSerializer
    permission_classes = [IsManagerOrDispatcher]
    pagination_class = DriverPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'active']
    search_fields = ['name', 'phone_number']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'], url_path='available')
    def available(self, request):
        """Return only active drivers with AVAILABLE status."""
        queryset = get_available_drivers()
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
