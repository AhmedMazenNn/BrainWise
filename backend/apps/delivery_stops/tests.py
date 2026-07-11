from decimal import Decimal

from django.test import TestCase
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import RoleChoices, User
from apps.drivers.models import Driver, DriverStatus
from apps.delivery_runs.models import DeliveryRun, RunStatus
from apps.orders.models import Order, OrderStatus

from .models import DeliveryStop, StopStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_user_counter = 0


def _next_counter():
    global _user_counter
    _user_counter += 1
    return _user_counter


def _create_user(role=RoleChoices.MANAGER, **kwargs):
    n = _next_counter()
    defaults = {
        'email': f'{role.lower()}_{n}@example.com',
        'password': 'testpass123',
        'username': f'{role.lower()}_{n}',
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults, role=role)


def _auth_header(user):
    refresh = RefreshToken.for_user(user)
    return f'Bearer {str(refresh.access_token)}'


def _create_driver(user=None, **kwargs):
    if user is None:
        user = _create_user(role=RoleChoices.DRIVER)
    defaults = {
        'user': user,
        'name': 'Test Driver',
        'phone_number': '+1234567890',
        'active': True,
        'max_stops_per_run': 5,
        'status': DriverStatus.AVAILABLE,
    }
    defaults.update(kwargs)
    return Driver.objects.create(**defaults)


def _create_delivery_run(driver=None, **kwargs):
    if driver is None:
        driver = _create_driver()
    defaults = {
        'driver': driver,
        'status': RunStatus.DRAFT,
        'total_cash_collected': Decimal('0.00'),
    }
    defaults.update(kwargs)
    return DeliveryRun.objects.create(**defaults)


def _create_order(**kwargs):
    defaults = {
        'customer_name': 'Test Customer',
        'customer_phone': '+201234567890',
        'address': '15 El Tahrir St, Cairo',
        'cash_amount': Decimal('100.00'),
    }
    defaults.update(kwargs)
    return Order.objects.create(**defaults)


def _create_delivery_stop(delivery_run=None, order=None, **kwargs):
    if delivery_run is None:
        delivery_run = _create_delivery_run()
    if order is None:
        order = _create_order()
    defaults = {
        'delivery_run': delivery_run,
        'order': order,
        'stop_sequence': 1,
        'customer_name': order.customer_name,
        'address': order.address,
        'cash_amount': order.cash_amount,
        'status': StopStatus.ASSIGNED,
    }
    defaults.update(kwargs)
    return DeliveryStop.objects.create(**defaults)


