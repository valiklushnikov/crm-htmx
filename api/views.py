import logging

from django.db import transaction
from rest_framework import generics
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from django.contrib.auth import authenticate

from apps.users.models import User
from apps.main.models import Employee, Task
from .utils import set_auth_cookies
from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    LoginSerializer,
    EmployeeDetailSerializer, TaskCreateUpdateSerializer, TaskSerializer, UserListSerializer
)


logger = logging.getLogger(__name__)

class RegisterAPIView(generics.CreateAPIView):
    """API для реєстрації нових користувачів"""
    serializer_class = UserRegistrationSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                user = serializer.save()

                refresh = RefreshToken.for_user(user)
                access = refresh.access_token

            response = Response({
                'user': UserSerializer(user).data,
                'message': 'Реєстрація успішна'
            }, status=status.HTTP_201_CREATED)

            return set_auth_cookies(response, access_token=str(access), refresh_token=str(refresh))
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return Response({
                'error': 'Помилка реєстрації'
            }, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    """API для входу користувача"""
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer
    throttle_classes = (AnonRateThrottle,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(username=email, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token

            response = Response({
                'user': UserSerializer(user).data,
                'message': 'Вхід виконано успішно'
            }, status=status.HTTP_200_OK)
            return set_auth_cookies(response, access_token=str(access), refresh_token=str(refresh))
        else:
            return Response({
                'error': 'Невірне ім\'я користувача або пароль'
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutAPIView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        user_info = getattr(request.user, 'email', 'Anonymous')

        try:
            refresh_token = request.COOKIES.get("refresh_token")

            if refresh_token:
                try:
                    with transaction.atomic():
                        token = RefreshToken(refresh_token)
                        token.blacklist()
                    logger.info(f"Token blacklisted for user: {user_info}")
                except TokenError as e:
                    # Токен невалідний або вже в blacklist
                    logger.warning(f"Token error during logout for {user_info}: {e}")
            else:
                logger.info(f"No refresh token found for logout: {user_info}")

        except Exception as e:
            logger.error(f"Unexpected error during logout for {user_info}: {e}")

        response = Response({"message": "Вихід виконано успішно"})

        # Видаляємо cookies з тими ж параметрами, що і при створенні
        response.delete_cookie(
            key='access_token',
            path='/',
            samesite='Lax'
        )
        response.delete_cookie(
            key='refresh_token',
            path='/',
            samesite='Lax'
        )

        logger.info(f"Logout completed for user: {user_info}")
        return response


class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """API для отримання та оновлення профілю поточного користувача"""
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        from .serializers import UserProfileSerializer
        return UserProfileSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_api(request):
    """API для зміни пароля користувача"""
    from .serializers import ChangePasswordSerializer
    
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Пароль успішно змінено'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenRefreshView(TokenRefreshView):
    """Кастомний view для оновлення токена"""
    permission_classes = (AllowAny,)
    
    def post(self, request, *args, **kwargs):
        # Отримуємо refresh token з cookies
        refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            return Response({
                'error': 'Refresh token not found'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Додаємо refresh token до request.data
        request.data['refresh'] = refresh_token
        
        try:
            response = super().post(request, *args, **kwargs)
            
            if response.status_code == 200:
                # Отримуємо новий access token
                access_token = response.data.get('access')
                
                # Встановлюємо новий access token в cookies
                response = set_auth_cookies(
                    response, 
                    access_token=access_token,
                    refresh_token=refresh_token
                )
                
            return response
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return Response({
                'error': 'Failed to refresh token'
            }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employee_detail_api(request, id):
    """
    Получить детали сотрудника по ID
    Доступно только аутентифицированным пользователям
    """
    try:
        employee = Employee.objects.prefetch_related(
            "employment_period",
            "documents",
            "work_permits",
            "card_submissions",
            "contracts",
            "sanepids",
            "contacts",
        ).get(id=id)
    except Employee.DoesNotExist:
        return Response(
            {'error': 'Сотрудник не знайдений'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = EmployeeDetailSerializer(employee)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def employee_delete_api(request, id):
    """
    Удалить сотрудника по ID
    Доступно только аутентифицированным пользователям
    """
    try:
        employee = Employee.objects.get(id=id)
    except Employee.DoesNotExist:
        return Response(
            {'error': 'Сотрудник не знайдений'},
            status=status.HTTP_404_NOT_FOUND
        )

    employee_name = employee.get_full_name
    try:
        with transaction.atomic():
            # Видаляємо співробітника та всі пов'язані об'єкти
            employee.delete()

        return Response(
            {'message': f'Сотрудник {employee_name} успішно видалений'},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        logger.error(f"Employee deletion error: {e}")
        return Response(
            {'error': 'Помилка видалення співробітника'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class UserListAPIView(generics.ListAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserListSerializer
    permission_classes = (IsAuthenticated,)


class TaskListCreateAPIView(generics.ListCreateAPIView):
    """API для отримання списку завдань та створення нового"""
    queryset = Task.objects.all()
    permission_classes = (IsAuthenticated,)  # Тимчасово для тестування

    def get_queryset(self):
        queryset = super().get_queryset()
        assigned_to = self.request.query_params.get('assigned_to', None)
        if assigned_to is not None:
            if assigned_to == 'me':
                assigned_to = self.request.user.id
            queryset = queryset.filter(assigned_to_id=assigned_to)
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskCreateUpdateSerializer
        return TaskSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class TaskRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """API для отримання, оновлення та видалення завдання"""
    queryset = Task.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return TaskCreateUpdateSerializer
        return TaskSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_update(self, serializer):
        task = self.get_object()
        new_status = serializer.validated_data.get('status', task.status)

        # Отримуємо користувача
        user = self.request.user if self.request.user.is_authenticated else None

        # Перевірка автентифікації
        if not user or not user.is_authenticated:
            raise PermissionDenied("Потрібна автентифікація")

        # Перевірка прав на редагування
        if not task.can_edit(user):
            # Дозволяємо тільки зміну статусу для не-власників
            if set(serializer.validated_data.keys()) != {'status'}:
                raise PermissionDenied("Тільки автор може редагувати це завдання")

        # Логіка зміни статусу
        from django.utils import timezone

        try:
            with transaction.atomic():
                if new_status == 'in_progress':
                    # СПОЧАТКУ блокуємо запис, ПОТІМ перевіряємо статус
                    task_locked = Task.objects.select_for_update().get(pk=task.pk)

                    # Тепер перевіряємо статус на заблокованому об'єкті
                    if task_locked.status != 'todo':
                        raise DRFValidationError({"detail": "Завдання вже не в статусі 'todo'"})

                    if task_locked.taken_by and task_locked.taken_by != user:
                        raise DRFValidationError({"detail": "Це завдання вже хтось виконує"})

                    # Перевіряємо чи може користувач взяти завдання
                    if task_locked.assigned_to and task_locked.assigned_to != user:
                        raise DRFValidationError({"detail": "Це завдання призначене іншому користувачу"})

                    serializer.save(
                        taken_by=user,
                        taken_at=timezone.now()
                    )

                elif new_status == 'completed':
                    serializer.save(completed_at=timezone.now())

                elif new_status == 'todo':
                    # Блокуємо перед зміною
                    task_locked = Task.objects.select_for_update().get(pk=task.pk)

                    if task_locked.status == 'in_progress':
                        serializer.save(
                            taken_by=None,
                            taken_at=None
                        )
                    else:
                        serializer.save()
                else:
                    serializer.save()

        except DRFValidationError:
            raise
        except Exception as e:
            logger.error(f"Task update error: {e}")
            raise DRFValidationError({"detail": "Помилка оновлення завдання"})

    def perform_destroy(self, instance):
        """Тільки суперюзер може видалити завдання"""
        user = self.request.user if self.request.user.is_authenticated else None
        
        if not user or not user.is_authenticated:
            raise PermissionDenied("Потрібна автентифікація")
        
        if not user.is_superuser:
            raise PermissionDenied("Тільки адміністратор може видаляти завдання")
        
        instance.delete()
