from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from apps.users.models import InviteToken
from apps.main.models import (
    Employee,
    EmploymentPeriod,
    Document,
    WorkPermit,
    CardSubmission,
    Contract,
    Sanepid,
    Contact,
    Task
)

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)
    invite_token = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'first_name', 'last_name', 'invite_token')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True}
        }

    def validate(self, attrs):
        from django.utils import timezone
        from apps.users.models import InviteToken

        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Паролі не співпадають"
            })
        token = attrs.get('invite_token')

        if not token:
            raise serializers.ValidationError({"invite_token": "Недійсне запрошення."})
        try:
            invite = InviteToken.objects.get(token=token)
        except InviteToken.DoesNotExist:
            raise serializers.ValidationError({"invite_token": "Недійсне запрошення."})

        if invite.expires_at < timezone.now():
            raise serializers.ValidationError({"invite_token": "Термін дії запрошення минув."})

        if invite.email.lower() != attrs["email"].lower():
            raise serializers.ValidationError({"email": "Email не відповідає запрошенню."})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        invite = validated_data.pop('invite_token')
        invite_token = InviteToken.objects.get(token=invite)
        invite_token.delete()

        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer для профиля пользователя с возможностью обновления"""
    avatar = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'avatar', 'date_joined')
        read_only_fields = ('id', 'email', 'date_joined')


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer для смены пароля"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Паролі не співпадають"})
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неправильний старий пароль")
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class EmploymentPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentPeriod
        fields = '__all__'


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'


class WorkPermitSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkPermit
        fields = '__all__'


class CardSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardSubmission
        fields = '__all__'


class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = '__all__'


class SanepidSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sanepid
        fields = '__all__'


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'


class EmployeeDetailSerializer(serializers.ModelSerializer):
    employment_period = EmploymentPeriodSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    work_permits = WorkPermitSerializer(many=True, read_only=True)
    card_submissions = CardSubmissionSerializer(many=True, read_only=True)
    contracts = ContractSerializer(many=True, read_only=True)
    sanepids = SanepidSerializer(many=True, read_only=True)
    contacts = ContactSerializer(many=True, read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id',
            'first_name',
            'last_name',
            'age',
            'is_student',
            'pesel',
            'pesel_urk',
            'workplace',
            'pit_2',
            'working_status',
            'additional_information',
            'student_end_date',
            'employment_period',
            'documents',
            'work_permits',
            'card_submissions',
            'contracts',
            'sanepids',
            'contacts',
        ]


class UserListSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'get_full_name')
        read_only_fields = ('id', 'email', 'first_name', 'last_name')


class TaskSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    taken_by_name = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_take = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'status', 'priority',
            'assigned_to', 'assigned_to_name', 'created_by', 'created_by_name',
            'taken_by', 'taken_by_name', 'taken_at',
            'created_at', 'updated_at', 'due_date', 'completed_at',
            'is_locked', 'can_edit', 'can_take', 'can_delete',
        )
        read_only_fields = ('created_by', 'taken_by', 'taken_at', 'created_at', 'updated_at', 'completed_at')

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return None

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}"
        return None

    def get_taken_by_name(self, obj):
        if obj.taken_by:
            return f"{obj.taken_by.first_name} {obj.taken_by.last_name}"
        return None

    def get_is_locked(self, obj):
        return obj.is_locked()

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return obj.can_edit(request.user)
        # Для тестування без авторизації - дозволяємо все
        return True

    def get_can_take(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return obj.can_take(request.user)
        # Для тестування без авторизації - дозволяємо все
        return True
    
    def get_can_delete(self, obj):
        """Перевіряємо чи може користувач видалити завдання"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_delete(request.user)
        return False


class TaskCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'status', 'priority',
            'assigned_to', 'due_date'
        )

    def validate_assigned_to(self, value):
        # Валидация существования пользователя
        if value is not None:
            if not User.objects.filter(id=value.id).exists():
                raise serializers.ValidationError("User does not exist")
        return value

    def create(self, validated_data):
        # Якщо є користувач в request, використовуємо його
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        else:
            # Для тестування використовуємо першого користувача
            from django.contrib.auth import get_user_model
            User = get_user_model()
            validated_data['created_by'] = User.objects.first()
        return super().create(validated_data)