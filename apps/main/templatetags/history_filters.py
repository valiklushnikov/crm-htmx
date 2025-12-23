from django import template
from django.utils.translation import gettext as _

register = template.Library()

@register.filter
def field_verbose_name(field_name):
    """
    Конвертує технічну назву поля в читабельну форму
    """
    field_names = {
        # Employee fields
        'first_name': _('Ім\'я'),
        'last_name': _('Прізвище'),
        'age': _('Вік'),
        'is_student': _('Студент'),
        'pesel': _('PESEL'),
        'pesel_urk': _('PESEL (UKR)'),
        'workplace': _('Місце роботи'),
        'pit_2': _('PIT-2'),
        'working_status': _('Статус роботи'),
        'additional_information': _('Додаткова інформація'),
        'created_at': _('Дата створення'),
        'updated_at': _('Дата оновлення'),
        'student_end_date': _('Дійсний до'),
        
        # EmploymentPeriod fields
        'employee': _('Співробітник'),
        'start_date': _('Дата початку'),
        'end_date': _('Дата закінчення'),
        
        # Document fields
        'doc_type': _('Тип документа'),
        'number': _('Номер'),
        'valid_until': _('Дійсний до'),
        
        # WorkPermit fields
        
        # Contact fields
        'contact_type': _('Тип контакту'),
        'value': _('Значення'),
        
        # Contract fields
        'contract_type': _('Тип контракту'),
        
        # Sanepid fields
        'status': _('Статус'),
        
        # Task fields
        'title': _('Назва'),
        'description': _('Опис'),
        'priority': _('Пріоритет'),
        'assigned_to': _('Призначено'),
        'created_by': _('Створив'),
        'taken_by': _('Взяв в роботу'),
        'taken_at': _('Час взяття'),
        'due_date': _('Термін виконання'),
        'completed_at': _('Завершено'),
    }
    
    return field_names.get(field_name, field_name)


@register.filter
def format_field_value(value):
    """
    Форматує значення поля для красивого відображення
    """
    if value is None or value == '':
        return ''
    
    # Конвертуємо булеві значення
    if value.lower() == 'true':
        return _('Так')
    elif value.lower() == 'false':
        return _('Ні')
    
    # Конвертуємо статуси роботи
    working_statuses = {
        'Pracujący': _('Працевлаштований'),
        'Zwolniony': _('Звільнений'),
        'Umowa o prace': _('Трудовий договір'),
        'Zmiana stanowiska': _('Зміна посади'),
    }
    
    if value in working_statuses:
        return working_statuses[value]
    
    # Конвертуємо типи контрактів
    contract_types = {
        'o_prace': _('Трудовий договір'),
        'zlecenia': _('Мандатний контракт'),
    }
    
    if value in contract_types:
        return contract_types[value]
    
    # Конвертуємо типи контактів
    contact_types = {
        'phone': _('Телефон'),
        'email': _('Email'),
        'viber': _('Viber'),
    }
    
    if value in contact_types:
        return contact_types[value]
    
    return value


@register.filter
def model_verbose_name(content_type):
    """
    Конвертує назву моделі в читабельну форму
    """
    model_names = {
        'employee': _('Співробітник'),
        'document': _('Документ'),
        'workpermit': _('Дозвіл на роботу'),
        'cardsubmission': _('Картка'),
        'contract': _('Контракт'),
        'sanepid': _('Sanepid'),
        'contact': _('Контакт'),
        'employmentperiod': _('Період роботи'),
    }
    return model_names.get(content_type.model, content_type.model)


@register.simple_tag
def get_display_name(history_item):
    """
    Отримує правильне відображуване ім'я для об'єкта історії
    """
    obj = history_item.content_object
    
    if obj is None:
        return _('Видалений об\'єкт')
    
    # Якщо це Employee - повертаємо повне ім'я
    if hasattr(obj, 'get_full_name'):
        return obj.get_full_name
    
    # Якщо об'єкт має employee - повертаємо ім'я співробітника
    if hasattr(obj, 'employee'):
        return obj.employee.get_full_name
    
    # В іншому випадку повертаємо __str__ об'єкта
    return str(obj)