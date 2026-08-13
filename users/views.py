from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import CustomUser
from .serializers import RegisterSerializer


class RegisterView(generics.CreateAPIView):
    """
    POST /api/register/ - регистрация нового пользователя.

    Открыт для всех: без AllowAny сюда не пустил бы глобальный
    IsAuthenticated из REST_FRAMEWORK.
    В ответе сразу отдаём токен, чтобы после регистрации
    не ходить отдельно на /api/token/.
    """

    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {'email': user.email, 'token': token.key},
            status=status.HTTP_201_CREATED,
        )
