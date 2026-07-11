from decimal import Decimal

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import RoleChoices, User
from apps.drivers.models import Driver, DriverStatus
from apps.orders.models import Order, OrderStatus
from apps.delivery_stops.models import DeliveryStop, StopStatus

from .models import DeliveryRun, RunStatus


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


_SENTINEL = object()


def _build_delivery_run(**kwargs):
    """Build a DeliveryRun instance without saving (for validation tests)."""
    driver = kwargs.pop('driver', _SENTINEL)
    if driver is _SENTINEL:
        driver = _create_driver()
    defaults = {
        'driver': driver,
        'status': RunStatus.DRAFT,
        'total_cash_collected': Decimal('0.00'),
    }
    defaults.update(kwargs)
    return DeliveryRun(**defaults)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class DeliveryRunModelTests(TestCase):
    def test_create_valid_delivery_run(self):
        driver = _create_driver()
        run = _create_delivery_run(driver=driver)
        self.assertEqual(run.driver, driver)
        self.assertEqual(run.status, RunStatus.DRAFT)
        self.assertEqual(run.total_cash_collected, Decimal('0.00'))
        self.assertIsNone(run.started_at)
        self.assertIsNone(run.completed_at)
        self.assertIsNone(run.cash_banked_at)
        self.assertEqual(run.cash_banked_location, '')
        self.assertIsNotNone(run.created_at)
        self.assertIsNotNone(run.updated_at)

    def test_delivery_run_str(self):
        driver = _create_driver(name='Ahmed Ali')
        run = _create_delivery_run(driver=driver)
        self.assertEqual(str(run), f'DeliveryRun #{run.pk} - Ahmed Ali (Draft)')

    def test_delivery_run_str_en_route(self):
        driver = _create_driver(name='Sara Hassan')
        run = _create_delivery_run(driver=driver, status=RunStatus.EN_ROUTE)
        self.assertEqual(str(run), f'DeliveryRun #{run.pk} - Sara Hassan (En Route)')

    def test_default_status_is_draft(self):
        run = _create_delivery_run()
        self.assertEqual(run.status, RunStatus.DRAFT)

    def test_default_cash_is_zero(self):
        run = _create_delivery_run()
        self.assertEqual(run.total_cash_collected, Decimal('0.00'))

    def test_missing_driver(self):
        run = _build_delivery_run(driver=None)
        with self.assertRaises(ValidationError):
            run.full_clean()

    def test_negative_cash_amount(self):
        run = _build_delivery_run(total_cash_collected=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            run.full_clean()

    def test_zero_cash_is_valid(self):
        run = _build_delivery_run(total_cash_collected=Decimal('0.00'))
        run.full_clean()

    def test_invalid_status(self):
        run = _build_delivery_run()
        run.status = 'INVALID_STATUS'
        with self.assertRaises(ValidationError):
            run.full_clean()

    def test_all_status_choices(self):
        for status_val in RunStatus.values:
            run = _build_delivery_run(status=status_val)
            run.full_clean()

    def test_save_calls_full_clean(self):
        run = _build_delivery_run(total_cash_collected=Decimal('-5.00'))
        with self.assertRaises(ValidationError):
            run.save()

    def test_stops_count_property(self):
        run = _create_delivery_run()
        self.assertEqual(run.stops_count, 0)

    def test_cash_banked_location_without_at_raises(self):
        run = _build_delivery_run(
            cash_banked_location='Cairo Branch',
            cash_banked_at=None,
        )
        with self.assertRaises(ValidationError):
            run.full_clean()

    def test_cash_banked_location_with_at_is_valid(self):
        from django.utils import timezone
        run = _build_delivery_run(
            cash_banked_location='Cairo Branch',
            cash_banked_at=timezone.now(),
        )
        run.full_clean()

    def test_delete_driver_with_runs_protected(self):
        driver = _create_driver()
        _create_delivery_run(driver=driver)
        with self.assertRaises(IntegrityError):
            driver.delete()

    def test_cascade_delete_user_with_driver_runs_protected(self):
        user = _create_user(role=RoleChoices.DRIVER)
        driver = _create_driver(user=user)
        _create_delivery_run(driver=driver)
        with self.assertRaises(ProtectedError):
            user.delete()


# ---------------------------------------------------------------------------
# Serializer Tests
# ---------------------------------------------------------------------------

class DeliveryRunSerializerTests(TestCase):
    def setUp(self):
        from .serializers import DeliveryRunSerializer
        self.driver = _create_driver()
        self.run = _create_delivery_run(driver=self.driver)
        self.serializer = DeliveryRunSerializer(self.run)

    def test_serializer_fields(self):
        data = self.serializer.data
        expected = {
            'id', 'driver', 'driver_name', 'status', 'total_cash_collected',
            'started_at', 'completed_at', 'cash_banked_at', 'cash_banked_location',
            'created_at', 'updated_at',
        }
        self.assertEqual(set(data.keys()), expected)

    def test_serializer_read_only_fields(self):
        meta = self.serializer.Meta
        self.assertIn('id', meta.read_only_fields)
        self.assertIn('created_at', meta.read_only_fields)
        self.assertIn('updated_at', meta.read_only_fields)

    def test_serializer_driver_name(self):
        self.assertEqual(self.serializer.data['driver_name'], self.driver.name)

    def test_serializer_driver_id(self):
        self.assertEqual(self.serializer.data['driver'], self.driver.pk)

    def test_serializer_invalid_cash_negative(self):
        from .serializers import DeliveryRunSerializer
        s = DeliveryRunSerializer(self.run, data={'total_cash_collected': '-50.00'}, partial=True)
        self.assertFalse(s.is_valid())
        self.assertIn('total_cash_collected', s.errors)

    def test_serializer_valid_update(self):
        from .serializers import DeliveryRunSerializer
        s = DeliveryRunSerializer(self.run, data={'total_cash_collected': '250.00'}, partial=True)
        self.assertTrue(s.is_valid())
        updated = s.save()
        self.assertEqual(updated.total_cash_collected, Decimal('250.00'))


# ---------------------------------------------------------------------------
# Permission Tests
# ---------------------------------------------------------------------------

class DeliveryRunPermissionTests(TestCase):
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

class DeliveryRunAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.driver_user = _create_user(role=RoleChoices.DRIVER)
        self.url = '/api/delivery-runs/'
        self.driver = _create_driver(user=self.driver_user, name='Alpha Driver', phone_number='+1111111111')
        self.run = _create_delivery_run(
            driver=self.driver,
            status=RunStatus.DRAFT,
            total_cash_collected=Decimal('150.00'),
        )

    def _auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(user))

    # -- Create --
    def test_create_run_as_manager(self):
        self._auth(self.manager)
        driver2 = _create_driver()
        response = self.client.post(self.url, {
            'driver': driver2.pk,
            'total_cash_collected': '0.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['driver'], driver2.pk)
        self.assertEqual(response.data['status'], RunStatus.DRAFT)

    def test_create_run_as_dispatcher(self):
        self._auth(self.dispatcher)
        driver2 = _create_driver()
        response = self.client.post(self.url, {
            'driver': driver2.pk,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_run_as_driver_forbidden(self):
        self._auth(self.driver_user)
        response = self.client.post(self.url, {
            'driver': self.driver.pk,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_run_unauthorized(self):
        response = self.client.post(self.url, {
            'driver': self.driver.pk,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_run_invalid_data(self):
        self._auth(self.manager)
        response = self.client.post(self.url, {
            'total_cash_collected': '-100.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- List --
    def test_list_runs_as_manager(self):
        self._auth(self.manager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_list_runs_as_dispatcher(self):
        self._auth(self.dispatcher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_runs_as_driver_forbidden(self):
        self._auth(self.driver_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_runs_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- Retrieve --
    def test_retrieve_run_as_manager(self):
        self._auth(self.manager)
        response = self.client.get(f'{self.url}{self.run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['driver_name'], 'Alpha Driver')

    def test_retrieve_run_not_found(self):
        self._auth(self.manager)
        response = self.client.get(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- Update (PUT) --
    def test_update_run_as_manager(self):
        self._auth(self.manager)
        response = self.client.put(f'{self.url}{self.run.pk}/', {
            'driver': self.driver.pk,
            'status': RunStatus.ASSIGNED,
            'total_cash_collected': '200.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.ASSIGNED)

    def test_update_run_as_dispatcher(self):
        self._auth(self.dispatcher)
        response = self.client.put(f'{self.url}{self.run.pk}/', {
            'driver': self.driver.pk,
            'status': RunStatus.DRAFT,
            'total_cash_collected': '0.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # -- Partial Update (PATCH) --
    def test_patch_run_status(self):
        self._auth(self.manager)
        response = self.client.patch(f'{self.url}{self.run.pk}/', {
            'status': RunStatus.ASSIGNED,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.ASSIGNED)

    def test_patch_run_cash(self):
        self._auth(self.manager)
        response = self.client.patch(f'{self.url}{self.run.pk}/', {
            'total_cash_collected': '500.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_cash_collected'], '500.00')

    def test_patch_run_invalid_cash(self):
        self._auth(self.manager)
        response = self.client.patch(f'{self.url}{self.run.pk}/', {
            'total_cash_collected': '-50.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- Delete --
    def test_delete_draft_run_as_manager(self):
        self._auth(self.manager)
        run = _create_delivery_run(driver=self.driver)
        response = self.client.delete(f'{self.url}{run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DeliveryRun.objects.filter(pk=run.pk).exists())

    def test_delete_draft_run_as_dispatcher(self):
        self._auth(self.dispatcher)
        run = _create_delivery_run(driver=self.driver)
        response = self.client.delete(f'{self.url}{run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_non_draft_run_forbidden(self):
        self._auth(self.manager)
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        response = self.client.delete(f'{self.url}{run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_run_as_driver_forbidden(self):
        self._auth(self.driver_user)
        response = self.client.delete(f'{self.url}{self.run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Filtering Tests
# ---------------------------------------------------------------------------

class DeliveryRunFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-runs/'
        self.driver1 = _create_driver(name='Driver One', phone_number='+1111111111')
        self.driver2 = _create_driver(name='Driver Two', phone_number='+2222222222')

        _create_delivery_run(driver=self.driver1, status=RunStatus.DRAFT)
        _create_delivery_run(driver=self.driver2, status=RunStatus.EN_ROUTE)
        _create_delivery_run(driver=self.driver1, status=RunStatus.COMPLETED)

    def test_filter_by_status_draft(self):
        response = self.client.get(self.url, {'status': 'DRAFT'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        drivers = [r['driver'] for r in response.data['results']]
        self.assertIn(self.driver1.pk, drivers)
        self.assertNotIn(self.driver2.pk, drivers)

    def test_filter_by_status_en_route(self):
        response = self.client.get(self.url, {'status': 'EN_ROUTE'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        drivers = [r['driver'] for r in response.data['results']]
        self.assertIn(self.driver2.pk, drivers)

    def test_filter_by_driver(self):
        response = self.client.get(self.url, {'driver': self.driver1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_combined_filter(self):
        response = self.client.get(self.url, {'status': 'DRAFT', 'driver': self.driver1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


# ---------------------------------------------------------------------------
# Search Tests
# ---------------------------------------------------------------------------

class DeliveryRunSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-runs/'

        self.d1 = _create_driver(name='Mohamed Ahmed', phone_number='+201234567890')
        self.d2 = _create_driver(name='Sara Hassan', phone_number='+201987654321')
        _create_delivery_run(driver=self.d1)
        _create_delivery_run(driver=self.d2)

    def test_search_by_driver_name(self):
        response = self.client.get(self.url, {'search': 'Mohamed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        driver_ids = [r['driver'] for r in response.data['results']]
        self.assertIn(self.d1.pk, driver_ids)
        self.assertNotIn(self.d2.pk, driver_ids)

    def test_search_by_driver_phone(self):
        response = self.client.get(self.url, {'search': '01987'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        driver_ids = [r['driver'] for r in response.data['results']]
        self.assertIn(self.d2.pk, driver_ids)
        self.assertNotIn(self.d1.pk, driver_ids)

    def test_search_no_results(self):
        response = self.client.get(self.url, {'search': 'ZZZZZZZ'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)


# ---------------------------------------------------------------------------
# Ordering Tests
# ---------------------------------------------------------------------------

class DeliveryRunOrderingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-runs/'
        self.driver = _create_driver()

        self.r1 = _create_delivery_run(
            driver=self.driver,
            total_cash_collected=Decimal('50.00'),
        )
        self.r2 = _create_delivery_run(
            driver=self.driver,
            total_cash_collected=Decimal('200.00'),
        )
        self.r3 = _create_delivery_run(
            driver=self.driver,
            total_cash_collected=Decimal('100.00'),
        )

    def test_order_by_created_at_ascending(self):
        response = self.client.get(self.url, {'ordering': 'created_at'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in response.data['results']]
        self.assertEqual(ids, [self.r1.pk, self.r2.pk, self.r3.pk])

    def test_order_by_created_at_descending(self):
        response = self.client.get(self.url, {'ordering': '-created_at'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in response.data['results']]
        self.assertEqual(ids, [self.r3.pk, self.r2.pk, self.r1.pk])

    def test_order_by_total_cash_ascending(self):
        response = self.client.get(self.url, {'ordering': 'total_cash_collected'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        amounts = [Decimal(r['total_cash_collected']) for r in response.data['results']]
        self.assertEqual(amounts, sorted(amounts))

    def test_order_by_total_cash_descending(self):
        response = self.client.get(self.url, {'ordering': '-total_cash_collected'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        amounts = [Decimal(r['total_cash_collected']) for r in response.data['results']]
        self.assertEqual(amounts, sorted(amounts, reverse=True))

    def test_order_by_started_at(self):
        from django.utils import timezone
        self.r1.started_at = timezone.now()
        self.r1.save()
        self.r2.started_at = timezone.now()
        self.r2.save()
        response = self.client.get(self.url, {'ordering': 'started_at'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_default_ordering_by_created_at_desc(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in response.data['results']]
        self.assertEqual(ids[0], self.r3.pk)

    def test_invalid_ordering_field_ignored(self):
        response = self.client.get(self.url, {'ordering': 'nonexistent'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------

class DeliveryRunAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/delivery-runs/'
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

class DeliveryRunStatusCodesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-runs/'
        self.driver = _create_driver()
        self.run = _create_delivery_run(driver=self.driver)

    def test_200_on_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_201_on_create(self):
        driver2 = _create_driver()
        response = self.client.post(self.url, {
            'driver': driver2.pk,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_204_on_delete(self):
        run = _create_delivery_run(driver=self.driver)
        response = self.client.delete(f'{self.url}{run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_404_on_nonexistent(self):
        response = self.client.get(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_400_on_invalid_data(self):
        response = self.client.post(self.url, {
            'total_cash_collected': '-50.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_405_on_wrong_method(self):
        response = self.client.put(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ---------------------------------------------------------------------------
# Dispatcher CRUD Tests
# ---------------------------------------------------------------------------

class DeliveryRunDispatcherCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.driver = _create_driver()
        self.url = '/api/delivery-runs/'
        self.run = _create_delivery_run(driver=self.driver)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.dispatcher))

    def test_dispatcher_retrieve(self):
        response = self.client.get(f'{self.url}{self.run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dispatcher_patch(self):
        response = self.client.patch(f'{self.url}{self.run.pk}/', {
            'status': RunStatus.ASSIGNED,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.ASSIGNED)

    def test_dispatcher_delete(self):
        run = _create_delivery_run(driver=self.driver)
        response = self.client.delete(f'{self.url}{run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_dispatcher_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Delete Business Rule Tests
# ---------------------------------------------------------------------------

class DeliveryRunDeleteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-runs/'
        self.driver = _create_driver()

    def test_delete_draft_succeeds(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.DRAFT)
        response = self.client.delete(f'{self.url}{run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_assigned_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.ASSIGNED)
        response = self.client.delete(f'{self.url}{run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_en_route_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        response = self.client.delete(f'{self.url}{run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_completed_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.COMPLETED)
        response = self.client.delete(f'{self.url}{run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_cash_banked_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.CASH_BANKED)
        response = self.client.delete(f'{self.url}{run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_cancelled_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.CANCELLED)
        response = self.client.delete(f'{self.url}{run.pk}/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_nonexistent_returns_404(self):
        response = self.client.delete(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Pagination Tests
# ---------------------------------------------------------------------------

class DeliveryRunPaginationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-runs/'
        self.driver = _create_driver()
        for _ in range(5):
            _create_delivery_run(driver=self.driver)

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

class DeliveryRunEdgeCaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/delivery-runs/'

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
            {'status': 'DRAFT'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent(self):
        response = self.client.delete(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_not_allowed_on_detail(self):
        driver = _create_driver()
        run = _create_delivery_run(driver=driver)
        response = self.client.post(f'{self.url}{run.pk}/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_with_nonexistent_driver(self):
        response = self.client.post(self.url, {
            'driver': 99999,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_zero_cash(self):
        driver = _create_driver()
        response = self.client.post(self.url, {
            'driver': driver.pk,
            'total_cash_collected': '0.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_with_large_cash(self):
        driver = _create_driver()
        response = self.client.post(self.url, {
            'driver': driver.pk,
            'total_cash_collected': '999999.99',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Admin Tests
# ---------------------------------------------------------------------------

class DeliveryRunAdminTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = _create_user(
            role=RoleChoices.MANAGER,
            username='admin_dr_test',
            email='admin_dr_test@example.com',
        )
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()

    def test_admin_list_page(self):
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin/delivery_runs/deliveryrun/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_changelist_page(self):
        self.client.force_login(self.admin_user)
        driver = _create_driver()
        _create_delivery_run(driver=driver)
        response = self.client.get('/admin/delivery_runs/deliveryrun/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Workflow Action Tests
# ---------------------------------------------------------------------------

def _create_order(**kwargs):
    defaults = {
        'customer_name': 'Test Customer',
        'customer_phone': '+201234567890',
        'address': '15 El Tahrir St, Cairo',
        'cash_amount': Decimal('100.00'),
    }
    defaults.update(kwargs)
    return Order.objects.create(**defaults)


class BuildRunActionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.driver_user = _create_user(role=RoleChoices.DRIVER)
        self.driver = _create_driver(user=self.driver_user, name='Build Driver', phone_number='+1111111111')
        self.url = '/api/delivery-runs/'
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))

    def test_build_run_basic(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.DRAFT)
        o1 = _create_order(customer_name='Cust 1', cash_amount=Decimal('50.00'))
        o2 = _create_order(customer_name='Cust 2', cash_amount=Decimal('75.00'))
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk, o2.pk],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.ASSIGNED)
        self.driver.refresh_from_db()
        self.assertEqual(self.driver.status, DriverStatus.AVAILABLE)
        o1.refresh_from_db()
        o2.refresh_from_db()
        self.assertEqual(o1.status, OrderStatus.ASSIGNED)
        self.assertEqual(o2.status, OrderStatus.ASSIGNED)
        self.assertEqual(o1.assigned_driver, self.driver)
        self.assertEqual(o2.assigned_driver, self.driver)
        self.assertEqual(run.stops.count(), 2)
        stop1 = run.stops.first()
        self.assertEqual(stop1.customer_name, 'Cust 1')
        self.assertEqual(stop1.cash_amount, Decimal('50.00'))
        self.assertEqual(stop1.stop_sequence, 1)

    def test_build_run_as_dispatcher(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.dispatcher))
        run = _create_delivery_run(driver=self.driver, status=RunStatus.DRAFT)
        o1 = _create_order()
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_build_run_as_driver_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.driver_user))
        run = _create_delivery_run(driver=self.driver, status=RunStatus.DRAFT)
        o1 = _create_order()
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_build_run_unauthorized(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.DRAFT)
        o1 = _create_order()
        self.client.credentials()
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_build_run_not_draft_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        o1 = _create_order()
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_build_run_missing_order_ids(self):
        run = _create_delivery_run(driver=self.driver)
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_build_run_empty_order_ids(self):
        run = _create_delivery_run(driver=self.driver)
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_build_run_nonexistent_order(self):
        run = _create_delivery_run(driver=self.driver)
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [99999],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_build_run_order_not_open(self):
        run = _create_delivery_run(driver=self.driver)
        o1 = _create_order()
        o1.status = OrderStatus.DELIVERED
        o1.save()
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('99999' if o1.pk is None else str(o1.pk), str(response.data))

    def test_build_run_exceeds_max_stops(self):
        driver2 = _create_driver(max_stops_per_run=2)
        run = _create_delivery_run(driver=driver2)
        o1 = _create_order(customer_name='O1', address='A1')
        o2 = _create_order(customer_name='O2', address='A2')
        o3 = _create_order(customer_name='O3', address='A3')
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk, o2.pk, o3.pk],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('exceed', str(response.data).lower())

    def test_build_run_inactive_driver(self):
        driver2 = _create_driver(active=False)
        run = _create_delivery_run(driver=driver2)
        o1 = _create_order()
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_build_run_on_run_driver(self):
        driver2 = _create_driver(status=DriverStatus.ON_RUN)
        run = _create_delivery_run(driver=driver2)
        o1 = _create_order()
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_build_run_transitions_to_assigned(self):
        driver2 = _create_driver(max_stops_per_run=3)
        run = _create_delivery_run(driver=driver2)
        o1 = _create_order(customer_name='O1', address='A1')
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.ASSIGNED)
        run.refresh_from_db()
        self.assertEqual(run.status, RunStatus.ASSIGNED)

    def test_build_run_cannot_build_twice(self):
        driver2 = _create_driver(max_stops_per_run=3)
        run = _create_delivery_run(driver=driver2)
        o1 = _create_order(customer_name='O1', address='A1')
        o2 = _create_order(customer_name='O2', address='A2')
        self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk],
        }, format='json')
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o2.pk],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_build_run_sets_stop_sequence_correctly(self):
        driver2 = _create_driver(max_stops_per_run=5)
        run = _create_delivery_run(driver=driver2)
        o1 = _create_order(customer_name='O1', address='A1')
        o2 = _create_order(customer_name='O2', address='A2')
        o3 = _create_order(customer_name='O3', address='A3')
        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk, o2.pk, o3.pk],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sequences = list(run.stops.values_list('stop_sequence', flat=True))
        self.assertEqual(sorted(sequences), [1, 2, 3])


class StartRunActionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.driver_user = _create_user(role=RoleChoices.DRIVER)
        self.driver = _create_driver(user=self.driver_user, name='Start Driver')
        self.url = '/api/delivery-runs/'
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))

    def test_start_run_basic(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.ASSIGNED)
        o1 = _create_order(customer_name='C1', cash_amount=Decimal('50.00'))
        o2 = _create_order(customer_name='C2', cash_amount=Decimal('75.00'))
        from apps.delivery_stops.models import DeliveryStop
        DeliveryStop.objects.create(
            delivery_run=run, order=o1, stop_sequence=1,
            customer_name='C1', address='A1', cash_amount=Decimal('50.00'),
        )
        DeliveryStop.objects.create(
            delivery_run=run, order=o2, stop_sequence=2,
            customer_name='C2', address='A2', cash_amount=Decimal('75.00'),
        )
        response = self.client.post(f'{self.url}{run.pk}/start-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.EN_ROUTE)
        self.assertIsNotNone(response.data['started_at'])
        self.driver.refresh_from_db()
        self.assertEqual(self.driver.status, DriverStatus.ON_RUN)
        o1.refresh_from_db()
        o2.refresh_from_db()
        self.assertEqual(o1.status, OrderStatus.EN_ROUTE)
        self.assertEqual(o2.status, OrderStatus.EN_ROUTE)
        self.assertTrue(all(s['status'] == StopStatus.EN_ROUTE for s in run.stops.all().values('status')))

    def test_start_run_as_dispatcher(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(
            _create_user(role=RoleChoices.DISPATCHER)
        ))
        run = _create_delivery_run(driver=self.driver, status=RunStatus.ASSIGNED)
        o1 = _create_order()
        DeliveryStop.objects.create(
            delivery_run=run, order=o1, stop_sequence=1,
            customer_name='C1', address='A1', cash_amount=Decimal('0.00'),
        )
        response = self.client.post(f'{self.url}{run.pk}/start-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_start_run_not_assigned_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.DRAFT)
        response = self.client.post(f'{self.url}{run.pk}/start-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_run_already_en_route_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        response = self.client.post(f'{self.url}{run.pk}/start-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_run_completed_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.COMPLETED)
        response = self.client.post(f'{self.url}{run.pk}/start-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_run_no_stops_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.ASSIGNED)
        response = self.client.post(f'{self.url}{run.pk}/start-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_run_as_driver_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.driver_user))
        run = _create_delivery_run(driver=self.driver, status=RunStatus.ASSIGNED)
        response = self.client.post(f'{self.url}{run.pk}/start-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_start_run_unauthorized(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.ASSIGNED)
        self.client.credentials()
        response = self.client.post(f'{self.url}{run.pk}/start-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CompleteRunActionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.driver_user = _create_user(role=RoleChoices.DRIVER)
        self.driver = _create_driver(user=self.driver_user, name='Complete Driver')
        self.url = '/api/delivery-runs/'
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))

    def _build_en_route_run(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        o1 = _create_order(customer_name='C1', cash_amount=Decimal('50.00'))
        o2 = _create_order(customer_name='C2', cash_amount=Decimal('75.00'))
        DeliveryStop.objects.create(
            delivery_run=run, order=o1, stop_sequence=1,
            customer_name='C1', address='A1', cash_amount=Decimal('50.00'),
            status=StopStatus.DELIVERED,
        )
        DeliveryStop.objects.create(
            delivery_run=run, order=o2, stop_sequence=2,
            customer_name='C2', address='A2', cash_amount=Decimal('75.00'),
            status=StopStatus.DELIVERED,
        )
        return run, o1, o2

    def test_complete_run_basic(self):
        run, o1, o2 = self._build_en_route_run()
        response = self.client.post(f'{self.url}{run.pk}/complete-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.COMPLETED)
        self.assertIsNotNone(response.data['completed_at'])
        self.driver.refresh_from_db()
        self.assertEqual(self.driver.status, DriverStatus.AVAILABLE)

    def test_complete_run_with_failed_stop(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        o1 = _create_order(customer_name='C1', cash_amount=Decimal('50.00'))
        o2 = _create_order(customer_name='C2', cash_amount=Decimal('75.00'))
        DeliveryStop.objects.create(
            delivery_run=run, order=o1, stop_sequence=1,
            customer_name='C1', address='A1', cash_amount=Decimal('50.00'),
            status=StopStatus.DELIVERED,
        )
        DeliveryStop.objects.create(
            delivery_run=run, order=o2, stop_sequence=2,
            customer_name='C2', address='A2', cash_amount=Decimal('75.00'),
            status=StopStatus.FAILED, failed_reason='Customer not home',
        )
        response = self.client.post(f'{self.url}{run.pk}/complete-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.COMPLETED)

    def test_complete_run_not_en_route_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.ASSIGNED)
        response = self.client.post(f'{self.url}{run.pk}/complete-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_complete_run_draft_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.DRAFT)
        response = self.client.post(f'{self.url}{run.pk}/complete-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_complete_run_completed_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.COMPLETED)
        response = self.client.post(f'{self.url}{run.pk}/complete-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_complete_run_unfinished_stops_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        o1 = _create_order(customer_name='C1')
        DeliveryStop.objects.create(
            delivery_run=run, order=o1, stop_sequence=1,
            customer_name='C1', address='A1', cash_amount=Decimal('0.00'),
            status=StopStatus.EN_ROUTE,
        )
        response = self.client.post(f'{self.url}{run.pk}/complete-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Remaining stops', str(response.data))

    def test_complete_run_mixed_delivered_failed(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        o1 = _create_order(customer_name='C1')
        o2 = _create_order(customer_name='C2')
        o3 = _create_order(customer_name='C3')
        DeliveryStop.objects.create(
            delivery_run=run, order=o1, stop_sequence=1,
            customer_name='C1', address='A1', cash_amount=Decimal('0.00'),
            status=StopStatus.DELIVERED,
        )
        DeliveryStop.objects.create(
            delivery_run=run, order=o2, stop_sequence=2,
            customer_name='C2', address='A2', cash_amount=Decimal('0.00'),
            status=StopStatus.FAILED, failed_reason='Wrong address',
        )
        DeliveryStop.objects.create(
            delivery_run=run, order=o3, stop_sequence=3,
            customer_name='C3', address='A3', cash_amount=Decimal('0.00'),
            status=StopStatus.ASSIGNED,
        )
        response = self.client.post(f'{self.url}{run.pk}/complete-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_complete_run_as_driver_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.driver_user))
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        response = self.client.post(f'{self.url}{run.pk}/complete-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_complete_run_unauthorized(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        self.client.credentials()
        response = self.client.post(f'{self.url}{run.pk}/complete-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BankCashActionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.driver_user = _create_user(role=RoleChoices.DRIVER)
        self.driver = _create_driver(user=self.driver_user, name='Bank Driver')
        self.url = '/api/delivery-runs/'
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))

    def test_bank_cash_basic(self):
        run = _create_delivery_run(
            driver=self.driver, status=RunStatus.COMPLETED,
            total_cash_collected=Decimal('150.00'),
        )
        o1 = _create_order(customer_name='C1', cash_amount=Decimal('150.00'))
        o1.status = OrderStatus.DELIVERED
        o1.save()
        DeliveryStop.objects.create(
            delivery_run=run, order=o1, stop_sequence=1,
            customer_name='C1', address='A1', cash_amount=Decimal('150.00'),
            status=StopStatus.DELIVERED,
        )
        response = self.client.post(f'{self.url}{run.pk}/bank-cash/', {
            'cash_banked_location': 'Cairo Main Branch',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.CASH_BANKED)
        self.assertIsNotNone(response.data['cash_banked_at'])
        self.assertEqual(response.data['cash_banked_location'], 'Cairo Main Branch')
        o1.refresh_from_db()
        self.assertEqual(o1.status, OrderStatus.CASH_BANKED)

    def test_bank_cash_as_dispatcher(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.dispatcher))
        run = _create_delivery_run(
            driver=self.driver, status=RunStatus.COMPLETED,
            total_cash_collected=Decimal('100.00'),
        )
        response = self.client.post(f'{self.url}{run.pk}/bank-cash/', {
            'cash_banked_location': 'Branch A',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bank_cash_not_completed_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.EN_ROUTE)
        response = self.client.post(f'{self.url}{run.pk}/bank-cash/', {
            'cash_banked_location': 'Branch A',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bank_cash_draft_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.DRAFT)
        response = self.client.post(f'{self.url}{run.pk}/bank-cash/', {
            'cash_banked_location': 'Branch A',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bank_cash_assigend_fails(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.ASSIGNED)
        response = self.client.post(f'{self.url}{run.pk}/bank-cash/', {
            'cash_banked_location': 'Branch A',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bank_cash_missing_location(self):
        run = _create_delivery_run(
            driver=self.driver, status=RunStatus.COMPLETED,
            total_cash_collected=Decimal('0.00'),
        )
        response = self.client.post(f'{self.url}{run.pk}/bank-cash/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bank_cash_empty_location(self):
        run = _create_delivery_run(
            driver=self.driver, status=RunStatus.COMPLETED,
            total_cash_collected=Decimal('0.00'),
        )
        response = self.client.post(f'{self.url}{run.pk}/bank-cash/', {
            'cash_banked_location': '   ',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bank_cash_as_driver_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.driver_user))
        run = _create_delivery_run(
            driver=self.driver, status=RunStatus.COMPLETED,
            total_cash_collected=Decimal('0.00'),
        )
        response = self.client.post(f'{self.url}{run.pk}/bank-cash/', {
            'cash_banked_location': 'Branch A',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bank_cash_unauthorized(self):
        run = _create_delivery_run(
            driver=self.driver, status=RunStatus.COMPLETED,
            total_cash_collected=Decimal('0.00'),
        )
        self.client.credentials()
        response = self.client.post(f'{self.url}{run.pk}/bank-cash/', {
            'cash_banked_location': 'Branch A',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bank_cash_only_delivered_orders_became_cash_banked(self):
        run = _create_delivery_run(
            driver=self.driver, status=RunStatus.COMPLETED,
            total_cash_collected=Decimal('100.00'),
        )
        o_delivered = _create_order(customer_name='Delivered', cash_amount=Decimal('100.00'))
        o_delivered.status = OrderStatus.DELIVERED
        o_delivered.save()
        o_failed = _create_order(customer_name='Failed', cash_amount=Decimal('50.00'))
        o_failed.status = OrderStatus.FAILED
        o_failed.save()
        DeliveryStop.objects.create(
            delivery_run=run, order=o_delivered, stop_sequence=1,
            customer_name='Delivered', address='A1', cash_amount=Decimal('100.00'),
            status=StopStatus.DELIVERED,
        )
        DeliveryStop.objects.create(
            delivery_run=run, order=o_failed, stop_sequence=2,
            customer_name='Failed', address='A2', cash_amount=Decimal('50.00'),
            status=StopStatus.FAILED,
        )
        response = self.client.post(f'{self.url}{run.pk}/bank-cash/', {
            'cash_banked_location': 'Main Branch',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        o_delivered.refresh_from_db()
        o_failed.refresh_from_db()
        self.assertEqual(o_delivered.status, OrderStatus.CASH_BANKED)
        self.assertEqual(o_failed.status, OrderStatus.FAILED)


class FullWorkflowIntegrationTests(TestCase):
    """End-to-end test of the entire delivery workflow lifecycle."""

    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.driver_user = _create_user(role=RoleChoices.DRIVER)
        self.driver = _create_driver(
            user=self.driver_user, name='Integration Driver',
            max_stops_per_run=5,
        )
        self.url = '/api/delivery-runs/'
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))

    def test_full_happy_path_workflow(self):
        o1 = _create_order(customer_name='Alice', cash_amount=Decimal('100.00'))
        o2 = _create_order(customer_name='Bob', cash_amount=Decimal('200.00'))
        o3 = _create_order(customer_name='Charlie', cash_amount=Decimal('150.00'))

        run = _create_delivery_run(driver=self.driver, status=RunStatus.DRAFT)

        response = self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk, o2.pk, o3.pk],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.ASSIGNED)
        self.assertEqual(run.stops.count(), 3)

        response = self.client.post(f'{self.url}{run.pk}/start-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.EN_ROUTE)
        self.driver.refresh_from_db()
        self.assertEqual(self.driver.status, DriverStatus.ON_RUN)

        stops_url = '/api/delivery-stops/'
        stop_o1 = run.stops.get(order=o1)
        stop_o2 = run.stops.get(order=o2)
        stop_o3 = run.stops.get(order=o3)

        response = self.client.post(f'{stops_url}{stop_o1.pk}/mark-delivered/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        run.refresh_from_db()
        self.assertEqual(run.total_cash_collected, Decimal('100.00'))

        response = self.client.post(f'{stops_url}{stop_o2.pk}/mark-failed/', {
            'failed_reason': 'Customer not available',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        run.refresh_from_db()
        self.assertEqual(run.total_cash_collected, Decimal('100.00'))

        response = self.client.post(f'{stops_url}{stop_o3.pk}/mark-delivered/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        run.refresh_from_db()
        self.assertEqual(run.total_cash_collected, Decimal('250.00'))

        response = self.client.post(f'{self.url}{run.pk}/complete-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.COMPLETED)
        self.driver.refresh_from_db()
        self.assertEqual(self.driver.status, DriverStatus.AVAILABLE)

        response = self.client.post(f'{self.url}{run.pk}/bank-cash/', {
            'cash_banked_location': 'Cairo HQ',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.CASH_BANKED)
        self.assertEqual(response.data['cash_banked_location'], 'Cairo HQ')

        o1.refresh_from_db()
        o2.refresh_from_db()
        o3.refresh_from_db()
        self.assertEqual(o1.status, OrderStatus.CASH_BANKED)
        self.assertEqual(o2.status, OrderStatus.FAILED)
        self.assertEqual(o3.status, OrderStatus.CASH_BANKED)

    def test_full_workflow_with_all_failed_stops(self):
        o1 = _create_order(customer_name='Fail 1', cash_amount=Decimal('50.00'))
        o2 = _create_order(customer_name='Fail 2', cash_amount=Decimal('75.00'))
        run = _create_delivery_run(driver=self.driver, status=RunStatus.DRAFT)

        self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk, o2.pk],
        }, format='json')

        self.client.post(f'{self.url}{run.pk}/start-run/', format='json')

        stops_url = '/api/delivery-stops/'
        stops = list(run.stops.all())

        self.client.post(f'{stops_url}{stops[0].pk}/mark-failed/', {
            'failed_reason': 'Address not found',
        }, format='json')
        self.client.post(f'{stops_url}{stops[1].pk}/mark-failed/', {
            'failed_reason': 'Customer refused',
        }, format='json')

        response = self.client.post(f'{self.url}{run.pk}/complete-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.COMPLETED)

        response = self.client.post(f'{self.url}{run.pk}/bank-cash/', {
            'cash_banked_location': 'Main Office',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RunStatus.CASH_BANKED)
        run.refresh_from_db()
        self.assertEqual(run.total_cash_collected, Decimal('0.00'))

    def test_cannot_start_run_twice(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.DRAFT)
        o1 = _create_order()
        self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk],
        }, format='json')
        self.client.post(f'{self.url}{run.pk}/start-run/', format='json')
        response = self.client.post(f'{self.url}{run.pk}/start-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_complete_run_twice(self):
        run = _create_delivery_run(driver=self.driver, status=RunStatus.DRAFT)
        o1 = _create_order()
        self.client.post(f'{self.url}{run.pk}/build-run/', {
            'order_ids': [o1.pk],
        }, format='json')
        self.client.post(f'{self.url}{run.pk}/start-run/', format='json')
        stop = run.stops.first()
        self.client.post(f'/api/delivery-stops/{stop.pk}/mark-delivered/', format='json')
        self.client.post(f'{self.url}{run.pk}/complete-run/', format='json')
        response = self.client.post(f'{self.url}{run.pk}/complete-run/', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
