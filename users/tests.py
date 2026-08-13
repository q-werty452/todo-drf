from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import CustomUser

PASSWORD = 'Tr0ub4dour-x9'


class RegisterTests(APITestCase):
    url = '/api/register/'

    def test_register_returns_token(self):
        response = self.client.post(self.url, {
            'email': 'student@mail.ru',
            'password': PASSWORD,
            'password2': PASSWORD,
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'student@mail.ru')
        self.assertEqual(len(response.data['token']), 40)

        user = CustomUser.objects.get(email='student@mail.ru')
        self.assertEqual(Token.objects.get(user=user).key, response.data['token'])

    def test_password_not_in_response(self):
        response = self.client.post(self.url, {
            'email': 'student@mail.ru',
            'password': PASSWORD,
            'password2': PASSWORD,
        })

        self.assertNotIn('password', response.data)
        self.assertNotIn('password2', response.data)

    def test_password_is_hashed(self):
        self.client.post(self.url, {
            'email': 'student@mail.ru',
            'password': PASSWORD,
            'password2': PASSWORD,
        })

        user = CustomUser.objects.get(email='student@mail.ru')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))
        self.assertTrue(user.check_password(PASSWORD))

    def test_passwords_do_not_match(self):
        response = self.client.post(self.url, {
            'email': 'student@mail.ru',
            'password': PASSWORD,
            'password2': 'Drugoy-parol-77',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CustomUser.objects.filter(email='student@mail.ru').exists())

    def test_weak_password(self):
        response = self.client.post(self.url, {
            'email': 'student@mail.ru',
            'password': '123',
            'password2': '123',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CustomUser.objects.filter(email='student@mail.ru').exists())

    def test_email_already_exists(self):
        CustomUser.objects.create_user(email='student@mail.ru', password=PASSWORD)

        response = self.client.post(self.url, {
            'email': 'student@mail.ru',
            'password': PASSWORD,
            'password2': PASSWORD,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CustomUser.objects.filter(email='student@mail.ru').count(), 1)

    def test_invalid_email(self):
        response = self.client.post(self.url, {
            'email': 'ne-email',
            'password': PASSWORD,
            'password2': PASSWORD,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_allows_anonymous(self):
        response = self.client.post(self.url, {
            'email': 'student@mail.ru',
            'password': PASSWORD,
            'password2': PASSWORD,
        })

        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LoginTests(APITestCase):
    url = '/api/token/'

    def setUp(self):
        self.user = CustomUser.objects.create_user(email='student@mail.ru', password=PASSWORD)

    def test_login_returns_token(self):
        response = self.client.post(self.url, {
            'username': 'student@mail.ru',
            'password': PASSWORD,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['token'], Token.objects.get(user=self.user).key)

    def test_login_returns_same_token(self):
        first = self.client.post(self.url, {'username': 'student@mail.ru', 'password': PASSWORD})
        second = self.client.post(self.url, {'username': 'student@mail.ru', 'password': PASSWORD})

        self.assertEqual(first.data['token'], second.data['token'])

    def test_wrong_password(self):
        response = self.client.post(self.url, {
            'username': 'student@mail.ru',
            'password': 'sovsem-drugoy-99',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CustomUserModelTests(APITestCase):

    def test_username_field_is_email(self):
        self.assertEqual(CustomUser.USERNAME_FIELD, 'email')
        self.assertEqual(CustomUser.REQUIRED_FIELDS, [])

        field_names = [field.name for field in CustomUser._meta.get_fields()]
        self.assertNotIn('username', field_names)
        self.assertIn('email', field_names)

    def test_create_user(self):
        user = CustomUser.objects.create_user(email='student@mail.ru', password=PASSWORD)

        self.assertEqual(str(user), 'student@mail.ru')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_superuser(self):
        admin = CustomUser.objects.create_superuser(email='admin@mail.ru', password=PASSWORD)

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_create_user_without_email(self):
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(email='', password=PASSWORD)
