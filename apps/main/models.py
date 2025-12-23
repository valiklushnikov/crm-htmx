from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from .querysets import EmployeeQuerySet
from .utils import get_change_user

class EmployeeManager(models.Manager):
    def get_queryset(self):
        return EmployeeQuerySet(self.model, using=self._db)
    
    def base_select(self):
        return self.get_queryset().base_select()

    def with_period_annotations(self):
        return self.get_queryset().with_period_annotations()


class History(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    field_name = models.CharField(max_length=128)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)

    action = models.CharField(max_length=16, choices=(
        ('created', 'created'),
        ('updated', 'updated'),
        ('deleted', 'deleted')),
        blank=True, null=True)

    changed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['changed_at']),
            models.Index(fields=['content_type']),
            models.Index(fields=['object_id']),
        ]

    def __str__(self):
        return f"{self.content_object} — {self.field_name}"


class HistoryMixin:
    """
    Миксин для автоматического логирования изменений модели.
    Используй с моделями, где нужно отслеживать изменения.
    """

    history_exclude_fields = ["updated_at", "created_at"]

    def save(self, *args, **kwargs):
        user = kwargs.pop("changed_by", None) or get_change_user()
        is_create = self.pk is None

        if not is_create:
            old_obj = self.__class__.objects.get(pk=self.pk)

            for field in self._meta.fields:
                name = field.name
                if name in self.history_exclude_fields:
                    continue

                old = getattr(old_obj, name)
                new = getattr(self, name)

                old_val = self._prepare_value(old)
                new_val = self._prepare_value(new)

                if old_val != new_val:
                    History.objects.create(
                        content_type=ContentType.objects.get_for_model(self),
                        object_id=self.pk,
                        field_name=name,
                        old_value=old_val,
                        new_value=new_val,
                        changed_by=user,
                        action="updated"
                    )

        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        if self.pk:
            content_type = ContentType.objects.get_for_model(self.__class__)
            History.objects.filter(
                content_type=content_type,
                object_id=self.pk
            ).delete()
        
        super().delete(*args, **kwargs)

    def _prepare_value(self, value):
        if value is None:
            return ''
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, models.Model):
            return str(value)
        return str(value).strip()


class Employee(HistoryMixin, models.Model):
    WORKING_STATUS_CHOICES = [
        ("Pracujący", "0080004D"),
        ("Zwolniony", "FFA5004D"),
        ("Umowa o prace", "0000FF4D"),
        ("Zmiana stanowiska", "FFFFFF4D"),
    ]
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    is_student = models.BooleanField(default=False, null=True, blank=True)
    pesel = models.CharField(max_length=36, null=True, blank=True)
    pesel_urk = models.BooleanField(default=False, null=True, blank=True)
    workplace = models.CharField(max_length=128, null=True, blank=True)
    pit_2 = models.BooleanField(default=False, null=True, blank=True)
    working_status = models.CharField(max_length=128, choices=WORKING_STATUS_CHOICES, null=True, blank=True)
    additional_information = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    student_end_date = models.DateField(blank=True, null=True)

    objects = EmployeeManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    

    @property
    def get_full_name(self):
        return f"{self.last_name} {self.first_name}"

    class Meta:
        indexes = [
            models.Index(fields=['last_name', 'pesel']),
            models.Index(fields=['workplace', 'last_name']),
        ]


class EmploymentPeriod(HistoryMixin, models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='employment_period')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['employee', 'start_date']),
            models.Index(fields=['employee', 'end_date']),
        ]


class Document(HistoryMixin, models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=128, null=True, blank=True)
    number = models.CharField(max_length=128, null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['doc_type', 'number']),
            models.Index(fields=['valid_until']),
        ]


class WorkPermit(HistoryMixin, models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='work_permits')
    doc_type = models.CharField(max_length=128, null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['doc_type', 'end_date']),
        ]


class CardSubmission(HistoryMixin, models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='card_submissions')
    doc_type = models.CharField(max_length=128, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)


class Contract(HistoryMixin, models.Model):
    CONTRACT_TYPE_CHOICES = [
        ('o_prace', 'Umowa o pracę'),
        ('zlecenia', 'Umowa zlecenia')
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='contracts')
    contract_type = models.CharField(max_length=128, choices=CONTRACT_TYPE_CHOICES)


class Sanepid(HistoryMixin, models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='sanepids')
    status = models.CharField(max_length=128, blank=True, null=True)
    doc_type = models.CharField(max_length=128, null=True, blank=True)
    end_date = models.DateField(blank=True, null=True)


class Contact(HistoryMixin, models.Model):
    CONTACT_TYPE_CHOICES = [
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('viber', 'Viber'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='contacts',
    )

    contact_type = models.CharField(max_length=16, choices=CONTACT_TYPE_CHOICES, blank=True, null=True)
    value = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return f"{self.contact_type}: {self.value}"

    class Meta:
        indexes = [
            models.Index(fields=['value']),
        ]


class Task(models.Model):
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    assigned_to = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='created_tasks'
    )
    # Хто взяв завдання в роботу
    taken_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='taken_tasks'
    )
    taken_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

    def is_locked(self):
        """Перевіряє чи завдання заблоковане (хтось вже працює над ним)"""
        return self.status == 'in_progress' and self.taken_by is not None

    def can_edit(self, user):
        """Перевіряє чи може користувач редагувати завдання"""
        return self.created_by == user

    def can_take(self, user):
        """Перевіряє чи може користувач взяти завдання в роботу"""
        # Якщо завдання призначене конкретному користувачу
        if self.assigned_to is not None:
            # Тільки призначений користувач може взяти його в роботу
            if self.assigned_to != user:
                return False
        
        # Якщо завдання не призначене або призначене поточному користувачу
        return self.status == 'todo' or (self.status == 'in_progress' and self.taken_by == user)
    
    def can_delete(self, user):
        """Перевірка чи може користувач видалити завдання"""
        return user.is_superuser

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['taken_by', 'status']),
        ]





