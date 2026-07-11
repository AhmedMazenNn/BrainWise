from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.common.pagination import StandardPagination

from .filters import DeliveryRunFilter
from .models import DeliveryRun, RunStatus
from .permissions import IsManagerOrDispatcher
from .serializers import DeliveryRunSerializer


class DeliveryRunViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for delivery runs. Only Managers and Dispatchers allowed."""

    queryset = DeliveryRun.objects.select_related('driver').all()
    serializer_class = DeliveryRunSerializer
    permission_classes = [IsManagerOrDispatcher]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DeliveryRunFilter
    search_fields = ['driver__name', 'driver__phone_number']
    ordering_fields = ['created_at', 'started_at', 'completed_at', 'total_cash_collected']
    ordering = ['-created_at']
    tags = ['Delivery Runs']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != RunStatus.DRAFT:
            return Response(
                {'detail': _('Only runs with DRAFT status can be deleted.')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)
