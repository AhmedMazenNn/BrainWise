from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.common.pagination import StandardPagination
from apps.drivers.models import DriverStatus
from apps.orders.models import OrderStatus

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

    @action(detail=True, methods=['post'], url_path='build-run')
    def build_run(self, request, pk=None):
        """Build a delivery run by assigning open orders as delivery stops.

        Accepts: {"order_ids": [1, 2, 3]}
        Validates driver availability, order openness, and max stops limit.
        """
        run = self.get_object()

        if run.status != RunStatus.DRAFT:
            return Response(
                {'detail': _('Only DRAFT runs can be built.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_ids = request.data.get('order_ids')
        if not order_ids or not isinstance(order_ids, list):
            return Response(
                {'detail': _('order_ids must be a non-empty list of order IDs.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        driver = run.driver
        if not driver.active or driver.status != DriverStatus.AVAILABLE:
            return Response(
                {'detail': _('Driver is not available for assignment.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.orders.models import Order
        from apps.delivery_stops.models import DeliveryStop

        order_map = Order.objects.filter(
            id__in=order_ids, status=OrderStatus.OPEN,
        ).in_bulk()
        ordered_orders = [order_map[i] for i in order_ids if i in order_map]

        if len(ordered_orders) != len(order_ids):
            found_ids = set(order_map.keys())
            missing = set(order_ids) - found_ids
            return Response(
                {'detail': _('Some orders are not open or do not exist: %(ids)s') % {
                    'ids': ', '.join(str(i) for i in sorted(missing))
                }},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_stops = driver.max_stops_per_run
        existing_stops = run.stops.count()
        if existing_stops + len(ordered_orders) > max_stops:
            return Response(
                {'detail': _('Adding %(count)s stops would exceed driver max of %(max)s (currently has %(existing)s).') % {
                    'count': len(ordered_orders),
                    'max': max_stops,
                    'existing': existing_stops,
                }},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            next_seq = existing_stops + 1
            for idx, order in enumerate(ordered_orders):
                DeliveryStop.objects.create(
                    delivery_run=run,
                    order=order,
                    stop_sequence=next_seq + idx,
                    customer_name=order.customer_name,
                    address=order.address,
                    cash_amount=order.cash_amount,
                )
                order.status = OrderStatus.ASSIGNED
                order.assigned_driver = driver
                order.save()

            run.status = RunStatus.ASSIGNED
            run.save()

        return Response(
            DeliveryRunSerializer(run).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='start-run')
    def start_run(self, request, pk=None):
        """Start a delivery run: transition to EN_ROUTE, dispatch the driver."""
        run = self.get_object()

        if run.status != RunStatus.ASSIGNED:
            return Response(
                {'detail': _('Only ASSIGNED runs can be started.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if run.stops.count() == 0:
            return Response(
                {'detail': _('Cannot start a run with no delivery stops.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            run.status = RunStatus.EN_ROUTE
            run.started_at = timezone.now()
            run.save()

            from apps.delivery_stops.models import StopStatus
            run.stops.update(status=StopStatus.EN_ROUTE)

            from apps.orders.models import Order
            order_ids = run.stops.values_list('order_id', flat=True)
            Order.objects.filter(id__in=order_ids).update(status=OrderStatus.EN_ROUTE)

            driver = run.driver
            driver.status = DriverStatus.ON_RUN
            driver.save()

        return Response(
            DeliveryRunSerializer(run).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='complete-run')
    def complete_run(self, request, pk=None):
        """Complete a delivery run once all stops are Delivered or Failed."""
        run = self.get_object()

        if run.status != RunStatus.EN_ROUTE:
            return Response(
                {'detail': _('Only EN_ROUTE runs can be completed.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.delivery_stops.models import StopStatus
        unfinished = run.stops.exclude(status__in=[StopStatus.DELIVERED, StopStatus.FAILED])
        if unfinished.exists():
            remaining = list(unfinished.values_list('stop_sequence', flat=True))
            return Response(
                {'detail': _('All stops must be Delivered or Failed before completing. Remaining stops: %(stops)s') % {
                    'stops': remaining,
                }},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            run.status = RunStatus.COMPLETED
            run.completed_at = timezone.now()
            run.save()

            driver = run.driver
            driver.status = DriverStatus.AVAILABLE
            driver.save()

        return Response(
            DeliveryRunSerializer(run).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='bank-cash')
    def bank_cash(self, request, pk=None):
        """Bank cash collected from a completed run.

        Accepts: {"cash_banked_location": "Cairo Branch"}
        """
        run = self.get_object()

        if run.status != RunStatus.COMPLETED:
            return Response(
                {'detail': _('Only COMPLETED runs can have cash banked.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cash_banked_location = request.data.get('cash_banked_location', '').strip()
        if not cash_banked_location:
            return Response(
                {'detail': _('cash_banked_location is required.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            run.status = RunStatus.CASH_BANKED
            run.cash_banked_at = timezone.now()
            run.cash_banked_location = cash_banked_location
            run.save()

            from apps.orders.models import Order
            order_ids = run.stops.values_list('order_id', flat=True)
            Order.objects.filter(
                id__in=order_ids,
                status=OrderStatus.DELIVERED,
            ).update(status=OrderStatus.CASH_BANKED)

        return Response(
            DeliveryRunSerializer(run).data,
            status=status.HTTP_200_OK,
        )
