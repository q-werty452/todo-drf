from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Todo

CustomUser = get_user_model()
PASSWORD = 'Tr0ub4dour-x9'


def access_for(user):
    """access-токен для юзера, без похода на /api/token/."""
    return str(RefreshToken.for_user(user).access_token)


class TodoAuthTests(APITestCase):
    """Без токена внутрь не пускают."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(email='student@mail.ru', password=PASSWORD)
        self.todo = Todo.objects.create(owner=self.user, title='Сделать домашку')

    def test_list_without_token(self):
        response = self.client.get('/api/todos/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Authentication credentials', response.data['detail'])

    def test_create_without_token(self):
        response = self.client.post('/api/todos/', {'title': 'Тайком'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Todo.objects.count(), 1)

    def test_detail_without_token(self):
        response = self.client.get(f'/api/todos/{self.todo.pk}/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + 'f' * 40)
        response = self.client.get('/api/todos/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tampered_token(self):
        """Подмена данных внутри токена ломает подпись."""
        header, payload, signature = access_for(self.user).split('.')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {header}.{payload}.xxx')
        response = self.client.get('/api/todos/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_without_prefix(self):
        """Частая ошибка в Postman: забыли префикс."""
        self.client.credentials(HTTP_AUTHORIZATION=access_for(self.user))
        response = self.client.get('/api/todos/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TodoCrudTests(APITestCase):
    """Весь CRUD от лица владельца."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(email='student@mail.ru', password=PASSWORD)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_for(self.user))

    def test_create_todo(self):
        response = self.client.post('/api/todos/', {'title': 'Сделать домашку'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Сделать домашку')
        self.assertFalse(response.data['completed'])

    def test_owner_set_from_token(self):
        self.client.post('/api/todos/', {'title': 'Сделать домашку'})

        self.assertEqual(Todo.objects.get().owner, self.user)

    def test_cannot_set_other_owner(self):
        """owner не входит в поля сериализатора, поэтому из тела запроса не читается."""
        chuzhoy = CustomUser.objects.create_user(email='petya@mail.ru', password=PASSWORD)

        self.client.post('/api/todos/', {'title': 'Сделать домашку', 'owner': chuzhoy.pk})

        self.assertEqual(Todo.objects.get().owner, self.user)

    def test_list_todos(self):
        Todo.objects.create(owner=self.user, title='Первая')
        Todo.objects.create(owner=self.user, title='Вторая')

        response = self.client.get('/api/todos/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_todo(self):
        todo = Todo.objects.create(owner=self.user, title='Сделать домашку')

        response = self.client.get(f'/api/todos/{todo.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Сделать домашку')

    def test_patch_todo(self):
        todo = Todo.objects.create(owner=self.user, title='Сделать домашку')

        response = self.client.patch(f'/api/todos/{todo.pk}/', {'completed': True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['completed'])
        self.assertEqual(response.data['title'], 'Сделать домашку')

    def test_put_todo(self):
        """Разница с PATCH: непереданное completed сбрасывается в значение по умолчанию."""
        todo = Todo.objects.create(owner=self.user, title='Сделать домашку', completed=True)

        response = self.client.put(f'/api/todos/{todo.pk}/', {'title': 'Домашка по математике'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Домашка по математике')
        self.assertFalse(response.data['completed'])

    def test_put_requires_title(self):
        todo = Todo.objects.create(owner=self.user, title='Сделать домашку')

        response = self.client.put(f'/api/todos/{todo.pk}/', {'completed': True})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_todo(self):
        todo = Todo.objects.create(owner=self.user, title='Сделать домашку')

        response = self.client.delete(f'/api/todos/{todo.pk}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Todo.objects.filter(pk=todo.pk).exists())

    def test_read_only_fields(self):
        response = self.client.post('/api/todos/', {
            'title': 'Сделать домашку',
            'id': 999,
            'created_at': '2000-01-01T00:00:00Z',
        })

        self.assertNotEqual(response.data['id'], 999)
        self.assertNotIn('2000', response.data['created_at'])


class TodoIsolationTests(APITestCase):
    """Главное: чужие задачи не видны и не трогаются."""

    def setUp(self):
        self.student = CustomUser.objects.create_user(email='student@mail.ru', password=PASSWORD)
        self.petya = CustomUser.objects.create_user(email='petya@mail.ru', password=PASSWORD)

        self.todo = Todo.objects.create(owner=self.student, title='Задача студента')

        # ходим от лица Пети
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_for(self.petya))

    def test_other_user_list_is_empty(self):
        response = self.client.get('/api/todos/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_other_user_gets_404(self):
        """403 подтвердил бы, что задача существует. 404 не выдаёт ничего."""
        response = self.client.get(f'/api/todos/{self.todo.pk}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_other_user_cannot_update(self):
        response = self.client.patch(f'/api/todos/{self.todo.pk}/', {'title': 'Взломано'})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.todo.refresh_from_db()
        self.assertEqual(self.todo.title, 'Задача студента')

    def test_other_user_cannot_delete(self):
        response = self.client.delete(f'/api/todos/{self.todo.pk}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Todo.objects.filter(pk=self.todo.pk).exists())

    def test_each_user_has_own_list(self):
        Todo.objects.create(owner=self.petya, title='Задача Пети')

        response = self.client.get('/api/todos/')

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Задача Пети')
