# todo-drf

Простое API для списка задач на Django REST Framework. Учебное, разбирался с APIView.

Задача это title, completed и created_at, больше ничего.
Вьюхи написаны на APIView, а не на ViewSet — специально, чтобы руками расписать все методы.

## Запуск

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Ручки

```
GET    /api/todos/       список всех задач
POST   /api/todos/       создать задачу
GET    /api/todos/1/     одна задача
PUT    /api/todos/1/     заменить целиком
PATCH  /api/todos/1/     обновить часть полей
DELETE /api/todos/1/     удалить
```

Проверить:

```bash
curl http://127.0.0.1:8000/api/todos/
curl -X POST http://127.0.0.1:8000/api/todos/ -H "Content-Type: application/json" -d '{"title":"купить хлеб"}'
curl -X PATCH http://127.0.0.1:8000/api/todos/1/ -H "Content-Type: application/json" -d '{"completed":true}'
```

Админка на /admin/, туда нужен `python manage.py createsuperuser`.

## Заметки

- id и created_at только на чтение, руками не задаются
- база sqlite, лежит рядом и в репу не коммитится
- авторизации нет, любой может дёргать ручки, для учебного пока норм
