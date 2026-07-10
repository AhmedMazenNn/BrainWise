from django.test import TestCase
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import RoleChoices, User

from .models import Driver, DriverStatus


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


def _build_driver(**kwargs):
    """Build a Driver instance without saving (for validation tests)."""
    user = kwargs.pop('user', None)
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
    return Driver(**defaults)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class DriverModelTests(TestCase):
    def setUp(self):
        self.user = _create_user(role=RoleChoices.DRIVER)

    def test_create_valid_driver(self):
        driver = _create_driver(user=self.user)
        self.assertEqual(driver.name, 'Test Driver')
        self.assertEqual(driver.phone_number, '+1234567890')
        self.assertTrue(driver.active)
        self.assertEqual(driver.max_stops_per_run, 5)
        self.assertEqual(driver.status, DriverStatus.AVAILABLE)
        self.assertIsNotNone(driver.created_at)
        self.assertIsNotNone(driver.updated_at)

    def test_driver_str(self):
        driver = _create_driver(user=self.user)
        self.assertEqual(str(driver), 'Test Driver (Available)')

    def test_driver_str_on_run(self):
        driver = _create_driver(user=self.user, status=DriverStatus.ON_RUN)
        self.assertEqual(str(driver), 'Test Driver (On Run)')

    def test_invalid_phone_number_blank(self):
        driver = _build_driver(user=self.user, phone_number='')
        with self.assertRaises(ValidationError):
            driver.full_clean()

    def test_invalid_phone_number_too_short(self):
        driver = _build_driver(user=self.user, phone_number='123')
        with self.assertRaises(ValidationError):
            driver.full_clean()

    def test_valid_phone_formats(self):
        formats = ['+1234567890', '+1 (234) 567-890', '+44 20 7946 0958', '01234567890']
        for fmt in formats:
            user = _create_user(role=RoleChoices.DRIVER)
            driver = _build_driver(user=user, phone_number=fmt)
            driver.full_clean()

    def test_invalid_max_stops_zero(self):
        driver = _build_driver(user=self.user, max_stops_per_run=0)
        with self.assertRaises(ValidationError):
            driver.full_clean()

    def test_invalid_max_stops_negative(self):
        driver = _build_driver(user=self.user, max_stops_per_run=-1)
        with self.assertRaises(ValidationError):
            driver.full_clean()

    def test_max_stops_one_is_valid(self):
        driver = _build_driver(user=self.user, max_stops_per_run=1)
        driver.full_clean()

    def test_inactive_on_run_raises(self):
        driver = _build_driver(user=self.user, active=False, status=DriverStatus.ON_RUN)
        with self.assertRaises(ValidationError):
            driver.full_clean()

    def test_inactive_available_is_valid(self):
        driver = _build_driver(user=self.user, active=False, status=DriverStatus.AVAILABLE)
        driver.full_clean()

    def test_inactive_inactive_is_valid(self):
        driver = _build_driver(user=self.user, active=False, status=DriverStatus.INACTIVE)
        driver.full_clean()

    def test_status_must_be_valid_choice(self):
        driver = _build_driver(user=self.user)
        driver.status = 'INVALID_STATUS'
        with self.assertRaises(ValidationError):
            driver.full_clean()

    def test_default_status_is_available(self):
        driver = Driver.objects.create(user=self.user, name='Def', phone_number='+1234567890')
        self.assertEqual(driver.status, DriverStatus.AVAILABLE)

    def test_default_active_is_true(self):
        driver = Driver.objects.create(user=self.user, name='Def', phone_number='+1234567890')
        self.assertTrue(driver.active)

    def test_default_max_stops_is_one(self):
        driver = Driver.objects.create(user=self.user, name='Def', phone_number='+1234567890')
        self.assertEqual(driver.max_stops_per_run, 1)

    def test_user_one_to_one(self):
        _create_driver(user=self.user)
        user2 = _create_user(role=RoleChoices.DRIVER)
        with self.assertRaises(Exception):
            Driver.objects.create(user=user2, name='Dup', phone_number='+1111111111')
            Driver.objects.create(user=self.user, name='Dup2', phone_number='+2222222222')

    def test_cascade_delete(self):
        driver = _create_driver(user=self.user)
        driver_id = driver.pk
        self.user.delete()
        self.assertFalse(Driver.objects.filter(pk=driver_id).exists())

    def test_save_calls_full_clean(self):
        driver = _build_driver(user=self.user, phone_number='bad')
        with self.assertRaises(ValidationError):
            driver.save()


