from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import RoleChoices, User
from .permissions import IsDispatcher, IsDriver, IsManager
from .serializers import UserSerializer


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------


class UserModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser',
        )

    def test_create_user(self):
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('testpass123'))
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.user.role, RoleChoices.DRIVER)

    def test_create_user_with_role(self):
        user = User.objects.create_user(
            email='manager@example.com',
            password='pass123',
            username='manager',
            role=RoleChoices.MANAGER,
        )
        self.assertEqual(user.role, RoleChoices.MANAGER)

    def test_create_user_no_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='pass123', username='noemail')

    def test_create_user_no_password_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='x@x.com', password='', username='nopass')

    def test_create_user_normalizes_email_domain(self):
        user = User.objects.create_user(
            email='User@EXAMPLE.COM',
            password='pass123',
            username='normalized',
        )
        self.assertEqual(user.email, 'User@example.com')

    def test_create_user_preserves_local_part_case(self):
        user = User.objects.create_user(
            email='Mixed@Example.Com',
            password='pass123',
            username='mixedcase',
        )
        self.assertEqual(user.email, 'Mixed@example.com')

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            username='admin',
        )
        self.assertEqual(admin.email, 'admin@example.com')
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, RoleChoices.MANAGER)

    def test_create_superuser_is_staff_false_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email='bad@example.com',
                password='pass123',
                username='badadmin',
                is_staff=False,
            )

    def test_create_superuser_is_superuser_false_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email='bad2@example.com',
                password='pass123',
                username='badadmin2',
                is_superuser=False,
            )

    def test_user_str(self):
        self.assertEqual(str(self.user), 'testuser (Driver)')

    def test_user_str_manager(self):
        self.user.role = RoleChoices.MANAGER
        self.user.save()
        self.assertEqual(str(self.user), 'testuser (Manager)')

    def test_email_is_unique(self):
        with self.assertRaises(Exception):
            User.objects.create_user(
                email='test@example.com',
                password='pass123',
                username='duplicate',
            )

    def test_username_is_unique(self):
        with self.assertRaises(Exception):
            User.objects.create_user(
                email='other@example.com',
                password='pass123',
                username='testuser',
            )

    def test_default_role_is_driver(self):
        user = User.objects.create_user(
            email='default@example.com',
            password='pass123',
            username='defaultrole',
        )
        self.assertEqual(user.role, RoleChoices.DRIVER)

    def test_role_max_length(self):
        field = User._meta.get_field('role')
        self.assertEqual(field.max_length, 20)


# ---------------------------------------------------------------------------
# Serializer Tests
# ---------------------------------------------------------------------------


class UserSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='serialize@example.com',
            password='pass123',
            username='serializeuser',
            first_name='Test',
            last_name='User',
            role=RoleChoices.DISPATCHER,
        )

    def test_serializer_fields(self):
        serializer = UserSerializer(self.user)
        data = serializer.data
        expected_fields = {'id', 'username', 'email', 'first_name', 'last_name', 'role', 'date_joined'}
        self.assertEqual(set(data.keys()), expected_fields)

    def test_serializer_read_only_fields(self):
        meta = UserSerializer.Meta
        self.assertIn('id', meta.read_only_fields)
        self.assertIn('role', meta.read_only_fields)
        self.assertIn('username', meta.read_only_fields)
        self.assertIn('email', meta.read_only_fields)
        self.assertIn('date_joined', meta.read_only_fields)

    def test_serializer_values(self):
        data = UserSerializer(self.user).data
        self.assertEqual(data['username'], 'serializeuser')
        self.assertEqual(data['email'], 'serialize@example.com')
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['role'], RoleChoices.DISPATCHER)
        self.assertIn('date_joined', data)
        self.assertIn('id', data)

    def test_serializer_date_joined_is_datetime_string(self):
        data = UserSerializer(self.user).data
        self.assertIsInstance(data['date_joined'], str)

    def test_serializer_update_first_name(self):
        serializer = UserSerializer(self.user, data={'first_name': 'Updated'}, partial=True)
        self.assertTrue(serializer.is_valid())
        updated = serializer.save()
        self.assertEqual(updated.first_name, 'Updated')

    def test_serializer_update_last_name(self):
        serializer = UserSerializer(self.user, data={'last_name': 'Changed'}, partial=True)
        self.assertTrue(serializer.is_valid())
        updated = serializer.save()
        self.assertEqual(updated.last_name, 'Changed')

    def test_serializer_cannot_change_role(self):
        serializer = UserSerializer(self.user, data={'role': RoleChoices.MANAGER}, partial=True)
        self.assertTrue(serializer.is_valid())
        updated = serializer.save()
        self.assertEqual(updated.role, RoleChoices.DISPATCHER)

    def test_serializer_cannot_change_email(self):
        serializer = UserSerializer(self.user, data={'email': 'hacker@example.com'}, partial=True)
        self.assertTrue(serializer.is_valid())
        updated = serializer.save()
        self.assertEqual(updated.email, 'serialize@example.com')

    def test_serializer_cannot_change_username(self):
        serializer = UserSerializer(self.user, data={'username': 'hacked'}, partial=True)
        self.assertTrue(serializer.is_valid())
        updated = serializer.save()
        self.assertEqual(updated.username, 'serializeuser')


