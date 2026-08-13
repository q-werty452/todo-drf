from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Todo

CustomUser = get_user_model()
PASSWORD = 'Tr0ub4dour-x9'


class TodoAuthTests(APITestCase):
    """Без токена внутрь не пускают."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(email='student@mail.ru', password=PASSWORD)
        self.todo = Todo.objects.create(owner=self.user, title='Сделать домашку')

    def test_список_без_токена(self):
        response = self.client.get('/api/todos/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Authentication credentials', response.data['detail'])

    def test_создание_без_токена(self):
        response = self.client.post('/api/todos/', {'title': 'Тайком'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Todo.objects.count(), 1)

    def test_одна_задача_без_токена(self):
        response = self.client.get(f'/api/todos/{self.todo.pk}/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_несуществующий_токен(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + 'f' * 40)
        response = self.client.get('/api/todos/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_токен_без_слова_Token(self):
        """Частая ошибка в Postman: забыли префикс."""
        key = Token.objects.create(user=self.user).key
        self.client.credentials(HTTP_AUTHORIZATION=key)
        response = self.client.get('/api/todos/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TodoCrudTests(APITestCase):
    """Весь CRUD от лица владельца."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(email='student@mail.ru', password=PASSWORD)
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_создать_задачу(self):
        response = self.client.post('/api/todos/', {'title': 'Сделать домашку'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Сделать домашку')
        self.assertFalse(response.data['completed'])

    def test_владелец_проставляется_из_токена(self):
        self.client.post('/api/todos/', {'title': 'Сделать домашку'})

        self.assertEqual(Todo.objects.get().owner, self.user)

    def test_чужого_владельца_подсунуть_нельзя(self):
        """owner не входит в поля сериализатора, поэтому из тела запроса не читается."""
        chuzhoy = CustomUser.objects.create_user(email='petya@mail.ru', password=PASSWORD)

        self.client.post('/api/todos/', {'title': 'Сделать домашку', 'owner': chuzhoy.pk})

        self.assertEqual(Todo.objects.get().owner, self.user)

    def test_список_своих_задач(self):
        Todo.objects.create(owner=self.user, title='Первая')
        Todo.objects.create(owner=self.user, title='Вторая')

        response = self.client.get('/api/todos/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_одна_задача_по_id(self):
        todo = Todo.objects.create(owner=self.user, title='Сделать домашку')

        response = self.client.get(f'/api/todos/{todo.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Сделать домашку')

    def test_patch_меняет_только_переданное(self):
        todo = Todo.objects.create(owner=self.user, title='Сделать домашку')

        response = self.client.patch(f'/api/todos/{todo.pk}/', {'completed': True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['completed'])
        self.assertEqual(response.data['title'], 'Сделать домашку')

    def test_put_заменяет_запись_целиком(self):
        """Разница с PATCH: непереданное completed сбрасывается в значение по умолчанию."""
        todo = Todo.objects.create(owner=self.user, title='Сделать домашку', completed=True)

        response = self.client.put(f'/api/todos/{todo.pk}/', {'title': 'Домашка по математике'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Домашка по математике')
        self.assertFalse(response.data['completed'])

    def test_put_без_обязательного_поля(self):
        todo = Todo.objects.create(owner=self.user, title='Сделать домашку')

        response = self.client.put(f'/api/todos/{todo.pk}/', {'completed': True})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_удалить_задачу(self):
        todo = Todo.objects.create(owner=self.user, title='Сделать домашку')

        response = self.client.delete(f'/api/todos/{todo.pk}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Todo.objects.filter(pk=todo.pk).exists())

    def test_id_и_created_at_только_на_чтение(self):
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
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + Token.objects.create(user=self.petya).key)

    def test_чужой_список_пуст(self):
        response = self.client.get('/api/todos/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_чужая_задача_даёт_404_а_не_403(self):
        """403 подтвердил бы, что задача существует. 404 не выдаёт ничего."""
        response = self.client.get(f'/api/todos/{self.todo.pk}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_чужую_задачу_нельзя_изменить(self):
        response = self.client.patch(f'/api/todos/{self.todo.pk}/', {'title': 'Взломано'})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.todo.refresh_from_db()
        self.assertEqual(self.todo.title, 'Задача студента')

    def test_чужую_задачу_нельзя_удалить(self):
        response = self.client.delete(f'/api/todos/{self.todo.pk}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Todo.objects.filter(pk=self.todo.pk).exists())

    def test_у_каждого_свой_список(self):
        Todo.objects.create(owner=self.petya, title='Задача Пети')

        response = self.client.get('/api/todos/')

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Задача Пети')