# ---------------------------------------------------------------------------
# Serializer Tests
# ---------------------------------------------------------------------------

class DriverSerializerTests(TestCase):
    def setUp(self):
        from .serializers import DriverSerializer
        self.user = _create_user(role=RoleChoices.DRIVER)
        self.driver = _create_driver(user=self.user)
        self.serializer = DriverSerializer(self.driver)

    def test_serializer_fields(self):
        data = self.serializer.data
        expected = {'id', 'user', 'name', 'phone_number', 'active', 'max_stops_per_run', 'status', 'created_at', 'updated_at'}
        self.assertEqual(set(data.keys()), expected)

    def test_serializer_read_only_fields(self):
        meta = self.serializer.Meta
        self.assertIn('id', meta.read_only_fields)
        self.assertIn('created_at', meta.read_only_fields)
        self.assertIn('updated_at', meta.read_only_fields)

    def test_serializer_invalid_phone_blank(self):
        from .serializers import DriverSerializer
        s = DriverSerializer(self.driver, data={'phone_number': ''}, partial=True)
        self.assertFalse(s.is_valid())
        self.assertIn('phone_number', s.errors)

    def test_serializer_invalid_max_stops(self):
        from .serializers import DriverSerializer
        s = DriverSerializer(self.driver, data={'max_stops_per_run': 0}, partial=True)
        self.assertFalse(s.is_valid())
        self.assertIn('max_stops_per_run', s.errors)

    def test_serializer_inactive_on_run(self):
        from .serializers import DriverSerializer
        s = DriverSerializer(self.driver, data={'active': False, 'status': DriverStatus.ON_RUN}, partial=True)
        self.assertFalse(s.is_valid())
        self.assertIn('status', s.errors)

    def test_serializer_invalid_status(self):
        from .serializers import DriverSerializer
        s = DriverSerializer(self.driver, data={'status': 'BANANA'}, partial=True)
        self.assertFalse(s.is_valid())
        self.assertIn('status', s.errors)

    def test_serializer_valid_update(self):
        from .serializers import DriverSerializer
        s = DriverSerializer(self.driver, data={'name': 'Updated Name'}, partial=True)
        self.assertTrue(s.is_valid())
        updated = s.save()
        self.assertEqual(updated.name, 'Updated Name')


# ---------------------------------------------------------------------------
# Permission Tests
# ---------------------------------------------------------------------------

class DriverPermissionTests(TestCase):
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

class DriverAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.driver_user = _create_user(role=RoleChoices.DRIVER)
        self.url = '/api/drivers/'
        self.driver = _create_driver(user=self.driver_user, name='Alpha Driver', phone_number='+1111111111')

    def _auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(user))

    # -- Create --
    def test_create_driver_as_manager(self):
        self._auth(self.manager)
        user2 = _create_user(role=RoleChoices.DRIVER)
        response = self.client.post(self.url, {
            'user': user2.pk,
            'name': 'New Driver',
            'phone_number': '+2222222222',
            'active': True,
            'max_stops_per_run': 3,
            'status': DriverStatus.AVAILABLE,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Driver')

    def test_create_driver_as_dispatcher(self):
        self._auth(self.dispatcher)
        user2 = _create_user(role=RoleChoices.DRIVER)
        response = self.client.post(self.url, {
            'user': user2.pk,
            'name': 'Dispatcher Created',
            'phone_number': '+3333333333',
            'active': True,
            'max_stops_per_run': 4,
            'status': DriverStatus.AVAILABLE,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_driver_as_driver_forbidden(self):
        self._auth(self.driver_user)
        user2 = _create_user(role=RoleChoices.DRIVER)
        response = self.client.post(self.url, {
            'user': user2.pk,
            'name': 'Nope',
            'phone_number': '+4444444444',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_driver_unauthorized(self):
        response = self.client.post(self.url, {
            'name': 'Unauth',
            'phone_number': '+5555555555',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_driver_invalid_data(self):
        self._auth(self.manager)
        user2 = _create_user(role=RoleChoices.DRIVER)
        response = self.client.post(self.url, {
            'user': user2.pk,
            'name': '',
            'phone_number': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- List --
    def test_list_drivers_as_manager(self):
        self._auth(self.manager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_list_drivers_as_dispatcher(self):
        self._auth(self.dispatcher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_drivers_as_driver_forbidden(self):
        self._auth(self.driver_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_drivers_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- Retrieve --
    def test_retrieve_driver_as_manager(self):
        self._auth(self.manager)
        response = self.client.get(f'{self.url}{self.driver.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Alpha Driver')

    def test_retrieve_driver_not_found(self):
        self._auth(self.manager)
        response = self.client.get(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- Update (PUT) --
    def test_update_driver_as_manager(self):
        self._auth(self.manager)
        response = self.client.put(f'{self.url}{self.driver.pk}/', {
            'user': self.driver_user.pk,
            'name': 'Updated Driver',
            'phone_number': '+9999999999',
            'active': True,
            'max_stops_per_run': 10,
            'status': DriverStatus.AVAILABLE,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Driver')

    def test_update_driver_as_dispatcher(self):
        self._auth(self.dispatcher)
        response = self.client.put(f'{self.url}{self.driver.pk}/', {
            'user': self.driver_user.pk,
            'name': 'Disp Update',
            'phone_number': '+8888888888',
            'active': True,
            'max_stops_per_run': 2,
            'status': DriverStatus.AVAILABLE,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # -- Partial Update (PATCH) --
    def test_patch_driver_as_manager(self):
        self._auth(self.manager)
        response = self.client.patch(f'{self.url}{self.driver.pk}/', {
            'name': 'Patched Name',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Patched Name')

    # -- Delete --
    def test_delete_driver_as_manager(self):
        self._auth(self.manager)
        user_del = _create_user(role=RoleChoices.DRIVER)
        driver_del = _create_driver(user=user_del, name='Del Driver', phone_number='+7777777777')
        response = self.client.delete(f'{self.url}{driver_del.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Driver.objects.filter(pk=driver_del.pk).exists())

    def test_delete_driver_as_driver_forbidden(self):
        self._auth(self.driver_user)
        response = self.client.delete(f'{self.url}{self.driver.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # -- Available endpoint --
    def test_available_drivers(self):
        self._auth(self.manager)
        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Available One',
            phone_number='+1000000001',
            active=True,
            status=DriverStatus.AVAILABLE,
        )
        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Inactive One',
            phone_number='+1000000002',
            active=False,
            status=DriverStatus.INACTIVE,
        )
        response = self.client.get('/api/drivers/available/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [d['name'] for d in response.data['results']]
        self.assertIn('Available One', names)
        self.assertNotIn('Inactive One', names)

    def test_available_drivers_excludes_on_run(self):
        self._auth(self.manager)
        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='On Run Driver',
            phone_number='+1000000003',
            active=True,
            status=DriverStatus.ON_RUN,
        )
        response = self.client.get('/api/drivers/available/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [d['name'] for d in response.data['results']]
        self.assertNotIn('On Run Driver', names)

    def test_available_drivers_unauthorized(self):
        response = self.client.get('/api/drivers/available/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_available_drivers_as_driver_forbidden(self):
        self._auth(self.driver_user)
        response = self.client.get('/api/drivers/available/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Filtering Tests
# ---------------------------------------------------------------------------

class DriverFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/drivers/'

        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Alice',
            phone_number='+1111111111',
            active=True,
            status=DriverStatus.AVAILABLE,
        )
        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Bob',
            phone_number='+2222222222',
            active=True,
            status=DriverStatus.ON_RUN,
        )
        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Charlie',
            phone_number='+3333333333',
            active=False,
            status=DriverStatus.INACTIVE,
        )

    def test_filter_by_status_available(self):
        response = self.client.get(self.url, {'status': 'AVAILABLE'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [d['name'] for d in response.data['results']]
        self.assertIn('Alice', names)
        self.assertNotIn('Bob', names)
        self.assertNotIn('Charlie', names)

    def test_filter_by_status_on_run(self):
        response = self.client.get(self.url, {'status': 'ON_RUN'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [d['name'] for d in response.data['results']]
        self.assertIn('Bob', names)

    def test_filter_by_active_true(self):
        response = self.client.get(self.url, {'active': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [d['name'] for d in response.data['results']]
        self.assertIn('Alice', names)
        self.assertIn('Bob', names)
        self.assertNotIn('Charlie', names)

    def test_filter_by_active_false(self):
        response = self.client.get(self.url, {'active': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [d['name'] for d in response.data['results']]
        self.assertNotIn('Alice', names)
        self.assertNotIn('Bob', names)
        self.assertIn('Charlie', names)

    def test_combined_filter(self):
        response = self.client.get(self.url, {'status': 'AVAILABLE', 'active': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [d['name'] for d in response.data['results']]
        self.assertIn('Alice', names)
        self.assertNotIn('Bob', names)


# ---------------------------------------------------------------------------
# Search Tests
# ---------------------------------------------------------------------------

class DriverSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/drivers/'

        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Mohamed Ahmed',
            phone_number='+201234567890',
        )
        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Sara Hassan',
            phone_number='+201987654321',
        )

    def test_search_by_name(self):
        response = self.client.get(self.url, {'search': 'Mohamed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [d['name'] for d in response.data['results']]
        self.assertIn('Mohamed Ahmed', names)
        self.assertNotIn('Sara Hassan', names)

    def test_search_by_phone(self):
        response = self.client.get(self.url, {'search': '01987'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [d['name'] for d in response.data['results']]
        self.assertIn('Sara Hassan', names)
        self.assertNotIn('Mohamed Ahmed', names)

    def test_search_no_results(self):
        response = self.client.get(self.url, {'search': 'ZZZZZZZ'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)


# ---------------------------------------------------------------------------
# Ordering Tests
# ---------------------------------------------------------------------------

class DriverOrderingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/drivers/'

        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Zara',
            phone_number='+1111111111',
        )
        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Adam',
            phone_number='+2222222222',
        )
        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Mike',
            phone_number='+3333333333',
        )

    def test_order_by_name_ascending(self):
        response = self.client.get(self.url, {'ordering': 'name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [d['name'] for d in response.data['results']]
        self.assertEqual(names, sorted(names))

    def test_order_by_name_descending(self):
        response = self.client.get(self.url, {'ordering': '-name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [d['name'] for d in response.data['results']]
        self.assertEqual(names, sorted(names, reverse=True))

    def test_order_by_created_at(self):
        response = self.client.get(self.url, {'ordering': 'created_at'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_default_ordering_by_created_at_desc(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------

class DriverAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/drivers/'
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

class DriverStatusCodesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/drivers/'
        self.driver = _create_driver(user=self.manager, name='SC Driver', phone_number='+1111111111')

    def test_200_on_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_201_on_create(self):
        u = _create_user(role=RoleChoices.DRIVER)
        response = self.client.post(self.url, {
            'user': u.pk,
            'name': 'New',
            'phone_number': '+2222222222',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_204_on_delete(self):
        u = _create_user(role=RoleChoices.DRIVER)
        d = _create_driver(user=u, name='Del', phone_number='+3333333333')
        response = self.client.delete(f'{self.url}{d.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_404_on_nonexistent(self):
        response = self.client.get(f'{self.url}99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_400_on_invalid_data(self):
        u = _create_user(role=RoleChoices.DRIVER)
        response = self.client.post(self.url, {
            'user': u.pk,
            'name': '',
            'phone_number': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_405_on_wrong_method(self):
        response = self.client.put(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ---------------------------------------------------------------------------
# Dispatcher CRUD Tests
# ---------------------------------------------------------------------------

class DriverDispatcherCRUDTests(TestCase):
    """Verify dispatchers have full CRUD like managers."""

    def setUp(self):
        self.client = APIClient()
        self.dispatcher = _create_user(role=RoleChoices.DISPATCHER)
        self.driver_user = _create_user(role=RoleChoices.DRIVER)
        self.url = '/api/drivers/'
        self.driver = _create_driver(user=self.dispatcher, name='Disp Driver', phone_number='+1111111111')
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.dispatcher))

    def test_dispatcher_retrieve(self):
        response = self.client.get(f'{self.url}{self.driver.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Disp Driver')

    def test_dispatcher_patch(self):
        response = self.client.patch(f'{self.url}{self.driver.pk}/', {
            'name': 'Disp Patched',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Disp Patched')

    def test_dispatcher_delete(self):
        user_del = _create_user(role=RoleChoices.DRIVER)
        driver_del = _create_driver(user=user_del, name='Disp Del', phone_number='+2222222222')
        response = self.client.delete(f'{self.url}{driver_del.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_dispatcher_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dispatcher_available(self):
        response = self.client.get('/api/drivers/available/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# API Validation Tests
# ---------------------------------------------------------------------------

class DriverAPIValidationTests(TestCase):
    """Test API-level validation for all fields."""

    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/drivers/'
        self.driver = _create_driver(user=self.manager, name='Val Driver', phone_number='+1111111111')

    def test_create_invalid_max_stops_zero(self):
        u = _create_user(role=RoleChoices.DRIVER)
        response = self.client.post(self.url, {
            'user': u.pk,
            'name': 'Bad Stops',
            'phone_number': '+3333333333',
            'max_stops_per_run': 0,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_max_stops_negative(self):
        u = _create_user(role=RoleChoices.DRIVER)
        response = self.client.post(self.url, {
            'user': u.pk,
            'name': 'Bad Stops',
            'phone_number': '+3333333333',
            'max_stops_per_run': -5,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_status(self):
        u = _create_user(role=RoleChoices.DRIVER)
        response = self.client.post(self.url, {
            'user': u.pk,
            'name': 'Bad Status',
            'phone_number': '+3333333333',
            'status': 'BANANA',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_inactive_on_run(self):
        u = _create_user(role=RoleChoices.DRIVER)
        response = self.client.post(self.url, {
            'user': u.pk,
            'name': 'Bad Combo',
            'phone_number': '+3333333333',
            'active': False,
            'status': DriverStatus.ON_RUN,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_blank_phone(self):
        u = _create_user(role=RoleChoices.DRIVER)
        response = self.client.post(self.url, {
            'user': u.pk,
            'name': 'No Phone',
            'phone_number': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_blank_name(self):
        u = _create_user(role=RoleChoices.DRIVER)
        response = self.client.post(self.url, {
            'user': u.pk,
            'name': '',
            'phone_number': '+3333333333',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_required_fields(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_invalid_status(self):
        response = self.client.patch(f'{self.url}{self.driver.pk}/', {
            'status': 'INVALID',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_inactive_on_run(self):
        response = self.client.patch(f'{self.url}{self.driver.pk}/', {
            'active': False,
            'status': DriverStatus.ON_RUN,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_nonexistent_user(self):
        response = self.client.post(self.url, {
            'user': 99999,
            'name': 'Ghost',
            'phone_number': '+3333333333',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_duplicate_user(self):
        u = _create_user(role=RoleChoices.DRIVER)
        _create_driver(user=u, name='First', phone_number='+1111111111')
        response = self.client.post(self.url, {
            'user': u.pk,
            'name': 'Second',
            'phone_number': '+2222222222',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_valid_all_statuses(self):
        for status_val in DriverStatus.values:
            u = _create_user(role=RoleChoices.DRIVER)
            is_on_run = status_val == DriverStatus.ON_RUN
            response = self.client.post(self.url, {
                'user': u.pk,
                'name': f'Driver {status_val}',
                'phone_number': '+3333333333',
                'status': status_val,
                'active': True if is_on_run else True,
            }, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Available Endpoint Tests
# ---------------------------------------------------------------------------

class DriverAvailableEndpointTests(TestCase):
    """Test the /api/drivers/available/ endpoint thoroughly."""

    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/drivers/available/'

    def test_available_post_not_allowed(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_available_put_not_allowed(self):
        response = self.client.put(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_available_delete_not_allowed(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_available_only_returns_available_active(self):
        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Avail',
            phone_number='+1111111111',
            active=True,
            status=DriverStatus.AVAILABLE,
        )
        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='On Run',
            phone_number='+2222222222',
            active=True,
            status=DriverStatus.ON_RUN,
        )
        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Inactive',
            phone_number='+3333333333',
            active=False,
            status=DriverStatus.INACTIVE,
        )
        _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Active Inactive',
            phone_number='+4444444444',
            active=True,
            status=DriverStatus.INACTIVE,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [d['name'] for d in response.data['results']]
        self.assertIn('Avail', names)
        self.assertNotIn('On Run', names)
        self.assertNotIn('Inactive', names)
        self.assertNotIn('Active Inactive', names)


# ---------------------------------------------------------------------------
# Pagination Tests
# ---------------------------------------------------------------------------

class DriverPaginationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/drivers/'
        _create_driver(user=_create_user(role=RoleChoices.DRIVER), name='Page1', phone_number='+1111111111')
        _create_driver(user=_create_user(role=RoleChoices.DRIVER), name='Page2', phone_number='+2222222222')
        _create_driver(user=_create_user(role=RoleChoices.DRIVER), name='Page3', phone_number='+3333333333')

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
        response = self.client.get(self.url, {'page': 1, 'page_size': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIsNotNone(response.data['next'])


# ---------------------------------------------------------------------------
# Ordering Direction Tests
# ---------------------------------------------------------------------------

class DriverOrderingDirectionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = _create_user(role=RoleChoices.MANAGER)
        self.client.credentials(HTTP_AUTHORIZATION=_auth_header(self.manager))
        self.url = '/api/drivers/'
        self.d1 = _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Adam',
            phone_number='+1111111111',
        )
        self.d2 = _create_driver(
            user=_create_user(role=RoleChoices.DRIVER),
            name='Zara',
            phone_number='+2222222222',
        )

    def test_created_at_ascending(self):
        response = self.client.get(self.url, {'ordering': 'created_at'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [d['id'] for d in response.data['results']]
        self.assertEqual(ids[0], self.d1.pk)
        self.assertEqual(ids[-1], self.d2.pk)

    def test_created_at_descending(self):
        response = self.client.get(self.url, {'ordering': '-created_at'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [d['id'] for d in response.data['results']]
        self.assertEqual(ids[0], self.d2.pk)
        self.assertEqual(ids[-1], self.d1.pk)

    def test_invalid_ordering_field_ignored(self):
        response = self.client.get(self.url, {'ordering': 'nonexistent'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