def _build_delivery_stop(**kwargs):
    """Build a DeliveryStop instance without saving (for validation tests)."""
    delivery_run = kwargs.pop('delivery_run', None)
    order = kwargs.pop('order', None)
    if delivery_run is None:
        delivery_run = _create_delivery_run()
    if order is None:
        order = _create_order()
    defaults = {
        'delivery_run': delivery_run,
        'order': order,
        'stop_sequence': 1,
        'customer_name': order.customer_name,
        'address': order.address,
        'cash_amount': order.cash_amount,
        'status': StopStatus.ASSIGNED,
    }
    defaults.update(kwargs)
    return DeliveryStop(**defaults)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class DeliveryStopModelTests(TestCase):
    def test_create_valid_stop(self):
        order = _create_order(customer_name='Ahmed Ali', cash_amount=Decimal('250.00'))
        run = _create_delivery_run()
        stop = _create_delivery_stop(delivery_run=run, order=order, stop_sequence=1)
        self.assertEqual(stop.delivery_run, run)
        self.assertEqual(stop.order, order)
        self.assertEqual(stop.stop_sequence, 1)
        self.assertEqual(stop.customer_name, 'Ahmed Ali')
        self.assertEqual(stop.address, '15 El Tahrir St, Cairo')
        self.assertEqual(stop.cash_amount, Decimal('250.00'))
        self.assertEqual(stop.status, StopStatus.ASSIGNED)
        self.assertIsNone(stop.delivered_at)
        self.assertEqual(stop.failed_reason, '')
        self.assertIsNotNone(stop.created_at)
        self.assertIsNotNone(stop.updated_at)

    def test_stop_str(self):
        order = _create_order(customer_name='Sara Hassan')
        stop = _create_delivery_stop(order=order, stop_sequence=3)
        self.assertEqual(str(stop), 'Stop #3 - Sara Hassan (Assigned)')

    def test_stop_str_delivered(self):
        order = _create_order(customer_name='Mohamed')
        stop = _create_delivery_stop(order=order, status=StopStatus.DELIVERED)
        self.assertEqual(str(stop), 'Stop #1 - Mohamed (Delivered)')

    def test_default_status_is_assigned(self):
        stop = _create_delivery_stop()
        self.assertEqual(stop.status, StopStatus.ASSIGNED)

    def test_missing_delivery_run(self):
        stop = _build_delivery_stop(delivery_run=None)
        with self.assertRaises(ValidationError):
            stop.full_clean()

    def test_missing_order(self):
        stop = _build_delivery_stop(order=None)
        with self.assertRaises(ValidationError):
            stop.full_clean()

    def test_invalid_stop_sequence_zero(self):
        stop = _build_delivery_stop(stop_sequence=0)
        with self.assertRaises(ValidationError):
            stop.full_clean()

    def test_invalid_stop_sequence_negative(self):
        stop = _build_delivery_stop(stop_sequence=-1)
        with self.assertRaises(ValidationError):
            stop.full_clean()

    def test_valid_stop_sequence(self):
        stop = _build_delivery_stop(stop_sequence=1)
        stop.full_clean()

    def test_negative_cash_amount(self):
        stop = _build_delivery_stop(cash_amount=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            stop.full_clean()

    def test_zero_cash_is_valid(self):
        stop = _build_delivery_stop(cash_amount=Decimal('0.00'))
        stop.full_clean()

    def test_invalid_status(self):
        stop = _build_delivery_stop()
        stop.status = 'INVALID_STATUS'
        with self.assertRaises(ValidationError):
            stop.full_clean()

    def test_all_status_choices(self):
        for status_val in StopStatus.values:
            stop = _build_delivery_stop(status=status_val)
            stop.full_clean()

    def test_save_calls_full_clean(self):
        stop = _build_delivery_stop(stop_sequence=0)
        with self.assertRaises(ValidationError):
            stop.save()

    def test_order_one_to_one(self):
        order = _create_order()
        _create_delivery_stop(order=order, stop_sequence=1)
        order2 = _create_order(customer_name='Second', address='Addr2')
        _create_delivery_stop(order=order2, stop_sequence=2)
        with self.assertRaises(Exception):
            _create_delivery_stop(order=order, stop_sequence=3)

    def test_stops_count_on_delivery_run(self):
        run = _create_delivery_run()
        self.assertEqual(run.stops_count, 0)
        _create_delivery_stop(delivery_run=run, stop_sequence=1)
        self.assertEqual(run.stops_count, 1)
        _create_delivery_stop(delivery_run=run, stop_sequence=2)
        self.assertEqual(run.stops_count, 2)


# ---------------------------------------------------------------------------
# Serializer Tests
# ---------------------------------------------------------------------------

class DeliveryStopSerializerTests(TestCase):
    def setUp(self):
        from .serializers import DeliveryStopSerializer
        self.order = _create_order(customer_name='Test Customer', cash_amount=Decimal('150.00'))
        self.run = _create_delivery_run()
        self.stop = _create_delivery_stop(delivery_run=self.run, order=self.order)
        self.serializer = DeliveryStopSerializer(self.stop)

    def test_serializer_fields(self):
        data = self.serializer.data
        expected = {
            'id', 'delivery_run', 'order', 'stop_sequence',
            'customer_name', 'address', 'cash_amount',
            'status', 'delivered_at', 'failed_reason',
            'created_at', 'updated_at',
        }
        self.assertEqual(set(data.keys()), expected)

    def test_serializer_read_only_fields(self):
        meta = self.serializer.Meta
        self.assertIn('id', meta.read_only_fields)
        self.assertIn('customer_name', meta.read_only_fields)
        self.assertIn('address', meta.read_only_fields)
        self.assertIn('cash_amount', meta.read_only_fields)
        self.assertIn('created_at', meta.read_only_fields)
        self.assertIn('updated_at', meta.read_only_fields)

    def test_serializer_customer_name_from_order(self):
        self.assertEqual(self.serializer.data['customer_name'], 'Test Customer')

    def test_serializer_invalid_stop_sequence(self):
        from .serializers import DeliveryStopSerializer
        s = DeliveryStopSerializer(self.stop, data={'stop_sequence': 0}, partial=True)
        self.assertFalse(s.is_valid())
        self.assertIn('stop_sequence', s.errors)

    def test_serializer_invalid_cash_negative(self):
        from .serializers import DeliveryStopSerializer
        s = DeliveryStopSerializer(self.stop, data={'cash_amount': '-50.00'}, partial=True)
        self.assertFalse(s.is_valid())
        self.assertIn('cash_amount', s.errors)

    def test_serializer_valid_update_status(self):
        from .serializers import DeliveryStopSerializer
        s = DeliveryStopSerializer(self.stop, data={'status': StopStatus.EN_ROUTE}, partial=True)
        self.assertTrue(s.is_valid())
        updated = s.save()
        self.assertEqual(updated.status, StopStatus.EN_ROUTE)


# ---------------------------------------------------------------------------
# Permission Tests
# ---------------------------------------------------------------------------

class DeliveryStopPermissionTests(TestCase):
    def setUp(self):
        from .permissions import DeliveryStopPermission
        self.permission = DeliveryStopPermission()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.driver_user = _create_user(role=RoleChoices.DRIVER)
        self.driver = _create_driver(user=self.driver_user)
        self.run = _create_delivery_run(driver=self.driver)
        self.order = _create_order()
        self.stop = _create_delivery_stop(delivery_run=self.run, order=self.order)

    def _mock_request(self, user, method='GET'):
        class MockRequest:
            def __init__(self, u, m):
                self.user = u
                self.method = m
        return MockRequest(user, method)

    def _mock_view(self):
        return object()

    def test_manager_allowed_list(self):
        self.assertTrue(self.permission.has_permission(self._mock_request(self.manager), self._mock_view()))

    def test_dispatcher_allowed_list(self):
        self.assertTrue(self.permission.has_permission(self._mock_request(self.dispatcher), self._mock_view()))

    def test_driver_allowed_read(self):
        self.assertTrue(self.permission.has_permission(self._mock_request(self.driver_user), self._mock_view()))

    def test_driver_denied_write(self):
        self.assertFalse(self.permission.has_permission(self._mock_request(self.driver_user, 'POST'), self._mock_view()))

    def test_unauthenticated_denied(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(self.permission.has_permission(self._mock_request(AnonymousUser()), self._mock_view()))

    def test_driver_object_permission_own_stop(self):
        self.assertTrue(
            self.permission.has_object_permission(
                self._mock_request(self.driver_user), self._mock_view(), self.stop
            )
        )

    def test_driver_object_permission_other_stop(self):
        other_user = _create_user(role=RoleChoices.DRIVER)
        other_driver = _create_driver(user=other_user, name='Other Driver', phone_number='+9999999999')
        other_run = _create_delivery_run(driver=other_driver)
        other_order = _create_order(customer_name='Other', address='Other Addr')
        other_stop = _create_delivery_stop(delivery_run=other_run, order=other_order)
        self.assertFalse(
            self.permission.has_object_permission(
                self._mock_request(self.driver_user), self._mock_view(), other_stop
            )
        )

    def test_manager_object_permission(self):
        self.assertTrue(
            self.permission.has_object_permission(
                self._mock_request(self.manager), self._mock_view(), self.stop
            )
        )


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------

class DeliveryStopAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.driver_user = _create_user(role=RoleChoices.DRIVER)
        self.driver = _create_driver(user=self.driver_user, name='Alpha Driver')
        self.url = '/api/delivery-stops/'
        self.run = _create_delivery_run(driver=self.driver)
        self.order = _create_order(customer_name='Alpha Customer', cash_amount=Decimal('200.00'))
        self.stop = _create_delivery_stop(delivery_run=self.run, order=self.order, stop_sequence=1)

    def _auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(user))

    # -- Create --
    def test_create_stop_as_manager(self):
        self._auth(self.manager)
        run2 = _create_delivery_run()
        order2 = _create_order(customer_name='New Customer', address='New Addr')
        response = self.client.post(self.url, {
            'delivery_run': run2.pk,
            'order': order2.pk,
            'stop_sequence': 1,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['customer_name'], 'New Customer')
        self.assertEqual(response.data['address'], 'New Addr')
        self.assertEqual(response.data['cash_amount'], '100.00')

    def test_create_stop_as_dispatcher(self):
        self._auth(self.dispatcher)
        run2 = _create_delivery_run()
        order2 = _create_order(customer_name='Disp Order', address='Disp Addr')
        response = self.client.post(self.url, {
            'delivery_run': run2.pk,
            'order': order2.pk,
            'stop_sequence': 1,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_stop_as_driver_forbidden(self):
        self._auth(self.driver_user)
        response = self.client.post(self.url, {
            'delivery_run': self.run.pk,
            'order': self.order.pk,
            'stop_sequence': 1,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_stop_unauthorized(self):
        response = self.client.post(self.url, {
            'delivery_run': self.run.pk,
            'order': self.order.pk,
            'stop_sequence': 1,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_stop_invalid_data(self):
        self._auth(self.manager)
        response = self.client.post(self.url, {
            'delivery_run': self.run.pk,
            'order': self.order.pk,
            'stop_sequence': 0,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- List --
    def test_list_stops_as_manager(self):
        self._auth(self.manager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_list_stops_as_driver(self):
        self._auth(self.driver_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_stops_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- Retrieve --
    def test_retrieve_stop_as_manager(self):
        self._auth(self.manager)
        response = self.client.get(f'{self.url}{self.stop.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['customer_name'], 'Alpha Customer')

    def test_retrieve_stop_as_driver_own(self):
        self._auth(self.driver_user)
        response = self.client.get(f'{self.url}{self.stop.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_stop_as_driver_other_forbidden(self):
        other_user = _create_user(role=RoleChoices.DRIVER)
        other_driver = _create_driver(user=other_user, name='Other', phone_number='+9999999999')
        other_run = _create_delivery_run(driver=other_driver)
        other_order = _create_order(customer_name='Other', address='Other Addr')
        other_stop = _create_delivery_stop(delivery_run=other_run, order=other_order)
        self._auth(self.driver_user)
        response = self.client.get(f'{self.url}{other_stop.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_stop_not_found(self):
        self._auth(self.manager)
        response = self.client.get(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- Update (PUT) --
    def test_update_stop_as_manager(self):
        self._auth(self.manager)
        run2 = _create_delivery_run()
        order2 = _create_order(customer_name='Updated', address='Updated Addr')
        response = self.client.put(f'{self.url}{self.stop.pk}/', {
            'delivery_run': run2.pk,
            'order': order2.pk,
            'stop_sequence': 5,
            'status': StopStatus.EN_ROUTE,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], StopStatus.EN_ROUTE)
        self.assertEqual(response.data['customer_name'], 'Updated')

    def test_update_stop_as_driver_forbidden(self):
        self._auth(self.driver_user)
        response = self.client.put(f'{self.url}{self.stop.pk}/', {
            'delivery_run': self.run.pk,
            'order': self.order.pk,
            'stop_sequence': 1,
            'status': StopStatus.DELIVERED,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # -- Partial Update (PATCH) --
    def test_patch_stop_status(self):
        self._auth(self.manager)
        response = self.client.patch(f'{self.url}{self.stop.pk}/', {
            'status': StopStatus.EN_ROUTE,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], StopStatus.EN_ROUTE)

    def test_patch_stop_invalid_sequence(self):
        self._auth(self.manager)
        response = self.client.patch(f'{self.url}{self.stop.pk}/', {
            'stop_sequence': 0,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- Delete --
    def test_delete_stop_draft_run(self):
        self._auth(self.manager)
        response = self.client.delete(f'{self.url}{self.stop.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DeliveryStop.objects.filter(pk=self.stop.pk).exists())

    def test_delete_stop_non_draft_run(self):
        self._auth(self.manager)
        run = _create_delivery_run(status=RunStatus.EN_ROUTE)
        order = _create_order(customer_name='No Delete', address='Addr')
        stop = _create_delivery_stop(delivery_run=run, order=order)
        response = self.client.delete(f'{self.url}{stop.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_stop_as_driver_forbidden(self):
        self._auth(self.driver_user)
        response = self.client.delete(f'{self.url}{self.stop.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Filtering Tests
# ---------------------------------------------------------------------------

class DeliveryStopFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-stops/'

        self.run1 = _create_delivery_run()
        self.run2 = _create_delivery_run()
        self.order1 = _create_order(customer_name='Order One')
        self.order2 = _create_order(customer_name='Order Two')
        self.order3 = _create_order(customer_name='Order Three')

        _create_delivery_stop(delivery_run=self.run1, order=self.order1, stop_sequence=1, status=StopStatus.ASSIGNED)
        _create_delivery_stop(delivery_run=self.run2, order=self.order2, stop_sequence=1, status=StopStatus.DELIVERED)
        _create_delivery_stop(delivery_run=self.run1, order=self.order3, stop_sequence=2, status=StopStatus.ASSIGNED)

    def test_filter_by_status_assigned(self):
        response = self.client.get(self.url, {'status': 'ASSIGNED'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_by_status_delivered(self):
        response = self.client.get(self.url, {'status': 'DELIVERED'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_by_delivery_run(self):
        response = self.client.get(self.url, {'delivery_run': self.run1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_by_order(self):
        response = self.client.get(self.url, {'order': self.order1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_combined_filter(self):
        response = self.client.get(self.url, {'status': 'ASSIGNED', 'delivery_run': self.run1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)


# ---------------------------------------------------------------------------
# Search Tests
# ---------------------------------------------------------------------------

class DeliveryStopSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-stops/'

        order1 = _create_order(customer_name='Mohamed Ahmed', address='15 El Tahrir St')
        order2 = _create_order(customer_name='Sara Hassan', address='25 Maadi St')
        _create_delivery_stop(order=order1, stop_sequence=1)
        _create_delivery_stop(order=order2, stop_sequence=2)

    def test_search_by_customer_name(self):
        response = self.client.get(self.url, {'search': 'Mohamed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [s['customer_name'] for s in response.data['results']]
        self.assertIn('Mohamed Ahmed', names)
        self.assertNotIn('Sara Hassan', names)

    def test_search_by_address(self):
        response = self.client.get(self.url, {'search': 'Maadi'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [s['customer_name'] for s in response.data['results']]
        self.assertIn('Sara Hassan', names)
        self.assertNotIn('Mohamed Ahmed', names)

    def test_search_no_results(self):
        response = self.client.get(self.url, {'search': 'ZZZZZZZ'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)


# ---------------------------------------------------------------------------
# Ordering Tests
# ---------------------------------------------------------------------------

class DeliveryStopOrderingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-stops/'
        run = _create_delivery_run()

        o1 = _create_order(customer_name='First', cash_amount=Decimal('50.00'))
        o2 = _create_order(customer_name='Second', cash_amount=Decimal('200.00'))
        o3 = _create_order(customer_name='Third', cash_amount=Decimal('100.00'))

        self.s1 = _create_delivery_stop(delivery_run=run, order=o1, stop_sequence=1)
        self.s2 = _create_delivery_stop(delivery_run=run, order=o2, stop_sequence=3)
        self.s3 = _create_delivery_stop(delivery_run=run, order=o3, stop_sequence=2)

    def test_order_by_stop_sequence_ascending(self):
        response = self.client.get(self.url, {'ordering': 'stop_sequence'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sequences = [s['stop_sequence'] for s in response.data['results']]
        self.assertEqual(sequences, [1, 2, 3])

    def test_order_by_stop_sequence_descending(self):
        response = self.client.get(self.url, {'ordering': '-stop_sequence'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sequences = [s['stop_sequence'] for s in response.data['results']]
        self.assertEqual(sequences, [3, 2, 1])

    def test_order_by_cash_amount_ascending(self):
        response = self.client.get(self.url, {'ordering': 'cash_amount'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        amounts = [Decimal(s['cash_amount']) for s in response.data['results']]
        self.assertEqual(amounts, sorted(amounts))

    def test_order_by_cash_amount_descending(self):
        response = self.client.get(self.url, {'ordering': '-cash_amount'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        amounts = [Decimal(s['cash_amount']) for s in response.data['results']]
        self.assertEqual(amounts, sorted(amounts, reverse=True))

    def test_default_ordering_by_stop_sequence(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sequences = [s['stop_sequence'] for s in response.data['results']]
        self.assertEqual(sequences, [1, 2, 3])

    def test_invalid_ordering_field_ignored(self):
        response = self.client.get(self.url, {'ordering': 'nonexistent'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------

class DeliveryStopAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/delivery-stops/'
        self.user = _create_user(role=RoleChoices.MANAGER)

    def test_no_auth_header(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid.token.here')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_valid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.user))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_wrong_method_post_without_auth(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# HTTP Status Code Tests
# ---------------------------------------------------------------------------

class DeliveryStopStatusCodesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-stops/'
        self.run = _create_delivery_run()
        self.order = _create_order()
        self.stop = _create_delivery_stop(delivery_run=self.run, order=self.order)

    def test_200_on_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_201_on_create(self):
        order2 = _create_order(customer_name='New', address='New Addr')
        response = self.client.post(self.url, {
            'delivery_run': self.run.pk,
            'order': order2.pk,
            'stop_sequence': 5,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_204_on_delete(self):
        response = self.client.delete(f'{self.url}{self.stop.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_400_on_invalid_data(self):
        response = self.client.post(self.url, {
            'delivery_run': self.run.pk,
            'order': self.order.pk,
            'stop_sequence': 0,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_404_on_nonexistent(self):
        response = self.client.get(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_405_on_wrong_method(self):
        response = self.client.put(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ---------------------------------------------------------------------------
# Dispatcher CRUD Tests
# ---------------------------------------------------------------------------

class DeliveryStopDispatcherCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.url = '/api/delivery-stops/'
        self.run = _create_delivery_run()
        self.order = _create_order()
        self.stop = _create_delivery_stop(delivery_run=self.run, order=self.order)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.dispatcher))

    def test_dispatcher_retrieve(self):
        response = self.client.get(f'{self.url}{self.stop.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dispatcher_patch(self):
        response = self.client.patch(f'{self.url}{self.stop.pk}/', {
            'status': StopStatus.EN_ROUTE,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], StopStatus.EN_ROUTE)

    def test_dispatcher_create(self):
        order2 = _create_order(customer_name='Disp Order', address='Disp Addr')
        response = self.client.post(self.url, {
            'delivery_run': self.run.pk,
            'order': order2.pk,
            'stop_sequence': 10,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_dispatcher_delete(self):
        response = self.client.delete(f'{self.url}{self.stop.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_dispatcher_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Delete Business Rule Tests
# ---------------------------------------------------------------------------

class DeliveryStopDeleteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-stops/'

    def test_delete_draft_run_stop_succeeds(self):
        run = _create_delivery_run(status=RunStatus.DRAFT)
        order = _create_order()
        stop = _create_delivery_stop(delivery_run=run, order=order)
        response = self.client.delete(f'{self.url}{stop.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_assigned_run_stop_fails(self):
        run = _create_delivery_run(status=RunStatus.ASSIGNED)
        order = _create_order()
        stop = _create_delivery_stop(delivery_run=run, order=order)
        response = self.client.delete(f'{self.url}{stop.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_en_route_run_stop_fails(self):
        run = _create_delivery_run(status=RunStatus.EN_ROUTE)
        order = _create_order()
        stop = _create_delivery_stop(delivery_run=run, order=order)
        response = self.client.delete(f'{self.url}{stop.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_completed_run_stop_fails(self):
        run = _create_delivery_run(status=RunStatus.COMPLETED)
        order = _create_order()
        stop = _create_delivery_stop(delivery_run=run, order=order)
        response = self.client.delete(f'{self.url}{stop.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_nonexistent_returns_404(self):
        response = self.client.delete(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Pagination Tests
# ---------------------------------------------------------------------------

class DeliveryStopPaginationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-stops/'
        run = _create_delivery_run()
        for i in range(5):
            order = _create_order(customer_name=f'Customer {i}', address=f'Addr {i}')
            _create_delivery_stop(delivery_run=run, order=order, stop_sequence=i + 1)

    def test_pagination_structure(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)

    def test_pagination_page_size(self):
        response = self.client.get(self.url, {'page_size': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data['results']), 2)

    def test_pagination_page_number(self):
        response = self.client.get(self.url, {'page': 1, 'page_size': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertIsNotNone(response.data['next'])

    def test_pagination_last_page(self):
        response = self.client.get(self.url, {'page': 3, 'page_size': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIsNone(response.data['next'])


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------

class DeliveryStopEdgeCaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-stops/'

    def test_malformed_json(self):
        response = self.client.post(
            self.url,
            data='{invalid json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_nonexistent(self):
        response = self.client.get(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_nonexistent(self):
        response = self.client.patch(
            f'{self.url}99999/',
            {'status': 'DELIVERED'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent(self):
        response = self.client.delete(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_not_allowed_on_detail(self):
        run = _create_delivery_run()
        order = _create_order()
        stop = _create_delivery_stop(delivery_run=run, order=order)
        response = self.client.post(f'{self.url}{stop.pk}/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_with_nonexistent_delivery_run(self):
        order = _create_order()
        response = self.client.post(self.url, {
            'delivery_run': 99999,
            'order': order.pk,
            'stop_sequence': 1,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_nonexistent_order(self):
        run = _create_delivery_run()
        response = self.client.post(self.url, {
            'delivery_run': run.pk,
            'order': 99999,
            'stop_sequence': 1,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_empty_body(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Admin Tests
# ---------------------------------------------------------------------------

class DeliveryStopAdminTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = _create_user(
            role=RoleChoices.MANAGER,
            username='admin_ds_test',
            email='admin_ds_test@example.com',
        )
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()

    def test_admin_list_page(self):
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin/delivery_stops/deliverystop/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_changelist_page(self):
        self.client.force_login(self.admin_user)
        run = _create_delivery_run()
        order = _create_order()
        _create_delivery_stop(delivery_run=run, order=order)
        response = self.client.get('/admin/delivery_stops/deliverystop/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Workflow Action Tests
# ---------------------------------------------------------------------------

class MarkDeliveredActionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.driver_user = _create_user(role=RoleChoices.DRIVER)
        self.driver = _create_driver(user=self.driver_user, name='Delivered Driver')
        self.url = '/api/delivery-stops/'
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))

    def test_mark_delivered_basic(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order(customer_name='C1', cash_amount=Decimal('100.00'))
        stop = _create_delivery_stop(
            delivery_run=run, order=order, stop_sequence=1,
            status=StopStatus.EN_ROUTE,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-delivered/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], StopStatus.DELIVERED)
        self.assertIsNotNone(response.data['delivered_at'])
        stop.refresh_from_db()
        order.refresh_from_db()
        run.refresh_from_db()
        self.assertEqual(stop.status, StopStatus.DELIVERED)
        self.assertIsNotNone(stop.delivered_at)
        self.assertEqual(order.status, OrderStatus.DELIVERED)
        self.assertEqual(run.total_cash_collected, Decimal('100.00'))

    def test_mark_delivered_from_assigned_status(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.ASSIGNED)
        order = _create_order(cash_amount=Decimal('50.00'))
        stop = _create_delivery_stop(
            delivery_run=run, order=order, stop_sequence=1,
            status=StopStatus.ASSIGNED,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-delivered/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], StopStatus.DELIVERED)

    def test_mark_delivered_adds_to_run_cash(self):
        run = _create_delivery_run(
            driver=self.driver, status=RunStatus.EN_ROUTE,
            total_cash_collected=Decimal('50.00'),
        )
        order = _create_order(cash_amount=Decimal('75.00'))
        stop = _create_delivery_stop(
            delivery_run=run, order=order, stop_sequence=1,
            status=StopStatus.EN_ROUTE,
        )
        self.client.post(f'{self.url}{stop.pk}/mark-delivered/', format='json')
        run.refresh_from_db()
        self.assertEqual(run.total_cash_collected, Decimal('125.00'))

    def test_mark_delivered_already_delivered_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.DELIVERED,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-delivered/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_delivered_failed_stop_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.FAILED,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-delivered/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_delivered_run_not_active_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.COMPLETED)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.EN_ROUTE,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-delivered/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_delivered_as_dispatcher(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.dispatcher))
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.EN_ROUTE,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-delivered/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_mark_delivered_as_driver_own_stop(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.driver_user))
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.EN_ROUTE,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-delivered/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_mark_delivered_as_driver_other_stop_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.driver_user))
        other_user = _create_user(role=RoleChoices.DRIVER)
        other_driver = _create_driver(user=other_user, name='Other', phone_number='+9999999999')
        other_run = _create_delivery_run(driver=other_driver, status=RunStatus.EN_ROUTE)
        other_order = _create_order(customer_name='Other', address='Other Addr')
        other_stop = _create_delivery_stop(
            delivery_run=other_run, order=other_order, status=StopStatus.EN_ROUTE,
        )
        response = self.client.post(f'{self.url}{other_stop.pk}/mark-delivered/', format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_mark_delivered_unauthorized(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.EN_ROUTE,
        )
        self.client.credentials()
        response = self.client.post(f'{self.url}{stop.pk}/mark-delivered/', format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MarkFailedActionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.driver_user = _create_user(role=RoleChoices.DRIVER)
        self.driver = _create_driver(user=self.driver_user, name='Failed Driver')
        self.url = '/api/delivery-stops/'
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))

    def test_mark_failed_basic(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order(customer_name='C1')
        stop = _create_delivery_stop(
            delivery_run=run, order=order, stop_sequence=1,
            status=StopStatus.EN_ROUTE,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-failed/', {
            'failed_reason': 'Customer not home',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], StopStatus.FAILED)
        self.assertEqual(response.data['failed_reason'], 'Customer not home')
        stop.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(stop.status, StopStatus.FAILED)
        self.assertEqual(stop.failed_reason, 'Customer not home')
        self.assertEqual(order.status, OrderStatus.FAILED)

    def test_mark_failed_from_assigned_status(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.ASSIGNED)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.ASSIGNED,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-failed/', {
            'failed_reason': 'Wrong address',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_mark_failed_missing_reason(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.EN_ROUTE,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-failed/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('failed_reason', str(response.data))

    def test_mark_failed_empty_reason(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.EN_ROUTE,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-failed/', {
            'failed_reason': '   ',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_failed_already_failed_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.FAILED,
            failed_reason='Already failed',
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-failed/', {
            'failed_reason': 'Again',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_failed_delivered_stop_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.DELIVERED,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-failed/', {
            'failed_reason': 'Reason',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_failed_run_not_active_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.COMPLETED)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.EN_ROUTE,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-failed/', {
            'failed_reason': 'Reason',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_failed_does_not_affect_cash(self):
        run = _create_delivery_run(
            driver=self.driver, status=RunStatus.EN_ROUTE,
            total_cash_collected=Decimal('50.00'),
        )
        order = _create_order(cash_amount=Decimal('100.00'))
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.EN_ROUTE,
        )
        self.client.post(f'{self.url}{stop.pk}/mark-failed/', {
            'failed_reason': 'No cash collected',
        }, format='json')
        run.refresh_from_db()
        self.assertEqual(run.total_cash_collected, Decimal('50.00'))

    def test_mark_failed_as_dispatcher(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.dispatcher))
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.EN_ROUTE,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-failed/', {
            'failed_reason': 'Dispatcher reason',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_mark_failed_as_driver_own_stop(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.driver_user))
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.EN_ROUTE,
        )
        response = self.client.post(f'{self.url}{stop.pk}/mark-failed/', {
            'failed_reason': 'Driver reported',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_mark_failed_as_driver_other_stop_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.driver_user))
        other_user = _create_user(role=RoleChoices.DRIVER)
        other_driver = _create_driver(user=other_user, name='Other', phone_number='+9999999999')
        other_run = _create_delivery_run(driver=other_driver, status=RunStatus.EN_ROUTE)
        other_order = _create_order(customer_name='Other', address='Other Addr')
        other_stop = _create_delivery_stop(
            delivery_run=other_run, order=other_order, status=StopStatus.EN_ROUTE,
        )
        response = self.client.post(f'{self.url}{other_stop.pk}/mark-failed/', {
            'failed_reason': 'Not mine',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_mark_failed_unauthorized(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        order = _create_order()
        stop = _create_delivery_stop(
            delivery_run=run, order=order, status=StopStatus.EN_ROUTE,
        )
        self.client.credentials()
        response = self.client.post(f'{self.url}{stop.pk}/mark-failed/', {
            'failed_reason': 'Reason',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mark_failed_multiple_stops_one_delivered_one_failed(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        o1 = _create_order(customer_name='OK', cash_amount=Decimal('100.00'))
        o2 = _create_order(customer_name='Fail', cash_amount=Decimal('50.00'))
        s1 = _create_delivery_stop(
            delivery_run=run, order=o1, stop_sequence=1, status=StopStatus.EN_ROUTE,
        )
        s2 = _create_delivery_stop(
            delivery_run=run, order=o2, stop_sequence=2, status=StopStatus.EN_ROUTE,
        )
        self.client.post(f'{self.url}{s1.pk}/mark-delivered/', format='json')
        self.client.post(f'{self.url}{s2.pk}/mark-failed/', {
            'failed_reason': 'Customer refused',
        }, format='json')
        s1.refresh_from_db()
        s2.refresh_from_db()
        run.refresh_from_db()
        self.assertEqual(s1.status, StopStatus.DELIVERED)
        self.assertEqual(s2.status, StopStatus.FAILED)
        self.assertEqual(run.total_cash_collected, Decimal('100.00'))
