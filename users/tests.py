from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import CustomUser

PASSWORD = 'Tr0ub4dour-x9'


class RegisterTests(APITestCase):
    """POST /api/register/ - регистрация нового пользователя."""

    url = '/api/register/'

    def test_регистрация_создаёт_пользователя_и_отдаёт_токен(self):
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

    def test_пароль_не_возвращается_в_ответе(self):
        response = self.client.post(self.url, {
            'email': 'student@mail.ru',
            'password': PASSWORD,
            'password2': PASSWORD,
        })

        self.assertNotIn('password', response.data)
        self.assertNotIn('password2', response.data)

    def test_пароль_в_базе_захеширован(self):
        self.client.post(self.url, {
            'email': 'student@mail.ru',
            'password': PASSWORD,
            'password2': PASSWORD,
        })

        user = CustomUser.objects.get(email='student@mail.ru')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))
        self.assertTrue(user.check_password(PASSWORD))

    def test_пароли_не_совпадают(self):
        response = self.client.post(self.url, {
            'email': 'student@mail.ru',
            'password': PASSWORD,
            'password2': 'Drugoy-parol-77',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('не совпадают', response.data['password'][0])
        self.assertFalse(CustomUser.objects.filter(email='student@mail.ru').exists())

    def test_слишком_слабый_пароль(self):
        response = self.client.post(self.url, {
            'email': 'student@mail.ru',
            'password': '123',
            'password2': '123',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CustomUser.objects.filter(email='student@mail.ru').exists())

    def test_email_уже_занят(self):
        CustomUser.objects.create_user(email='student@mail.ru', password=PASSWORD)

        response = self.client.post(self.url, {
            'email': 'student@mail.ru',
            'password': PASSWORD,
            'password2': PASSWORD,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CustomUser.objects.filter(email='student@mail.ru').count(), 1)

    def test_кривой_email(self):
        response = self.client.post(self.url, {
            'email': 'ne-email',
            'password': PASSWORD,
            'password2': PASSWORD,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_регистрация_открыта_без_авторизации(self):
        """AllowAny: иначе зарегистрироваться мог бы только уже зарегистрированный."""
        response = self.client.post(self.url, {
            'email': 'student@mail.ru',
            'password': PASSWORD,
            'password2': PASSWORD,
        })

        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LoginTests(APITestCase):
    """POST /api/token/ - повторный вход по email и паролю."""

    url = '/api/token/'

    def setUp(self):
        self.user = CustomUser.objects.create_user(email='student@mail.ru', password=PASSWORD)

    def test_вход_по_email_отдаёт_токен(self):
        # поле называется username, но модель ищет человека по email,
        # потому что USERNAME_FIELD = "email"
        response = self.client.post(self.url, {
            'username': 'student@mail.ru',
            'password': PASSWORD,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['token'], Token.objects.get(user=self.user).key)

    def test_повторный_вход_отдаёт_тот_же_токен(self):
        first = self.client.post(self.url, {'username': 'student@mail.ru', 'password': PASSWORD})
        second = self.client.post(self.url, {'username': 'student@mail.ru', 'password': PASSWORD})

        self.assertEqual(first.data['token'], second.data['token'])

    def test_неверный_пароль(self):
        response = self.client.post(self.url, {
            'username': 'student@mail.ru',
            'password': 'sovsem-drugoy-99',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CustomUserModelTests(APITestCase):
    """Сама модель пользователя: вход по email вместо username."""

    def test_у_модели_нет_поля_username(self):
        self.assertEqual(CustomUser.USERNAME_FIELD, 'email')
        self.assertEqual(CustomUser.REQUIRED_FIELDS, [])

        # username = None убирает не атрибут, а само поле - колонки в таблице нет
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

    def test_без_email_создать_нельзя(self):
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(email='', password=PASSWORD)