# ---------------------------------------------------------------------------
# Permission Tests
# ---------------------------------------------------------------------------


class _MockRequest:
    def __init__(self, user):
        self.user = user


class _MockView:
    pass


class PermissionTests(TestCase):
    def setUp(self):
        self.view = _MockView()

        self.manager = User.objects.create_user(
            email='pm@manager.com', password='pass123', username='pmmgr',
            role=RoleChoices.MANAGER,
        )
        self.dispatcher = User.objects.create_user(
            email='pm@dispatch.com', password='pass123', username='pmdisp',
            role=RoleChoices.DISPATCHER,
        )
        self.driver = User.objects.create_user(
            email='pm@driver.com', password='pass123', username='pmdrv',
            role=RoleChoices.DRIVER,
        )

    # IsManager
    def test_is_manager_allows_manager(self):
        perm = IsManager()
        self.assertTrue(perm.has_permission(_MockRequest(self.manager), self.view))

    def test_is_manager_rejects_dispatcher(self):
        perm = IsManager()
        self.assertFalse(perm.has_permission(_MockRequest(self.dispatcher), self.view))

    def test_is_manager_rejects_driver(self):
        perm = IsManager()
        self.assertFalse(perm.has_permission(_MockRequest(self.driver), self.view))

    def test_is_manager_rejects_unauthenticated(self):
        from django.contrib.auth.models import AnonymousUser
        perm = IsManager()
        self.assertFalse(perm.has_permission(_MockRequest(AnonymousUser()), self.view))

    def test_is_manager_object_permission(self):
        perm = IsManager()
        self.assertTrue(perm.has_object_permission(_MockRequest(self.manager), self.view, self.manager))
        self.assertFalse(perm.has_object_permission(_MockRequest(self.dispatcher), self.view, self.manager))

    # IsDispatcher
    def test_is_dispatcher_allows_dispatcher(self):
        perm = IsDispatcher()
        self.assertTrue(perm.has_permission(_MockRequest(self.dispatcher), self.view))

    def test_is_dispatcher_rejects_manager(self):
        perm = IsDispatcher()
        self.assertFalse(perm.has_permission(_MockRequest(self.manager), self.view))

    def test_is_dispatcher_rejects_driver(self):
        perm = IsDispatcher()
        self.assertFalse(perm.has_permission(_MockRequest(self.driver), self.view))

    def test_is_dispatcher_rejects_unauthenticated(self):
        from django.contrib.auth.models import AnonymousUser
        perm = IsDispatcher()
        self.assertFalse(perm.has_permission(_MockRequest(AnonymousUser()), self.view))

    def test_is_dispatcher_object_permission(self):
        perm = IsDispatcher()
        self.assertTrue(perm.has_object_permission(_MockRequest(self.dispatcher), self.view, self.dispatcher))
        self.assertFalse(perm.has_object_permission(_MockRequest(self.driver), self.view, self.dispatcher))

    # IsDriver
    def test_is_driver_allows_driver(self):
        perm = IsDriver()
        self.assertTrue(perm.has_permission(_MockRequest(self.driver), self.view))

    def test_is_driver_rejects_manager(self):
        perm = IsDriver()
        self.assertFalse(perm.has_permission(_MockRequest(self.manager), self.view))

    def test_is_driver_rejects_dispatcher(self):
        perm = IsDriver()
        self.assertFalse(perm.has_permission(_MockRequest(self.dispatcher), self.view))

    def test_is_driver_rejects_unauthenticated(self):
        from django.contrib.auth.models import AnonymousUser
        perm = IsDriver()
        self.assertFalse(perm.has_permission(_MockRequest(AnonymousUser()), self.view))

    def test_is_driver_object_permission(self):
        perm = IsDriver()
        self.assertTrue(perm.has_object_permission(_MockRequest(self.driver), self.view, self.driver))
        self.assertFalse(perm.has_object_permission(_MockRequest(self.manager), self.view, self.driver))


