from decimal import Decimal

from django.test import TestCase
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import RoleChoices, User
from apps.drivers.models import Driver, DriverStatus

from .models import Order, OrderPriority, OrderStatus


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


def _create_order(**kwargs):
    defaults = {
        'customer_name': 'Test Customer',
        'customer_phone': '+201234567890',
        'address': '15 El Tahrir St, Cairo',
        'cash_amount': Decimal('100.00'),
        'priority': OrderPriority.MEDIUM,
        'status': OrderStatus.OPEN,
    }
    defaults.update(kwargs)
    return Order.objects.create(**defaults)


def _build_order(**kwargs):
    """Build an Order instance without saving (for validation tests)."""
    defaults = {
        'customer_name': 'Test Customer',
        'customer_phone': '+201234567890',
        'address': '15 El Tahrir St, Cairo',
        'cash_amount': Decimal('100.00'),
        'priority': OrderPriority.MEDIUM,
        'status': OrderStatus.OPEN,
    }
    defaults.update(kwargs)
    return Order(**defaults)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class OrderModelTests(TestCase):
    def test_create_valid_order(self):
        order = _create_order()
        self.assertEqual(order.customer_name, 'Test Customer')
        self.assertEqual(order.customer_phone, '+201234567890')
        self.assertEqual(order.address, '15 El Tahrir St, Cairo')
        self.assertEqual(order.cash_amount, Decimal('100.00'))
        self.assertEqual(order.priority, OrderPriority.MEDIUM)
        self.assertEqual(order.status, OrderStatus.OPEN)
        self.assertIsNone(order.assigned_driver)
        self.assertIsNone(order.delivered_at)
        self.assertIsNotNone(order.created_at)
        self.assertIsNotNone(order.updated_at)

    def test_order_str(self):
        order = _create_order(customer_name='Ahmed Ali', status=OrderStatus.OPEN)
        self.assertEqual(str(order), f'Order #{order.pk} - Ahmed Ali (Open)')

    def test_order_str_delivered(self):
        order = _create_order(customer_name='Sara', status=OrderStatus.DELIVERED)
        self.assertEqual(str(order), f'Order #{order.pk} - Sara (Delivered)')

    def test_missing_customer_name(self):
        order = _build_order(customer_name='')
        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_missing_customer_name_whitespace(self):
        order = _build_order(customer_name='   ')
        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_missing_address(self):
        order = _build_order(address='')
        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_missing_address_whitespace(self):
        order = _build_order(address='   ')
        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_negative_cash_amount(self):
        order = _build_order(cash_amount=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_zero_cash_amount_is_valid(self):
        order = _build_order(cash_amount=Decimal('0.00'))
        order.full_clean()

    def test_invalid_status(self):
        order = _build_order()
        order.status = 'INVALID_STATUS'
        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_invalid_priority(self):
        order = _build_order()
        order.priority = 'URGENT'
        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_default_status_is_open(self):
        order = Order.objects.create(
            customer_name='Default Status',
            address='123 Main St',
        )
        self.assertEqual(order.status, OrderStatus.OPEN)

    def test_default_priority_is_medium(self):
        order = Order.objects.create(
            customer_name='Default Priority',
            address='123 Main St',
        )
        self.assertEqual(order.priority, OrderPriority.MEDIUM)

    def test_default_cash_amount_is_zero(self):
        order = Order.objects.create(
            customer_name='Default Cash',
            address='123 Main St',
        )
        self.assertEqual(order.cash_amount, Decimal('0.00'))

    def test_save_calls_full_clean(self):
        order = _build_order(customer_name='')
        with self.assertRaises(ValidationError):
            order.save()

    def test_order_with_assigned_driver(self):
        driver = _create_driver()
        order = _create_order(assigned_driver=driver)
        self.assertEqual(order.assigned_driver, driver)

    def test_order_cascade_driver_set_null(self):
        driver = _create_driver()
        order = _create_order(assigned_driver=driver)
        driver.delete()
        order.refresh_from_db()
        self.assertIsNone(order.assigned_driver)

    def test_all_priority_choices(self):
        for priority in OrderPriority.values:
            order = _build_order(priority=priority)
            order.full_clean()

    def test_all_status_choices(self):
        for status_val in OrderStatus.values:
            order = _build_order(status=status_val)
            order.full_clean()


# ---------------------------------------------------------------------------
# Serializer Tests
# ---------------------------------------------------------------------------

class OrderSerializerTests(TestCase):
    def setUp(self):
        from .serializers import OrderSerializer
        self.order = _create_order()
        self.serializer = OrderSerializer(self.order)

    def test_serializer_fields(self):
        data = self.serializer.data
        expected = {
            'id', 'customer_name', 'customer_phone', 'address',
            'cash_amount', 'priority', 'status', 'assigned_driver',
            'created_at', 'delivered_at', 'updated_at',
        }
        self.assertEqual(set(data.keys()), expected)

    def test_serializer_read_only_fields(self):
        meta = self.serializer.Meta
        self.assertIn('id', meta.read_only_fields)
        self.assertIn('created_at', meta.read_only_fields)
        self.assertIn('updated_at', meta.read_only_fields)

    def test_serializer_invalid_customer_name_blank(self):
        from .serializers import OrderSerializer
        s = OrderSerializer(self.order, data={'customer_name': ''}, partial=True)
        self.assertFalse(s.is_valid())
        self.assertIn('customer_name', s.errors)

    def test_serializer_invalid_address_blank(self):
        from .serializers import OrderSerializer
        s = OrderSerializer(self.order, data={'address': ''}, partial=True)
        self.assertFalse(s.is_valid())
        self.assertIn('address', s.errors)

    def test_serializer_invalid_cash_amount_negative(self):
        from .serializers import OrderSerializer
        s = OrderSerializer(self.order, data={'cash_amount': '-50.00'}, partial=True)
        self.assertFalse(s.is_valid())
        self.assertIn('cash_amount', s.errors)

    def test_serializer_valid_update(self):
        from .serializers import OrderSerializer
        s = OrderSerializer(self.order, data={'customer_name': 'Updated Name'}, partial=True)
        self.assertTrue(s.is_valid())
        updated = s.save()
        self.assertEqual(updated.customer_name, 'Updated Name')


# ---------------------------------------------------------------------------
# Permission Tests
# ---------------------------------------------------------------------------

class OrderPermissionTests(TestCase):
    def setUp(self):
        from .permissions import IsManagerOrDispatcher
        self.permission = IsManagerOrDispatcher()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.driver = _create_user(role=RoleChoices.DRIVER)

    def _mock_request(self, user):
        class MockRequest:
            def __init__(self, u):
                self.user = u
        return MockRequest(user)

    def _mock_view(self):
        return object()

    def test_manager_allowed(self):
        self.assertTrue(self.permission.has_permission(self._mock_request(self.manager), self._mock_view()))

    def test_dispatcher_allowed(self):
        self.assertTrue(self.permission.has_permission(self._mock_request(self.dispatcher), self._mock_view()))

    def test_driver_rejected(self):
        self.assertFalse(self.permission.has_permission(self._mock_request(self.driver), self._mock_view()))

    def test_unauthenticated_rejected(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(self.permission.has_permission(self._mock_request(AnonymousUser()), self._mock_view()))


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------

class OrderAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.driver_user = _create_user(role=RoleChoices.DRIVER)
        self.url = '/api/orders/'
        self.order = _create_order(
            customer_name='Alpha Customer',
            customer_phone='+1111111111',
            address='10 Nasr St, Cairo',
            cash_amount=Decimal('250.00'),
            priority=OrderPriority.HIGH,
        )

    def _auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(user))

    # -- Create --
    def test_create_order_as_manager(self):
        self._auth(self.manager)
        response = self.client.post(self.url, {
            'customer_name': 'New Customer',
            'customer_phone': '+2222222222',
            'address': '20 Maadi St, Cairo',
            'cash_amount': '150.00',
            'priority': OrderPriority.LOW,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['customer_name'], 'New Customer')
        self.assertEqual(response.data['status'], OrderStatus.OPEN)

    def test_create_order_as_dispatcher(self):
        self._auth(self.dispatcher)
        response = self.client.post(self.url, {
            'customer_name': 'Dispatcher Created',
            'customer_phone': '+3333333333',
            'address': '30 Heliopolis, Cairo',
            'cash_amount': '75.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_order_as_driver_forbidden(self):
        self._auth(self.driver_user)
        response = self.client.post(self.url, {
            'customer_name': 'Nope',
            'address': 'Some address',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_order_unauthorized(self):
        response = self.client.post(self.url, {
            'customer_name': 'Unauth',
            'address': 'Some address',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_order_invalid_data(self):
        self._auth(self.manager)
        response = self.client.post(self.url, {
            'customer_name': '',
            'address': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- List --
    def test_list_orders_as_manager(self):
        self._auth(self.manager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_list_orders_as_dispatcher(self):
        self._auth(self.dispatcher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_orders_as_driver_forbidden(self):
        self._auth(self.driver_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_orders_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- Retrieve --
    def test_retrieve_order_as_manager(self):
        self._auth(self.manager)
        response = self.client.get(f'{self.url}{self.order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['customer_name'], 'Alpha Customer')

    def test_retrieve_order_not_found(self):
        self._auth(self.manager)
        response = self.client.get(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- Update (PUT) --
    def test_update_order_as_manager(self):
        self._auth(self.manager)
        response = self.client.put(f'{self.url}{self.order.pk}/', {
            'customer_name': 'Updated Customer',
            'customer_phone': '+9999999999',
            'address': 'Updated Address',
            'cash_amount': '300.00',
            'priority': OrderPriority.LOW,
            'status': OrderStatus.OPEN,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['customer_name'], 'Updated Customer')

    def test_update_order_as_dispatcher(self):
        self._auth(self.dispatcher)
        response = self.client.put(f'{self.url}{self.order.pk}/', {
            'customer_name': 'Disp Update',
            'customer_phone': '+8888888888',
            'address': 'Disp Address',
            'cash_amount': '200.00',
            'priority': OrderPriority.HIGH,
            'status': OrderStatus.OPEN,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # -- Partial Update (PATCH) --
    def test_patch_order_as_manager(self):
        self._auth(self.manager)
        response = self.client.patch(f'{self.url}{self.order.pk}/', {
            'customer_name': 'Patched Name',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['customer_name'], 'Patched Name')

    def test_patch_order_priority(self):
        self._auth(self.manager)
        response = self.client.patch(f'{self.url}{self.order.pk}/', {
            'priority': OrderPriority.HIGH,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['priority'], OrderPriority.HIGH)

    def test_patch_order_status(self):
        self._auth(self.manager)
        response = self.client.patch(f'{self.url}{self.order.pk}/', {
            'status': OrderStatus.ASSIGNED,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], OrderStatus.ASSIGNED)

    def test_patch_order_invalid_customer_name(self):
        self._auth(self.manager)
        response = self.client.patch(f'{self.url}{self.order.pk}/', {
            'customer_name': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- Delete --
    def test_delete_open_order_as_manager(self):
        self._auth(self.manager)
        order = _create_order(customer_name='To Delete', address='Del Address')
        response = self.client.delete(f'{self.url}{order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(pk=order.pk).exists())

    def test_delete_open_order_as_dispatcher(self):
        self._auth(self.dispatcher)
        order = _create_order(customer_name='Disp Delete', address='Del Address')
        response = self.client.delete(f'{self.url}{order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_non_open_order_forbidden(self):
        self._auth(self.manager)
        order = _create_order(
            customer_name='Assigned Order',
            address='Addr',
            status=OrderStatus.ASSIGNED,
        )
        response = self.client.delete(f'{self.url}{order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_delivered_order_forbidden(self):
        self._auth(self.manager)
        order = _create_order(
            customer_name='Delivered Order',
            address='Addr',
            status=OrderStatus.DELIVERED,
        )
        response = self.client.delete(f'{self.url}{order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_order_as_driver_forbidden(self):
        self._auth(self.driver_user)
        response = self.client.delete(f'{self.url}{self.order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Filtering Tests
# ---------------------------------------------------------------------------

class OrderFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/orders/'
        self.driver1 = _create_driver()
        self.driver2 = _create_driver()

        _create_order(
            customer_name='Alice',
            status=OrderStatus.OPEN,
            priority=OrderPriority.HIGH,
            assigned_driver=self.driver1,
        )
        _create_order(
            customer_name='Bob',
            status=OrderStatus.ASSIGNED,
            priority=OrderPriority.LOW,
            assigned_driver=self.driver2,
        )
        _create_order(
            customer_name='Charlie',
            status=OrderStatus.DELIVERED,
            priority=OrderPriority.MEDIUM,
        )

    def test_filter_by_status_open(self):
        response = self.client.get(self.url, {'status': 'OPEN'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [o['customer_name'] for o in response.data['results']]
        self.assertIn('Alice', names)
        self.assertNotIn('Bob', names)
        self.assertNotIn('Charlie', names)

    def test_filter_by_status_assigned(self):
        response = self.client.get(self.url, {'status': 'ASSIGNED'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [o['customer_name'] for o in response.data['results']]
        self.assertIn('Bob', names)

    def test_filter_by_priority_high(self):
        response = self.client.get(self.url, {'priority': 'HIGH'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [o['customer_name'] for o in response.data['results']]
        self.assertIn('Alice', names)
        self.assertNotIn('Bob', names)

    def test_filter_by_assigned_driver(self):
        response = self.client.get(self.url, {'assigned_driver': self.driver1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [o['customer_name'] for o in response.data['results']]
        self.assertIn('Alice', names)
        self.assertNotIn('Bob', names)
        self.assertNotIn('Charlie', names)

    def test_combined_filter(self):
        response = self.client.get(self.url, {'status': 'OPEN', 'priority': 'HIGH'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [o['customer_name'] for o in response.data['results']]
        self.assertIn('Alice', names)
        self.assertNotIn('Bob', names)


# ---------------------------------------------------------------------------
# Search Tests
# ---------------------------------------------------------------------------

class OrderSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/orders/'

        _create_order(
            customer_name='Mohamed Ahmed',
            customer_phone='+201234567890',
            address='15 El Tahrir St, Cairo',
        )
        _create_order(
            customer_name='Sara Hassan',
            customer_phone='+201987654321',
            address='25 Maadi St, Cairo',
        )

    def test_search_by_name(self):
        response = self.client.get(self.url, {'search': 'Mohamed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [o['customer_name'] for o in response.data['results']]
        self.assertIn('Mohamed Ahmed', names)
        self.assertNotIn('Sara Hassan', names)

    def test_search_by_phone(self):
        response = self.client.get(self.url, {'search': '01987'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [o['customer_name'] for o in response.data['results']]
        self.assertIn('Sara Hassan', names)
        self.assertNotIn('Mohamed Ahmed', names)

    def test_search_by_address(self):
        response = self.client.get(self.url, {'search': 'Maadi'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [o['customer_name'] for o in response.data['results']]
        self.assertIn('Sara Hassan', names)
        self.assertNotIn('Mohamed Ahmed', names)

    def test_search_no_results(self):
        response = self.client.get(self.url, {'search': 'ZZZZZZZ'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)


# ---------------------------------------------------------------------------
# Ordering Tests
# ---------------------------------------------------------------------------

class OrderOrderingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/orders/'

        self.o1 = _create_order(
            customer_name='Adam',
            cash_amount=Decimal('50.00'),
        )
        self.o2 = _create_order(
            customer_name='Zara',
            cash_amount=Decimal('200.00'),
        )
        self.o3 = _create_order(
            customer_name='Mike',
            cash_amount=Decimal('100.00'),
        )

    def test_order_by_created_at_ascending(self):
        response = self.client.get(self.url, {'ordering': 'created_at'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [o['id'] for o in response.data['results']]
        self.assertEqual(ids, [self.o1.pk, self.o2.pk, self.o3.pk])

    def test_order_by_created_at_descending(self):
        response = self.client.get(self.url, {'ordering': '-created_at'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [o['id'] for o in response.data['results']]
        self.assertEqual(ids, [self.o3.pk, self.o2.pk, self.o1.pk])

    def test_order_by_cash_amount_ascending(self):
        response = self.client.get(self.url, {'ordering': 'cash_amount'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        amounts = [Decimal(o['cash_amount']) for o in response.data['results']]
        self.assertEqual(amounts, sorted(amounts))

    def test_order_by_cash_amount_descending(self):
        response = self.client.get(self.url, {'ordering': '-cash_amount'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        amounts = [Decimal(o['cash_amount']) for o in response.data['results']]
        self.assertEqual(amounts, sorted(amounts, reverse=True))

    def test_order_by_customer_name_ascending(self):
        response = self.client.get(self.url, {'ordering': 'customer_name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [o['customer_name'] for o in response.data['results']]
        self.assertEqual(names, sorted(names))

    def test_order_by_customer_name_descending(self):
        response = self.client.get(self.url, {'ordering': '-customer_name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [o['customer_name'] for o in response.data['results']]
        self.assertEqual(names, sorted(names, reverse=True))

    def test_default_ordering_by_created_at_desc(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [o['id'] for o in response.data['results']]
        self.assertEqual(ids[0], self.o3.pk)

    def test_invalid_ordering_field_ignored(self):
        response = self.client.get(self.url, {'ordering': 'nonexistent'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------

class OrderAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/orders/'
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

class OrderStatusCodesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/orders/'
        self.order = _create_order(
            customer_name='SC Order',
            address='SC Address',
        )

    def test_200_on_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_201_on_create(self):
        response = self.client.post(self.url, {
            'customer_name': 'New',
            'address': 'New Address',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_204_on_delete(self):
        order = _create_order(customer_name='Del', address='Del Addr')
        response = self.client.delete(f'{self.url}{order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_404_on_nonexistent(self):
        response = self.client.get(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_400_on_invalid_data(self):
        response = self.client.post(self.url, {
            'customer_name': '',
            'address': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_405_on_wrong_method(self):
        response = self.client.put(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ---------------------------------------------------------------------------
# Dispatcher CRUD Tests
# ---------------------------------------------------------------------------

class OrderDispatcherCRUDTests(TestCase):
    """Verify dispatchers have full CRUD like managers."""

    def setUp(self):
        self.client = APIClient()
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.url = '/api/orders/'
        self.order = _create_order(
            customer_name='Disp Order',
            address='Disp Address',
        )
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.dispatcher))

    def test_dispatcher_retrieve(self):
        response = self.client.get(f'{self.url}{self.order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['customer_name'], 'Disp Order')

    def test_dispatcher_patch(self):
        response = self.client.patch(f'{self.url}{self.order.pk}/', {
            'customer_name': 'Disp Patched',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['customer_name'], 'Disp Patched')

    def test_dispatcher_delete(self):
        order = _create_order(customer_name='Disp Del', address='Del Addr')
        response = self.client.delete(f'{self.url}{order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_dispatcher_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# API Validation Tests
# ---------------------------------------------------------------------------

class OrderAPIValidationTests(TestCase):
    """Test API-level validation for all fields."""

    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/orders/'
        self.order = _create_order(
            customer_name='Val Order',
            address='Val Address',
        )

    def test_create_blank_customer_name(self):
        response = self.client.post(self.url, {
            'customer_name': '',
            'address': 'Some address',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_blank_address(self):
        response = self.client.post(self.url, {
            'customer_name': 'Name',
            'address': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_negative_cash_amount(self):
        response = self.client.post(self.url, {
            'customer_name': 'Name',
            'address': 'Addr',
            'cash_amount': '-50.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_required_fields(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_invalid_customer_name(self):
        response = self.client.patch(f'{self.url}{self.order.pk}/', {
            'customer_name': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_valid_all_statuses(self):
        for status_val in OrderStatus.values:
            response = self.client.post(self.url, {
                'customer_name': f'Customer {status_val}',
                'address': 'Address',
                'status': status_val,
            }, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_valid_all_priorities(self):
        for priority in OrderPriority.values:
            response = self.client.post(self.url, {
                'customer_name': f'Customer {priority}',
                'address': 'Address',
                'priority': priority,
            }, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Delete Business Rule Tests
# ---------------------------------------------------------------------------

class OrderDeleteTests(TestCase):
    """Test the business rule: only OPEN orders can be deleted."""

    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/orders/'

    def test_delete_open_order_succeeds(self):
        order = _create_order(status=OrderStatus.OPEN)
        response = self.client.delete(f'{self.url}{order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_assigned_order_fails(self):
        order = _create_order(status=OrderStatus.ASSIGNED)
        response = self.client.delete(f'{self.url}{order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_en_route_order_fails(self):
        order = _create_order(status=OrderStatus.EN_ROUTE)
        response = self.client.delete(f'{self.url}{order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_delivered_order_fails(self):
        order = _create_order(status=OrderStatus.DELIVERED)
        response = self.client.delete(f'{self.url}{order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_failed_order_fails(self):
        order = _create_order(status=OrderStatus.FAILED)
        response = self.client.delete(f'{self.url}{order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_cash_banked_order_fails(self):
        order = _create_order(status=OrderStatus.CASH_BANKED)
        response = self.client.delete(f'{self.url}{order.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_nonexistent_order_returns_404(self):
        response = self.client.delete(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Pagination Tests
# ---------------------------------------------------------------------------

class OrderPaginationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/orders/'
        for i in range(5):
            _create_order(customer_name=f'Customer {i}', address=f'Address {i}')

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

class OrderEdgeCaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/orders/'

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
            {'customer_name': 'Test'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_nonexistent(self):
        response = self.client.put(
            f'{self.url}99999/',
            {'customer_name': 'Test', 'address': 'Addr'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent(self):
        response = self.client.delete(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_not_allowed_on_detail(self):
        order = _create_order()
        response = self.client.post(f'{self.url}{order.pk}/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_order_with_zero_cash(self):
        response = self.client.post(self.url, {
            'customer_name': 'Zero Cash',
            'address': 'Addr',
            'cash_amount': '0.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_order_with_large_cash(self):
        response = self.client.post(self.url, {
            'customer_name': 'Large Cash',
            'address': 'Addr',
            'cash_amount': '999999.99',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Admin Tests
# ---------------------------------------------------------------------------

class OrderAdminTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = _create_user(
            role=RoleChoices.MANAGER,
            username='admin_test',
            email='admin_test@example.com',
        )
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()

    def test_admin_list_page(self):
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin/orders/order/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_changelist_page(self):
        self.client.force_login(self.admin_user)
        _create_order(customer_name='Admin Order', address='Admin Addr')
        response = self.client.get('/admin/orders/order/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
