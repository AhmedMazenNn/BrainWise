from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.common.pagination import StandardPagination
from apps.delivery_runs.models import RunStatus

from .filters import DeliveryStopFilter
from .models import DeliveryStop, StopStatus
from .permissions import DeliveryStopPermission
from .serializers import DeliveryStopSerializer


class DeliveryStopViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for delivery stops.

    Manager/Dispatcher: full CRUD.
    Driver: read-only access to stops from their own runs,
    plus mark_delivered/mark_failed on own stops.
    """

    queryset = DeliveryStop.objects.select_related(
        'delivery_run', 'order', 'delivery_run__driver',
    ).all()
    serializer_class = DeliveryStopSerializer
    permission_classes = [DeliveryStopPermission]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DeliveryStopFilter
    search_fields = ['customer_name', 'address']
    ordering_fields = ['stop_sequence', 'created_at', 'delivered_at', 'cash_amount']
    ordering = ['stop_sequence']
    tags = ['Delivery Stops']

    def perform_create(self, serializer):
        order = serializer.validated_data['order']
        serializer.save(
            customer_name=order.customer_name,
            address=order.address,
            cash_amount=order.cash_amount,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.delivery_run.status != RunStatus.DRAFT:
            return Response(
                {'detail': _('Only stops in a DRAFT delivery run can be deleted.')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='mark-delivered')
    def mark_delivered(self, request, pk=None):
        """Mark a stop as delivered and add cash to run total."""
        stop = self.get_object()

        if stop.status not in (StopStatus.ASSIGNED, StopStatus.EN_ROUTE):
            return Response(
                {'detail': _('Only ASSIGNED or EN_ROUTE stops can be marked as delivered.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        run = stop.delivery_run
        if run.status not in (RunStatus.EN_ROUTE, RunStatus.ASSIGNED):
            return Response(
                {'detail': _('Delivery run must be active to mark stops as delivered.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            stop.status = StopStatus.DELIVERED
            stop.delivered_at = timezone.now()
            stop.save()

            stop.order.status = 'DELIVERED'
            stop.order.delivered_at = stop.delivered_at
            stop.order.save()

            from decimal import Decimal
            run.total_cash_collected = Decimal(str(run.total_cash_collected)) + Decimal(str(stop.cash_amount))
            run.save()

        return Response(
            DeliveryStopSerializer(stop).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='mark-failed')
    def mark_failed(self, request, pk=None):
        """Mark a stop as failed with a required failure reason."""
        stop = self.get_object()

        if stop.status not in (StopStatus.ASSIGNED, StopStatus.EN_ROUTE):
            return Response(
                {'detail': _('Only ASSIGNED or EN_ROUTE stops can be marked as failed.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        failed_reason = request.data.get('failed_reason', '').strip()
        if not failed_reason:
            return Response(
                {'detail': _('failed_reason is required when marking a stop as failed.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        run = stop.delivery_run
        if run.status not in (RunStatus.EN_ROUTE, RunStatus.ASSIGNED):
            return Response(
                {'detail': _('Delivery run must be active to mark stops as failed.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            stop.status = StopStatus.FAILED
            stop.failed_reason = failed_reason
            stop.save()

            stop.order.status = 'FAILED'
            stop.order.save()

        return Response(
            DeliveryStopSerializer(stop).data,
            status=status.HTTP_200_OK,
        )
