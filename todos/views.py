from rest_framework import generics
from .models import Todo
from .serializers import TodoSerializer


class TodoListCreateView(generics.ListCreateAPIView):
    """
    Эндпоинты для получения списка всех задач и создания новой задачи:
    GET /todos/ - список всех задач
    POST /todos/ - создание новой задачи
    """
    serializer_class = TodoSerializer

    def get_queryset(self):
        return Todo.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class TodoDetailView(generics.RetrieveUpdateDestroyAPIView):

    """ Эндпоинты для работы с отдельной задачей по id:

    Get /todos/<id>/ - одна задача по id
    Put /todos/<id>/ - обновление задачи по id
    Patch /todos/<id>/ - частичное обновление задачи по id
    Delete /todos/<id>/ - удаление задачи по id"""

    serializer_class = TodoSerializer

    def get_queryset(self):
        # по этому же queryset генерик ищет объект,
        # поэтому чужая задача даёт 404, а не 403
        return Todo.objects.filter(owner=self.request.user)
