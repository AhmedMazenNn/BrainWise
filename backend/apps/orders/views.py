from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.common.pagination import StandardPagination

from .filters import OrderFilter
from .models import Order, OrderStatus
from .permissions import IsManagerOrDispatcher
from .serializers import OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for orders. Only Managers and Dispatchers allowed."""

    queryset = Order.objects.select_related('assigned_driver').all()
    serializer_class = OrderSerializer
    permission_classes = [IsManagerOrDispatcher]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrderFilter
    search_fields = ['customer_name', 'customer_phone', 'address']
    ordering_fields = ['created_at', 'delivered_at', 'cash_amount', 'customer_name']
    ordering = ['-created_at']
    tags = ['Orders']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != OrderStatus.OPEN:
            return Response(
                {'detail': _('Only orders with OPEN status can be deleted.')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)
