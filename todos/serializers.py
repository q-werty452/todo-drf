from rest_framework import serializers
from .models import Todo


class TodoSerializer(serializers.ModelSerializer):
    '''
    Сериализатор для модели Todo.'''
    class Meta:
        model =Todo
        fields = ['id', 'title', 'completed', 'created_at']
        read_only_fields = ['id', 'created_at']