# ---------------------------------------------------------------------------
# View Tests — MeView
# ---------------------------------------------------------------------------


class MeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='me@example.com',
            password='testpass123',
            username='meuser',
            first_name='Me',
            last_name='User',
            role=RoleChoices.DRIVER,
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.auth_header = f'Bearer {self.access_token}'

    def test_me_get_authenticated(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'meuser')
        self.assertEqual(response.data['email'], 'me@example.com')
        self.assertEqual(response.data['first_name'], 'Me')
        self.assertEqual(response.data['last_name'], 'User')
        self.assertEqual(response.data['role'], RoleChoices.DRIVER)
        self.assertIn('date_joined', response.data)
        self.assertIn('id', response.data)

    def test_me_get_unauthenticated(self):
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_patch_authenticated(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.patch('/api/auth/me/', {'first_name': 'New', 'last_name': 'Name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'New')
        self.assertEqual(response.data['last_name'], 'Name')

    def test_me_patch_partial(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.patch('/api/auth/me/', {'first_name': 'OnlyFirst'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'OnlyFirst')
        self.assertEqual(response.data['last_name'], 'User')

    def test_me_patch_read_only_fields_ignored(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.patch(
            '/api/auth/me/',
            {'role': 'MANAGER', 'email': 'hacked@h.com', 'username': 'hacked', 'id': 999},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], RoleChoices.DRIVER)
        self.assertEqual(response.data['email'], 'me@example.com')
        self.assertEqual(response.data['username'], 'meuser')

    def test_me_patch_unauthenticated(self):
        response = self.client.patch('/api/auth/me/', {'first_name': 'X'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_get_wrong_http_method_post(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.post('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_me_get_wrong_http_method_delete(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.delete('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_me_patch_empty_body(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.patch('/api/auth/me/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_me_patch_invalid_first_name_too_long(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.patch(
            '/api/auth/me/', {'first_name': 'x' * 151}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_response_content_type(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_me_get_returns_all_expected_fields(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.get('/api/auth/me/')
        expected_fields = {'id', 'username', 'email', 'first_name', 'last_name', 'role', 'date_joined'}
        self.assertEqual(set(response.data.keys()), expected_fields)

    def test_me_with_manager_role(self):
        self.user.role = RoleChoices.MANAGER
        self.user.save()
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.data['role'], RoleChoices.MANAGER)

    def test_me_with_dispatcher_role(self):
        self.user.role = RoleChoices.DISPATCHER
        self.user.save()
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.data['role'], RoleChoices.DISPATCHER)


# ---------------------------------------------------------------------------
# JWT Authentication — Login Endpoint Tests
# ---------------------------------------------------------------------------


class LoginEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='login@example.com',
            password='loginpass123',
            username='loginuser',
        )
        self.login_url = '/api/auth/login/'

    def test_login_successful(self):
        response = self.client.post(
            self.login_url,
            {'username': 'loginuser', 'password': 'loginpass123'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_returns_valid_access_token(self):
        response = self.client.post(
            self.login_url,
            {'username': 'loginuser', 'password': 'loginpass123'},
            format='json',
        )
        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        me_response = self.client.get('/api/auth/me/')
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)

    def test_login_wrong_password(self):
        response = self.client.post(
            self.login_url,
            {'username': 'loginuser', 'password': 'wrongpassword'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_wrong_username(self):
        response = self.client.post(
            self.login_url,
            {'username': 'nonexistent', 'password': 'loginpass123'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_empty_body(self):
        response = self.client.post(self.login_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_username(self):
        response = self.client.post(
            self.login_url,
            {'password': 'loginpass123'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_password(self):
        response = self.client.post(
            self.login_url,
            {'username': 'loginuser'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_get_method_not_allowed(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_login_put_method_not_allowed(self):
        response = self.client.put(self.login_url, {'username': 'loginuser', 'password': 'loginpass123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_login_patch_method_not_allowed(self):
        response = self.client.patch(self.login_url, {'username': 'loginuser'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_login_delete_method_not_allowed(self):
        response = self.client.delete(self.login_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_login_response_content_type(self):
        response = self.client.post(
            self.login_url,
            {'username': 'loginuser', 'password': 'loginpass123'},
            format='json',
        )
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_login_token_types_are_strings(self):
        response = self.client.post(
            self.login_url,
            {'username': 'loginuser', 'password': 'loginpass123'},
            format='json',
        )
        self.assertIsInstance(response.data['access'], str)
        self.assertIsInstance(response.data['refresh'], str)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.login_url,
            {'username': 'loginuser', 'password': 'loginpass123'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# JWT Authentication — Refresh Token Tests
# ---------------------------------------------------------------------------


class RefreshTokenEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='refresh@example.com',
            password='refreshpass123',
            username='refreshuser',
        )
        self.refresh_url = '/api/auth/refresh/'
        refresh = RefreshToken.for_user(self.user)
        self.valid_refresh_token = str(refresh)

    def test_refresh_successful(self):
        response = self.client.post(
            self.refresh_url,
            {'refresh': self.valid_refresh_token},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_refresh_returns_valid_access_token(self):
        response = self.client.post(
            self.refresh_url,
            {'refresh': self.valid_refresh_token},
            format='json',
        )
        new_access = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access}')
        me_response = self.client.get('/api/auth/me/')
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)

    def test_refresh_invalid_token(self):
        response = self.client.post(
            self.refresh_url,
            {'refresh': 'invalid.token.here'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_empty_body(self):
        response = self.client.post(self.refresh_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_missing_refresh_field(self):
        response = self.client.post(self.refresh_url, {'token': 'something'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_get_method_not_allowed(self):
        response = self.client.get(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_refresh_put_method_not_allowed(self):
        response = self.client.put(self.refresh_url, {'refresh': self.valid_refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_refresh_delete_method_not_allowed(self):
        response = self.client.delete(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_refresh_response_content_type(self):
        response = self.client.post(
            self.refresh_url,
            {'refresh': self.valid_refresh_token},
            format='json',
        )
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_refresh_garbage_string(self):
        response = self.client.post(
            self.refresh_url,
            {'refresh': 'not-a-jwt-token-at-all'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# JWT Authentication — Token Validation Tests
# ---------------------------------------------------------------------------


class TokenValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='validate@example.com',
            password='validatepass123',
            username='validateuser',
        )
        self.me_url = '/api/auth/me/'
        refresh = RefreshToken.for_user(self.user)
        self.valid_access_token = str(refresh.access_token)

    def test_valid_access_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.valid_access_token}')
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_access_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid.token.value')
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_bearer_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ')
        response = self.client.get(self.me_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_malformed_auth_header_no_bearer_prefix(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.valid_access_token)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_malformed_auth_header_wrong_scheme(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.valid_access_token}')
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_auth_header(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_cannot_be_used_as_access_token(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh)}')
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_after_user_deletion(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.valid_access_token}')
        self.user.delete()
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_after_user_deactivation(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.valid_access_token}')
        self.user.is_active = False
        self.user.save()
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Protected Endpoint — General
# ---------------------------------------------------------------------------


class ProtectedEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='protected@example.com',
            password='protectedpass123',
            username='protecteduser',
        )
        self.me_url = '/api/auth/me/'
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_get_protected_endpoint(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_protected_endpoint_not_allowed(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(self.me_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_protected_endpoint_not_allowed(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.put(self.me_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_protected_endpoint_not_allowed(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.delete(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_unauthenticated_access_denied(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


class EdgeCaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.me_url = '/api/auth/me/'
        self.login_url = '/api/auth/login/'
        self.refresh_url = '/api/auth/refresh/'

    def test_nonexistent_endpoint(self):
        response = self.client.get('/api/auth/nonexistent/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_login_with_json_content_type_and_form_data(self):
        User.objects.create_user(
            email='form@example.com', password='formpass123', username='formuser',
        )
        response = self.client.post(
            self.login_url,
            'username=formuser&password=formpass123',
            content_type='application/x-www-form-urlencoded',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_malformed_json_body(self):
        response = self.client.post(
            self.login_url,
            '{invalid json',
            content_type='application/json',
        )
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        ])

    def test_login_with_empty_string_credentials(self):
        response = self.client.post(
            self.login_url,
            {'username': '', 'password': ''},
            format='json',
        )
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ])

    def test_refresh_with_empty_string_token(self):
        response = self.client.post(
            self.refresh_url,
            {'refresh': ''},
            format='json',
        )
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ])

    def test_concurrent_token_usage(self):
        user = User.objects.create_user(
            email='concurrent@example.com', password='concpass123', username='concurrent',
        )
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        for _ in range(5):
            response = self.client.get(self.me_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Admin Tests
# ---------------------------------------------------------------------------


class AdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='superadmin@example.com',
            password='superadmin123',
            username='superadmin',
        )
        self.client = APIClient()
        self.client.force_login(self.admin_user)

    def test_admin_accessible(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_user_list_accessible(self):
        response = self.client.get('/admin/accounts/user/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_admin_redirect(self):
        self.client.logout()
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
